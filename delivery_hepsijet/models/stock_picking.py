# -*- coding: utf-8 -*-
import json
import logging
import requests
import psycopg2
import traceback
from pytz import utc
from dateutil import parser
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _compute_hepsijet_contract(self):
        product_contract = self.env.ref('delivery_hepsijet.product_contract').id
        for picking in self:
            products = picking.move_ids.mapped('product_id').ids
            picking.delivery_hepsijet_contract_ok = product_contract in products
            picking.delivery_hepsijet_contract_only = all(product == product_contract for product in products)

    @api.depends('carrier_id')
    def _compute_delivery_hepsijet_ok(self):
        for picking in self:
            picking.delivery_hepsijet_ok = picking.carrier_id.delivery_type == 'hepsijet'

    @api.depends('scheduled_date')
    def _compute_delivery_hepsijet_datetime(self):
        for picking in self:
            now = datetime.now() + timedelta(hours=3) # Turkiye Timezone +3
            date = picking.scheduled_date + timedelta(hours=3) # Turkiye Timezone +3
            type = 'standard'
            time = '0'

            if now.date() == date.date():
                type = 'today'
            elif (now + timedelta(days=1)).date() == date.date():
                type = 'tomorrow'

            if type != 'standard':
                if 0 <= date.hour < 13:
                    time = '1'
                elif 13 <= date.hour < 18:
                    time = '2'
                elif 18 <= date.hour < 24:
                    time = '3'

            picking.delivery_hepsijet_delivery_type = type
            picking.delivery_hepsijet_delivery_time = time

    @api.depends('delivery_tracking_ids')
    def _compute_delivery_hepsijet_done(self):
        for picking in self:
            picking.delivery_hepsijet_done = any(line.status == 'DELIVERED' or line.status == 'DELIVER' or line.status == 'NOT_SIGNED' or line.status == 'RETURNED' for line in picking.delivery_tracking_ids)

    delivery_hepsijet_ok = fields.Boolean(string='HepsiJet', compute='_compute_delivery_hepsijet_ok', store=True)
    delivery_hepsijet_done = fields.Boolean(string='HepsiJet Delivered', compute='_compute_delivery_hepsijet_done', store=True)
    delivery_hepsijet_delivery_type = fields.Selection([
        ('standard', 'Standard'),
        ('today', 'Today'),
        ('tomorrow', 'Tomorrow'),
    ], string='HepsiJet Delivery Type', compute='_compute_delivery_hepsijet_datetime')
    delivery_hepsijet_delivery_time = fields.Selection([
        ('0', 'Standard'),
        ('1', '09:00 - 13:00'),
        ('2', '13:00 - 18:00'),
        ('3', '18:00 - 23:00'),
    ], string='HepsiJet Delivery Time', compute='_compute_delivery_hepsijet_datetime')
    delivery_hepsijet_pod = fields.Boolean(string='HepsiJet POD')
    delivery_hepsijet_connector_ok = fields.Boolean(string='HepsiJet Connector')
    delivery_hepsijet_connector_state = fields.Boolean(string='HepsiJet Connector State', readonly=True, copy=False)
    delivery_hepsijet_connector_message = fields.Char(string='HepsiJet Connector Message', readonly=True, copy=False)
    delivery_hepsijet_contract_picking_id = fields.Many2one('stock.picking', string='HepsiJet Contract Picking', copy=False)
    delivery_hepsijet_contract_picking_res_id = fields.Many2one('stock.picking', string='HepsiJet Contract Picking Origin', copy=False)
    delivery_hepsijet_contract_ok = fields.Boolean(string='HepsiJet Contract Product', compute='_compute_hepsijet_contract')
    delivery_hepsijet_contract_only = fields.Boolean(string='HepsiJet Contract Only', compute='_compute_hepsijet_contract')
    delivery_hepsijet_egyg_ok = fields.Boolean(string='HepsiJet EGYG')
    delivery_hepsijet_egyg_picking_id = fields.Many2one('stock.picking', string='HepsiJet EGYG Picking', copy=False)
    delivery_hepsijet_egyg_picking_res_id = fields.Many2one('stock.picking', string='HepsiJet EGYG Picking Origin', copy=False)
    delivery_hepsijet_date_update = fields.Datetime(string='HepsiJet Update Date', copy=False, readonly=True)
    delivery_hepsijet_date_query = fields.Datetime(string='HepsiJet Query Date', copy=False, readonly=True)
    delivery_hepsijet_contract_id = fields.Char(string='HepsiJet Contract ID', copy=False, readonly=True)
    delivery_hepsijet_recall_picking = fields.Boolean(string='HepsiJet Recall Picking', copy=False, readonly=True)

    def _hepsijet_get_sender(self):
        location = self.env.context.get('location') or self.location_id
        if hasattr(location.warehouse_id, 'partner_id'):
            return location.warehouse_id.partner_id
        return self.partner_id

    def _hepsijet_get_receiver(self, partner=None):
        if not partner:
            partner = self.partner_id
        if partner.is_company:
            partner = partner.contact_id
            if not partner:
                raise UserError(_('No contact found related to %s.') % partner.name)
        return partner

    def _hepsijet_get_customer_order_id(self):
        name = None
        if self.delivery_hepsijet_egyg_ok:
            egyg_id = self.delivery_hepsijet_egyg_picking_id
            egyg_res_id = self.delivery_hepsijet_egyg_picking_res_id
            if egyg_id:
                name = egyg_id.move_line_ids[:1].lot_id.name
            elif egyg_res_id:
                name = self.move_line_ids[:1].lot_id_name
        return name

    def _hepsijet_get_relation_code(self, prefix):
        return prefix + str(self.id).zfill(9)

    def _hepsijet_get_egyg_location_id(self):
        return self.location_id

    def write(self, values):
        if 'carrier_tracking_ref' in values and values['carrier_tracking_ref'] and isinstance(values['carrier_tracking_ref'], str) and ',' in values['carrier_tracking_ref']:
            if any(picking.delivery_hepsijet_ok for picking in self):
                del values['carrier_tracking_ref']
        return super().write(values)

    def get_delivery_hepsijet_log(self):
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

            if self.delivery_hepsijet_contract_picking_id:
                picking_product = self
                picking_contract = self.delivery_hepsijet_contract_picking_id
            elif self.delivery_hepsijet_contract_picking_res_id:
                picking_product = self.delivery_hepsijet_contract_picking_res_id
                picking_contract = self
            else:
                if self.delivery_hepsijet_contract_ok:
                    picking_product = self.env['stock.picking']
                    picking_contract = self
                else:
                    picking_product = self
                    picking_contract = self.env['stock.picking']

            reference = []
            if picking_product:
                reference.append(picking_product.syncops_log_ref or str(picking_product.id))
            if picking_contract:
                reference.append(picking_contract.syncops_log_ref or str(picking_contract.id))

            url += '/api/v1/log'
            connector = connectors[0]
            response = requests.get(url, params={
                'username': connector.username,
                'token': ','.join(connectors.mapped('token')),
                'reference': ','.join(reference),
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

    def update_delivery_hepsijet_state(self, domain=None):
        """Public helper to update HepsiJet states.

        Now enqueued in queue_job to avoid worker timeout / UI blocking.

        :param domain: optional extra search domain list
        :param immediate: force synchronous execution (used for tests / special cases)
        :return: queued job (or boolean True if executed immediately)
        """
        domain = list(domain) if domain else []
        domain += [
            # ('state', '=', 'done'),  # kept disabled intentionally – we also update not-done transfers
            ('delivery_hepsijet_ok', '=', True),
            ('carrier_tracking_ref', '!=', False),
            ('delivery_hepsijet_done', '=', False),
        ]
        if self:
            reference = ','.join(map(str, self.ids))
            domain.append(('id', 'in', self.ids))
        else:
            reference = 'Cronjob'
            start_date = datetime.now() - timedelta(days=30)
            domain.append(('scheduled_date', '>=', start_date))

        pickings = self.search(domain)
        if not pickings:
            return True

        ctx = dict(self.env.context, reference=reference)

        if self:
            pickings.with_context(ctx)._update_delivery_hepsijet_state()
            return True

        description = _('HepsiJet status update (%s)') % reference
        job = pickings.with_context(ctx).with_delay(channel='root.hepsijet', description=description)._update_delivery_hepsijet_state()
        return job

    def _get_delivery_hepsijet_state(self, name, code):
        return self.carrier_id.delivery_status_mapping_ids.get_status(name=name, code=code)

    def _update_delivery_hepsijet_webhook_state(self, data):
        try:
            tx = data.get('trackingEvent', {}) or {}
            package_info = tx.get('packageInfo', {}) or {}
            ref = package_info.get('orderId') or package_info.get('trackingCode')
            if not ref:
                return True
            picking = self.env['stock.picking'].search([('carrier_tracking_ref', '=', ref)], limit=1)
            if not picking:
                return True
            tracking_datetime = (tx.get('trackingDateTime', {}) or {}).get('eventDateTime') or ''
            if tracking_datetime and '+' not in tracking_datetime and 'Z' not in tracking_datetime:
                tracking_datetime_tz = tracking_datetime + '+0000'
            else:
                tracking_datetime_tz = tracking_datetime.replace('Z', '+0000')
            event_and_reason = tx.get('eventAndReason', {}) or {}
            location = (tx.get('location', {}) or {}).get('arrivalBranch')
            fake_result = [{
                'status': 'OK',
                'data': [{
                    'customerDeliveryNo': package_info.get('orderId'),
                    'barcode': package_info.get('trackingCode'),
                    'deliveryType': package_info.get('deliveryType') or package_info.get('type'),
                    'deliveryDatePromised': tracking_datetime_tz,
                    'transactions': [{
                        'transactionDateTime': tracking_datetime_tz,
                        'transaction': event_and_reason.get('reasonDescription'),
                        'deliveryStatus': event_and_reason.get('code'),
                        'location': location,
                        'nonDeliveryReason': package_info.get('nonDeliveryReason'),
                        'nonDeliveryReasonMessage': package_info.get('nonDeliveryReasonMessage'),
                        'nonDeliveryReturnReason': package_info.get('nonDeliveryReturnReason'),
                        'nonDeliveryReturnReasonMessage': package_info.get('nonDeliveryReturnReasonMessage'),
                    }],
                }],
            }]
            picking._process_delivery_hepsijet_state_chunk(webhook_data=fake_result)
            return True
        except Exception as e:
            _logger.error('An error occurred when updating HepsiJet delivery state (webhook): %s\n%s' % (e, json.dumps(data, default=str, indent=4, ensure_ascii=False)))
            return traceback.format_exc()

    @api.model
    def _update_delivery_hepsijet_state(self):
        if not self:
            return
        reference = self.env.context.get('reference')
        chunk_size = int(self.env.context.get('hepsijet_chunk_size', 50))
        orchestrate = self.env.context.get('hepsijet_orchestrate', True)
        if orchestrate and len(self) > chunk_size:
            groups = {}
            for picking in self:
                key = picking.syncops_connector_id.id or picking.carrier_id.delivery_hepsijet_connector_id.id
                groups.setdefault(key, self.env['stock.picking'])
                groups[key] |= picking
            for connector_id, picking_ids in groups.items():
                refs = picking_ids.mapped('carrier_tracking_ref')
                for i in range(0, len(refs), chunk_size):
                    ref_slice = refs[i:i+chunk_size]
                    subset = picking_ids.filtered(lambda p, rs=set(ref_slice): p.carrier_tracking_ref in rs)
                    desc = _('HepsiJet chunk (%s) %s-%s') % (connector_id, i+1, i+len(ref_slice))
                    subset.with_context(reference=reference, hepsijet_orchestrate=False).with_delay(channel='root.hepsijet', description=desc)._process_delivery_hepsijet_state_chunk(connector_id)
            return True

        connector_ids = {}
        for picking in self:
            key = picking.syncops_connector_id.id or picking.carrier_id.delivery_hepsijet_connector_id.id
            connector_ids.setdefault(key, self.env['stock.picking'])
            connector_ids[key] |= picking
        for connector_id, picking_ids in connector_ids.items():
            picking_ids._process_delivery_hepsijet_state_chunk(connector_id)
        return True

    def _process_delivery_hepsijet_state_chunk(self, connector_id=None, webhook_data=None):
        if not self:
            return True
        if webhook_data is not None:
            result = webhook_data
        else:
            reference = self.env.context.get('reference')
            params = {'reference': self.mapped('carrier_tracking_ref')}
            connectors = self.env['syncops.connector'].browse(connector_id)
            result = self.env['syncops.connector'].sudo()._execute('delivery_get_order', params=params, reference=reference, connectors=connectors) or []
        for res in result:
            if not res.get('status') == 'FAIL' and 'data' in res:
                for r in res.get('data', []):
                    try:
                        updated = False
                        ref = r.get('customerDeliveryNo', False) or r.get('barcode', False)
                        picking = self.filtered(lambda p: p.carrier_tracking_ref and p.carrier_tracking_ref == ref)
                        if not picking:
                            continue
                        for tx in r.get('transactions', []):
                            tx_dt_raw = tx.get('transactionDateTime', '')
                            if tx_dt_raw and '+' not in tx_dt_raw and 'Z' not in tx_dt_raw:
                                tx_dt_raw += '+0000'
                            tx_dt_raw = tx_dt_raw.replace('Z', '+0000')
                            tx_datetime = datetime.strptime(tx_dt_raw, '%Y-%m-%dT%H:%M:%S%z')
                            tx_date = tx_datetime.strftime('%d-%m-%Y')
                            tx_time = tx_datetime.strftime('%H:%M:%S')
                            tx_datetime = tx_datetime.astimezone(utc).replace(tzinfo=None)
                            tx_state = picking._get_delivery_hepsijet_state(tx.get('transaction'), tx.get('deliveryStatus'))
                            if not picking.delivery_tracking_ids.filtered(lambda t: t.status == tx.get('deliveryStatus') and t.transaction_date == tx_date and t.transaction_time == tx_time):
                                if r.get('deliveryType') != 'RETURNED':
                                    dp_raw = r.get('deliveryDatePromised', '')
                                    if dp_raw and '+' not in dp_raw and 'Z' not in dp_raw:
                                        dp_raw += '+0000'
                                    dp_raw = dp_raw.replace('Z', '+0000')
                                    date_promised = datetime.strptime(dp_raw, '%Y-%m-%dT%H:%M:%S%z').astimezone(utc).replace(tzinfo=None)
                                    tracking_values = {
                                        'name': picking.carrier_id.name,
                                        'picking_id': picking.id,
                                        'carrier_id': picking.carrier_id.id,
                                        'sale_order_id': picking.sale_id.id,
                                        'date_promised': date_promised,
                                        'transaction_datetime': tx_datetime,
                                        'transaction_date': tx_date,
                                        'transaction_time': tx_time,
                                        'transaction': tx.get('transaction', False),
                                        'location': tx.get('location', False),
                                        'customer_barcode': ref,
                                        'delivery_type': r.get('deliveryType', False),
                                        'delivery_status': tx.get('deliveryStatus', False) == 'DELIVERED' and date_promised > tx_datetime and 'done' or 'cancel',
                                        'delivery_return_reason': tx.get('nonDeliveryReason', False),
                                        'delivery_return_reason_message': tx.get('nonDeliveryReasonMessage', False),
                                        'delivery_on_promised': tx.get('deliveryStatus', False) == 'DELIVERED' and date_promised > tx_datetime,
                                        'status': tx.get('deliveryStatus', False),
                                        'state': tx_state.code,
                                        'status_id': tx_state.id,
                                    }
                                else:
                                    tracking_values = {
                                        'sale_order_id': picking.sale_id.id,
                                        'transaction_datetime': tx_datetime,
                                        'transaction_date': tx_date,
                                        'transaction_time': tx_time,
                                        'transaction': tx.get('transaction', ''),
                                        'location': tx.get('location', ''),
                                        'customer_barcode': ref,
                                        'delivery_type': r.get('deliveryType', False),
                                        'delivery_return_reason': tx.get('nonDeliveryReturnReason', False),
                                        'delivery_return_reason_message': tx.get('nonDeliveryReturnReasonMessage', False),
                                        'status': tx.get('deliveryStatus', False),
                                        'state': tx_state.code,
                                        'status_id': tx_state.id,
                                    }
                                picking.write({
                                    'carrier_doc_id': ref,
                                    'carrier_state': tx_state.code,
                                    'carrier_status_id': tx_state.id,
                                    'delivery_hepsijet_connector_ok': True,
                                    'delivery_hepsijet_connector_state': True,
                                    'delivery_hepsijet_connector_message': _('Connector process succeeded.'),
                                    'delivery_tracking_ids': [(0, 0, tracking_values)],
                                })
                                updated = True

                        if picking.delivery_hepsijet_egyg_ok and picking.delivery_tracking_ids and not picking.delivery_hepsijet_egyg_picking_id and not picking.delivery_hepsijet_egyg_picking_res_id:
                            p = self.env['stock.return.picking'].sudo().create({'picking_id': picking.id})
                            p._onchange_picking_id()
                            location = picking._hepsijet_get_egyg_location_id()
                            if location:
                                p.location_id = location.id
                            np, pti = p.with_context(egyg=True)._create_returns()
                            picking.write({'delivery_hepsijet_egyg_picking_id': np})
                            npicking = picking.browse(np)
                            npicking.write({
                                'carrier_id': picking.carrier_id.id,
                                'delivery_hepsijet_egyg_picking_res_id': picking.id,
                            })
                            self.env.cr.commit() # commit before send_to_shipper, because we do not want to lose picking id
                            try:
                                npicking.sudo().send_to_shipper()
                            except Exception as e:
                                _logger.error('An error occured when sending HepsiJet EGYG order: %s' % e, exc_info=True)
                            updated = True

                        now = fields.Datetime.now().strftime(DTF)
                        values = ["delivery_hepsijet_date_query='%s'" % now]
                        if updated:
                            values += ["delivery_hepsijet_date_update='%s'" % now]
                        self.env.cr.execute('UPDATE stock_picking SET %s WHERE id=%s' % (', '.join(values), picking.id))

                    except psycopg2.errors.SerializationFailure:
                        self.env.cr.rollback()
                        continue

                    except Exception as e:
                        _logger.error('An error occured when getting HepsiJet delivery orders: %s\n%s' % (e, json.dumps(r, default=str, indent=4, ensure_ascii=False)))

                    self.env.cr.commit()
        return True

    def cancel_shipment(self):
        if self.delivery_hepsijet_ok:
            params = {
                'reference' : self.delivery_hepsijet_contract_id if self.delivery_hepsijet_contract_ok else self.carrier_tracking_ref,
                'contract' : self.delivery_hepsijet_contract_ok,
            }
            connectors = self.syncops_connector_id or self.carrier_id.delivery_hepsijet_connector_id
            result = self.env['syncops.connector'].sudo()._execute('delivery_patch_order_cancel', params=params, reference=str(self.id), connectors=connectors)
            if not result:
                raise ValidationError(_('An error occured. Please check the logs for further detail.'))

            for r in result:
                if r['status'] == 'FAIL':
                    if r['message'] == "Bu gönderi TMS'den silinemez":
                        continue
                    elif r['message'] == "Gönderi statüsü uygun değil.":
                        continue
                    raise ValidationError(r['message'])

        return super(StockPicking, self).cancel_shipment()

    def recall_delivery_hepsijet_order(self):
        if self.delivery_hepsijet_ok:
            params = {'reference' : self.carrier_tracking_ref}
            connectors = self.syncops_connector_id or self.carrier_id.delivery_hepsijet_connector_id
            result = self.env['syncops.connector'].sudo()._execute('delivery_post_recall_order', params=params, reference=str(self.id), connectors=connectors)
            if not result:
                raise ValidationError(_('An error occured. Please check the logs for further detail.'))

            for r in result:
                if r['status'] == 'FAIL':
                    raise ValidationError(r['message'])
                else:
                    self.delivery_hepsijet_recall_picking = True
                    self.delivery_tracking_ids.sudo().write({'delivery_status': 'recall', 'delivery_on_promised': False})

    def action_cancel(self):
        res = super(StockPicking, self).action_cancel()
        for picking in self:
            if picking.delivery_hepsijet_ok and picking.picking_type_code == 'incoming' and picking.state == 'cancel' and picking.carrier_tracking_ref:
                picking.cancel_shipment()
        return res

    def action_delivery_hepsijet_picking_contract(self):
        action = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
        action['res_id'] = self.delivery_hepsijet_contract_picking_id.id
        action['views'] = [(False, 'form')]
        return action

    def action_delivery_hepsijet_picking_contract_origin(self):
        action = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
        action['res_id'] = self.delivery_hepsijet_contract_picking_res_id.id
        action['views'] = [(False, 'form')]
        return action

    def action_delivery_hepsijet_picking_egyg(self):
        action = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
        action['res_id'] = self.delivery_hepsijet_egyg_picking_id.id
        action['views'] = [(False, 'form')]
        return action

    def action_delivery_hepsijet_picking_egyg_origin(self):
        action = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
        action['res_id'] = self.delivery_hepsijet_egyg_picking_res_id.id
        action['views'] = [(False, 'form')]
        return action
