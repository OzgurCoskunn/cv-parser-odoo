# -*- coding: utf-8 -*-
import gc
import json
import logging
import requests
import psycopg2
import traceback
from dateutil import parser
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.depends('carrier_id')
    def _compute_delivery_yurtici_ok(self):
        for picking in self:
            picking.delivery_yurtici_ok = picking.carrier_id.delivery_type == 'yurtici'

    @api.depends('delivery_tracking_ids')
    def _compute_delivery_yurtici_done(self):
        if not self:
            return

        picking_ids = tuple(self.ids)
        if not picking_ids:
            return
        if len(picking_ids) == 1:
            picking_ids = (picking_ids[0],)

        self.env.cr.execute("""
            SELECT DISTINCT dt.picking_id
            FROM delivery_tracking dt
            WHERE dt.picking_id IN %s
            AND dt.transaction IN ('Teslim Edildi', 'Satıcıya İade Edildi')
            LIMIT %s
        """, (picking_ids, len(self)))

        delivered_picking_ids = set(row[0] for row in self.env.cr.fetchall())

        for picking in self:
            picking.delivery_yurtici_done = picking.id in delivered_picking_ids

    delivery_yurtici_ok = fields.Boolean(string='Yurtiçi Kargo', compute='_compute_delivery_yurtici_ok', store=True)
    delivery_yurtici_done = fields.Boolean(string='Yurtiçi Kargo Delivered', compute='_compute_delivery_yurtici_done', store=True)
    delivery_yurtici_connector_ok = fields.Boolean(string='Yurtiçi Kargo Connector')
    delivery_yurtici_connector_state = fields.Boolean(string='Yurtiçi Kargo Connector State', readonly=True, copy=False)
    delivery_yurtici_connector_message = fields.Char(string='Yurtiçi Kargo Connector Message', readonly=True, copy=False)
    delivery_yurtici_date_update = fields.Datetime(string='Yurtiçi Update Date', copy=False, readonly=True)
    delivery_yurtici_date_query = fields.Datetime(string='Yurtiçi Query Date', copy=False, readonly=True)

    def _yurtici_get_connector(self):
        self.ensure_one()
        if self.syncops_connector_id:
            return self.syncops_connector_id
        if self.is_return_picking and self.carrier_id.delivery_yurtici_return_connector_id:
            return self.carrier_id.delivery_yurtici_return_connector_id
        return self.carrier_id.delivery_yurtici_connector_id

    def _yurtici_get_partner(self, partner=None):
        if not partner:
            partner = self.partner_id

        if partner.is_company:
            if hasattr(partner, 'contact_id'):
                partner = partner.contact_id
                if not partner:
                    raise UserError(_('No contact found related to %s.') % self.partner_id.name)
            else:
                pass
        return partner

    def get_delivery_yurtici_log(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        connectors = self.env['syncops.connector'].sudo().with_context(active_test=False)._find('delivery_get_order', company=company)
        if not connectors:
            raise UserError(_('No syncOPS connector found'))

        if not self.id:
            raise UserError(_('Please save picking before checking connector logs'))

        result = []
        try:
            url = self.env['ir.config_parameter'].sudo().get_param('syncops.url')
            if not url:
                raise ValidationError(_('No syncOPS endpoint URL found'))

            url += '/api/v1/log'
            connector = connectors[0]
            response = requests.get(url, params={
                'username': connector.username,
                'token': ','.join(connectors.mapped('token')),
                'reference': str(self.id) if not self.is_return_picking else self.carrier_tracking_ref,
            })
            if response.status_code == 200:
                results = response.json()
                if not results['status'] == 0:
                    raise UserError(results['message'])
                logs = results.get('logs', [])
                for log in logs:
                    result.append({
                        'connector_id': connector.id,
                        'company_id': self.env.company.id,
                        'date': parser.parse(log['date']),
                        'partner_name': log['partner'],
                        'connector_name': log['connector'],
                        'token_name': log['token'],
                        'method_name': log['method'],
                        'status': log['status'],
                        'state': log['state'],
                        'message': log['message'],
                        'request_data': log['request_data'],
                        'request_raw': log['request_raw'],
                        'request_method': log['request_method'],
                        'request_url': log['request_url'],
                        'response_code': log['response_code'],
                        'response_message': log['response_message'],
                        'response_data': log['response_data'],
                        'response_raw': log['response_raw'],
                    })
            else:
                raise UserError(response.text or response.reason)
        except Exception as e:
            raise UserError(str(e))

        if result:
            logs = self.env['syncops.log'].sudo().create(result)
            action = self.env.ref('connector_syncops.action_log').sudo().read()[0]
            action['context'] = {'create': False, 'delete': False, 'edit': False, 'import': False}
            action['domain'] = [('id', 'in', logs.ids)]
            return action
        else:
            raise UserError(_('No log found'))

    def _get_delivery_yurtici_domain(self):
        return [
            ('state', '=', 'done'),
            ('delivery_yurtici_ok', '=', True),
            ('carrier_tracking_ref', '!=', False),
            ('delivery_yurtici_done', '=', False),
        ]

    def update_delivery_yurtici_state(self, domain=None):
        domain = list(domain) if domain else []
        domain += [
            ('state', '=', 'done'),
            ('delivery_yurtici_ok', '=', True),
            ('carrier_tracking_ref', '!=', False),
            ('delivery_yurtici_done', '=', False),
        ]
        if self:
            reference = ','.join(map(str, self.ids))
            domain.append(('id', 'in', self.ids))
        else:
            reference = 'Cronjob'
            date_start = self.env['ir.config_parameter'].sudo().get_param('delivery.yurtici.date.start', False)
            if date_start:
                domain.append(('create_date', '>', date_start))

        pickings = self.search(domain)
        if not pickings:
            return True

        active_pickings = self._cleanup_stale_yurtici_trackings(pickings)
        if not active_pickings:
            return True

        ctx = dict(self.env.context, reference=reference)

        if self:
            active_pickings.with_context(ctx)._update_delivery_yurtici_state()
            return active_pickings

        description = _('Yurtiçi status update (%s)') % reference
        job = active_pickings.with_context(ctx).with_delay(channel='root.yurtici', description=description)._update_delivery_yurtici_state()
        return job

    def _get_delivery_yurtici_state(self, name, code, ref):
        if ref == '10':
            name = False
        else:
            ref = False

        return self.carrier_id.delivery_status_mapping_ids.get_status(name=name, code=code, ref=ref)

    def _cleanup_stale_yurtici_trackings(self, pickings):
        cleanup_days = int(self.env['ir.config_parameter'].sudo().get_param('delivery.yurtici.cleanup.days', '14'))
        cleanup_date = datetime.now() - timedelta(days=cleanup_days)

        stale_pickings = pickings.filtered(
            lambda p: (
                (p.delivery_yurtici_date_query and p.delivery_yurtici_date_query < cleanup_date) or
                (not p.delivery_yurtici_date_query and p.delivery_yurtici_date_update and p.delivery_yurtici_date_update < cleanup_date) or
                (not p.delivery_yurtici_date_update and p.create_date < cleanup_date)
            ) and 
            not p.delivery_yurtici_done and
            p.carrier_tracking_ref
        )
        if stale_pickings:
            stale_pickings.write({
                'carrier_tracking_ref': False,
                'delivery_yurtici_connector_ok': False,
                'delivery_yurtici_connector_state': False,
                'delivery_yurtici_connector_message': _('Tracking reference cleaned due to stale data'),
            })
            
            for picking in stale_pickings:
                picking.message_post(
                    body=_('Yurtiçi Cargo tracking reference automatically cleaned. Reason: Record not updated for %d days.') % cleanup_days
                )
        
        active_pickings = pickings - stale_pickings
        return active_pickings

    def _check_tracking_exists_batch(self, picking_id, event_id, tx_date, tx_time, cache=None):
        cache = cache if cache is not None else {}
        cache_key = f"{picking_id}_{event_id}_{tx_date}_{tx_time}"
        if cache_key in cache:
            return cache[cache_key]

        self.env.cr.execute("""
            SELECT 1 FROM delivery_tracking
            WHERE picking_id = %s
            AND status = %s
            AND transaction_date = %s
            AND transaction_time = %s
            LIMIT 1
        """, (picking_id, event_id, tx_date, tx_time))

        exists = bool(self.env.cr.fetchone())
        cache[cache_key] = exists
        return exists

    def _check_operation_status_exists(self, picking_id, operation_status, cache=None):
        cache = cache if cache is not None else {}
        cache_key = f"{picking_id}_{operation_status or 'NULL'}"
        if cache_key in cache:
            return cache[cache_key]

        if not operation_status:
            self.env.cr.execute("""
                SELECT 1 FROM delivery_tracking
                WHERE picking_id = %s AND (status IS NULL OR status = '')
                LIMIT 1
            """, (picking_id,))
        else:
            self.env.cr.execute("""
                SELECT 1 FROM delivery_tracking
                WHERE picking_id = %s AND status = %s
                LIMIT 1
            """, (picking_id, operation_status))

        exists = bool(self.env.cr.fetchone())
        cache[cache_key] = exists
        return exists

    @api.model
    def _update_delivery_yurtici_state(self):
        if not self:
            return
        reference = self.env.context.get('reference')
        chunk_size = int(self.env.context.get('yurtici_chunk_size', 19)) 
        orchestrate = self.env.context.get('yurtici_orchestrate', True)
        
        if orchestrate and len(self) > chunk_size:
            groups = {}
            for picking in self:
                key = picking._yurtici_get_connector().id
                groups.setdefault(key, self.env['stock.picking'])
                groups[key] |= picking
            for connector_id, picking_ids in groups.items():
                refs = picking_ids.mapped('carrier_tracking_ref')
                for i in range(0, len(refs), chunk_size):
                    ref_slice = refs[i:i+chunk_size]
                    subset = picking_ids.filtered(lambda p, rs=set(ref_slice): p.carrier_tracking_ref in rs)
                    desc = _('Yurtiçi chunk (%s) %s-%s') % (connector_id, i+1, i+len(ref_slice))
                    subset.with_context(reference=reference, yurtici_orchestrate=False).with_delay(channel='root.yurtici', description=desc)._process_delivery_yurtici_state_chunk(connector_id)
            return True

        connector_ids = {}
        for picking in self:
            key = picking._yurtici_get_connector().id
            connector_ids.setdefault(key, self.env['stock.picking'])
            connector_ids[key] |= picking
        for connector_id, picking_ids in connector_ids.items():
            picking_ids._process_delivery_yurtici_state_chunk(connector_id)
        return True

    def _process_delivery_yurtici_state_chunk(self, connector_id=None):
        if not self:
            return True

        reference = self.env.context.get('reference')
        params = {'reference': self.mapped('carrier_tracking_ref')}
        connectors = self.env['syncops.connector'].browse(connector_id)
        result = self.env['syncops.connector'].sudo()._execute('delivery_get_order', params=params, reference=reference, connectors=connectors) or []

        tracking_batch = []
        picking_updates = {}
        tracking_cache = {}
        operation_cache = {}
        ts = fields.Datetime.now()

        for res in result:
            if 'data' in res:
                for r in res['data']:
                    try:
                        updated = False
                        picking = self.filtered(lambda p: p.carrier_tracking_ref == r['cargoKey'])
                        if not picking:
                            continue

                        if r['shippingDeliveryItemDetailVO']:
                            for tx in r['shippingDeliveryItemDetailVO']['invDocCargoVOArray']:
                                tx_datetime = datetime.strptime(tx['eventDate'] + tx['eventTime'], '%Y%m%d%H%M%S')
                                tx_date = tx_datetime.strftime('%d-%m-%Y')
                                tx_time = tx_datetime.strftime('%H:%M:%S')

                                if not self._check_tracking_exists_batch(picking.id, tx['eventId'], tx_date, tx_time, tracking_cache):
                                    tx_state = picking._get_delivery_yurtici_state(tx['eventName'], tx['eventId'], r['shippingDeliveryItemDetailVO']['rejectStatus'])
                                    tracking_values = {
                                        'name': picking.carrier_id.name,
                                        'picking_id': picking.id,
                                        'carrier_id': picking.carrier_id.id,
                                        'customer_barcode': r['cargoKey'],
                                        'location': tx['reasonName'],
                                        'delivery_type': 'RETAIL',
                                        'sale_order_id': picking.sale_id.id,
                                        'transaction_datetime': tx_datetime - timedelta(hours=3),
                                        'transaction_date': tx_date,
                                        'transaction_time': tx_time,
                                        'transaction': tx['eventName'],
                                        'status': tx['eventId'],
                                        'state': tx_state.code,
                                        'status_id': tx_state.id,
                                    }
                                    
                                    tracking_batch.append(tracking_values)
                                    picking_updates[picking.id] = {
                                        'carrier_state': tx_state.code,
                                        'carrier_status_id': tx_state.id,
                                        'carrier_doc_id': r['shippingDeliveryItemDetailVO']['docId'],
                                        'delivery_yurtici_connector_ok': True,
                                        'delivery_yurtici_connector_state': True,
                                        'delivery_yurtici_connector_message': _('Connector process succeeded.'),
                                        'delivery_yurtici_date_update': ts,
                                        'delivery_yurtici_date_query': ts,
                                    }
                                    updated = True
                        else:
                            if not self._check_operation_status_exists(picking.id, r['operationStatus'], operation_cache):
                                status = self.env['delivery.status'].get_status('other')
                                tracking_values = {
                                    'name': picking.carrier_id.name,
                                    'picking_id': picking.id,
                                    'carrier_id': picking.carrier_id.id,
                                    'customer_barcode': r['cargoKey'],
                                    'delivery_type': 'RETAIL',
                                    'sale_order_id': picking.sale_id.id,
                                    'transaction': r['operationMessage'],
                                    'status': r['operationStatus'],
                                    'state': status.code,
                                    'status_id': status.id,
                                }
                                
                                tracking_batch.append(tracking_values)
                                picking_updates[picking.id] = {
                                    'delivery_yurtici_connector_ok': True,
                                    'delivery_yurtici_connector_state': True,
                                    'delivery_yurtici_connector_message': _('Connector process succeeded.'),
                                    'delivery_yurtici_date_update': ts,
                                    'delivery_yurtici_date_query': ts,
                                }
                                updated = True

                        if picking.id not in picking_updates:
                            picking_updates[picking.id] = {
                                'delivery_yurtici_date_query': ts,
                            }

                    except psycopg2.errors.SerializationFailure:
                        self.env.cr.rollback()
                        continue

                    except Exception as e:
                        _logger.error('An error occurred when getting Yurtiçi delivery orders: %s\n%s' % (e, json.dumps(r, default=str, indent=4, ensure_ascii=False)))

        try:
            if tracking_batch:
                self.env['delivery.tracking'].sudo().create(tracking_batch)
            
            for picking_id, vals in picking_updates.items():
                try:
                    self.browse(picking_id).sudo().write(vals)
                except Exception as update_err:
                    _logger.error('Failed to batch update picking %s: %s', picking_id, update_err)
                    
        except Exception as batch_err:
            _logger.error('Failed to process batch updates: %s', batch_err)
            for picking_id, vals in picking_updates.items():
                try:
                    self.browse(picking_id).sudo().write({
                        'delivery_yurtici_date_query': ts,
                    })
                except Exception:
                    pass 

        return True

    def cancel_shipment(self):
        if self.delivery_yurtici_ok:
            params = {
                'reference' : self.carrier_tracking_ref,
                'returned': self.is_return_picking,
            }
            connectors = self._yurtici_get_connector()
            result = self.env['syncops.connector'].sudo()._execute('delivery_patch_order_cancel', params=params, reference=str(self.id), connectors=connectors)
            if not result:
                raise ValidationError(_('An error occured. Please check the logs for further detail.'))

            for r in result:
                if r['flag'] != '0':
                    if not r['data'] and r['code'] == 82656:
                        raise ValidationError(_('The return code does not exist in the system.'))
                    raise ValidationError(r['data']['errMessage'])

        return super(StockPicking, self).cancel_shipment()

    def action_cancel(self):
        if self.delivery_yurtici_ok:
            self.cancel_shipment()
        return super(StockPicking, self).action_cancel()
    
    @api.depends('carrier_id', 'move_ids_without_package')
    def _compute_return_picking(self):
        for picking in self:
            picking.is_return_picking = any(m.origin_returned_move_id for m in picking.move_ids_without_package)

