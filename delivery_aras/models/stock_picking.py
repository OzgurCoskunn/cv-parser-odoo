# -*- coding: utf-8 -*-
import json
import logging
import psycopg2
import traceback
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.depends('move_ids_without_package')
    def _compute_delivery_aras_piece_count(self):
        for picking in self:
            picking.delivery_aras_piece_count = len(picking.move_ids_without_package)

    @api.depends('carrier_id')
    def _compute_delivery_aras_ok(self):
        for picking in self:
            picking.delivery_aras_ok = picking.carrier_id.delivery_type == 'aras'

    def _compute_delivery_aras_currency(self):
        currency = self.env['res.currency'].sudo().with_context(active_test=False).search([('name', '=', 'TRY')])
        for picking in self:
            picking.delivery_aras_currency_id = currency.id

    @api.depends('partner_id')
    def _compute_delivery_aras_partner_info(self):
        for picking in self:
            street = []
            if picking.partner_id.street:
                street.append(picking.partner_id.street)
            if picking.partner_id.street2:
                street.append(picking.partner_id.street2)
            if street:
                address = "\n".join(street)
            else:
                address = False

            picking.delivery_aras_receiver_address = address
            picking.delivery_aras_receiver_name = picking.partner_id.name
            picking.delivery_aras_receiver_phone = picking.partner_id.mobile or picking.partner_id.phone or picking.partner_id.commercial_partner_id.mobile or picking.partner_id.commercial_partner_id.phone
            picking.delivery_aras_receiver_city = picking.partner_id.state_id.name
            picking.delivery_aras_receiver_town = picking.partner_id.city
            picking.delivery_aras_tax_number = picking.partner_id.vat
            picking.delivery_aras_tax_office = hasattr(picking.partner_id, 'tax_office_id') and picking.partner_id.tax_office_id.name or ''

    delivery_aras_ok = fields.Boolean(string='Aras Kargo', compute="_compute_delivery_aras_ok", store=True)
    delivery_aras_sender = fields.Char(string='Aras Kargo Sender', readonly=True)
    delivery_aras_receiver = fields.Char(string='Aras Kargo Receiver', readonly=True)
    delivery_aras_receiver_name = fields.Char(string='Aras Kargo Receiver Name', compute='_compute_delivery_aras_partner_info' , store=True, readonly=True)
    delivery_aras_receiver_city = fields.Char(string='Aras Kargo Receiver City', compute='_compute_delivery_aras_partner_info' , store=True, readonly=True)
    delivery_aras_receiver_town = fields.Char(string='Aras Kargo Receiver Town', compute='_compute_delivery_aras_partner_info' , store=True, readonly=True)
    delivery_aras_receiver_phone = fields.Char(string='Aras Kargo Receiver Phone', compute='_compute_delivery_aras_partner_info' , store=True, readonly=True)
    delivery_aras_receiver_address = fields.Text(string='Aras Kargo Receiver Address', compute='_compute_delivery_aras_partner_info' , store=True, readonly=True)

    delivery_aras_tax_number = fields.Char(string='Aras Kargo Tax Number', compute='_compute_delivery_aras_partner_info', store=True, readonly=True)
    delivery_aras_tax_office = fields.Char(string='Aras Kargo Tax Office', compute='_compute_delivery_aras_partner_info', store=True, readonly=True)
    delivery_aras_export_ok = fields.Boolean(string='Aras Kargo Export', readonly=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    delivery_aras_export_code = fields.Selection(string='Aras Kargo Export Code', selection=[('1', 'Yes'), ('0', 'No')], readonly=True)
    delivery_aras_delivery_code = fields.Char(string='Aras Kargo Delivery Code', readonly=True)
    delivery_aras_invoice_number = fields.Char(string='Aras Kargo Invoice Number', readonly=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    delivery_aras_dispatch_number = fields.Char(string='Aras Kargo Dispatch Number', readonly=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    delivery_aras_waybill_number = fields.Char(string='Aras Kargo Waybill Number', readonly=True)

    delivery_aras_type_code = fields.Selection(string='Aras Kargo Type Code', selection=[('1', 'Normal'), ('2', 'Redirected'), ('3', 'Returned')], readonly=True)
    delivery_aras_customer_code = fields.Char(string='Aras Kargo Customer Code', readonly=True)
    delivery_aras_integration_code = fields.Char(string='Aras Kargo Integration Code', readonly=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    delivery_aras_payor_type_code = fields.Selection(string='Aras Kargo Payor Type Code', related='carrier_id.delivery_aras_payor_type_code')

    delivery_aras_piece_count = fields.Integer(string='Aras Kargo Piece Count', compute='_compute_delivery_aras_piece_count', store=True, readonly=True)
    delivery_aras_privilege_order = fields.Boolean(string='Aras Kargo Privilege Order', readonly=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    delivery_aras_special_field_1 = fields.Char(string='Aras Kargo Special Field 1', readonly=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    delivery_aras_special_field_2 = fields.Char(string='Aras Kargo Special Field 2', readonly=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    delivery_aras_special_field_3 = fields.Char(string='Aras Kargo Special Field 3', readonly=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    delivery_aras_cod_ok = fields.Selection(string='Aras Kargo Cash on Delivery', related='carrier_id.delivery_aras_cod_ok')
    delivery_aras_cod_amount = fields.Monetary(string='Aras Kargo Cash on Delivery Amount', currency_field='delivery_aras_currency_id', related='carrier_id.delivery_aras_cod_amount')
    delivery_aras_cod_billing_type = fields.Char(string='Aras Kargo Cash on Delivery Billing Type', related='carrier_id.delivery_aras_cod_billing_type')
    delivery_aras_cod_collection_type = fields.Selection(string='Aras Kargo Cash on Delivery Collection Type', related='carrier_id.delivery_aras_cod_collection_type')
    delivery_aras_currency_id = fields.Many2one('res.currency', string='Aras Kargo Currency', compute='_compute_delivery_aras_currency')

    delivery_aras_description = fields.Char(string='Aras Kargo Description', readonly=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    delivery_aras_reference = fields.Char(string='Aras Kargo Reference', readonly=True)
    delivery_aras_link_reference = fields.Char(string='Aras Kargo Link Reference', readonly=True)
    delivery_aras_tracking_reference = fields.Char(string='Aras Kargo Tracking Reference', readonly=True)
    delivery_aras_departure_branch_name = fields.Char(string='Aras Kargo Departure Branch Name', readonly=True)
    delivery_aras_departure_branch_phone = fields.Char(string='Aras Kargo Departure Branch Phone', readonly=True)
    delivery_aras_departure_date = fields.Char(string='Aras Kargo Departure Date', readonly=True)
    delivery_aras_departure_hour = fields.Char(string='Aras Kargo Departure Hour', readonly=True)
    delivery_aras_arrival_code = fields.Char(string='Aras Kargo Arrival Code', readonly=True)
    delivery_aras_arrival_branch_name = fields.Char(string='Aras Kargo Arrival Branch Name', readonly=True)
    delivery_aras_arrival_branch_phone = fields.Char(string='Aras Kargo Arrival Branch Phone', readonly=True)

    delivery_aras_amount = fields.Monetary(string='Aras Kargo Amount', currency_field='delivery_aras_currency_id', readonly=True)
    delivery_aras_quantity = fields.Char(string='Aras Kargo Quantity', readonly=True)
    delivery_aras_date = fields.Datetime(string='Aras Kargo Date', readonly=True)
    delivery_aras_date_query = fields.Datetime(string='Aras Kargo Query Date', copy=False, readonly=True)
    delivery_aras_value_date = fields.Char(string='Aras Kargo Value Date', readonly=True)
    delivery_aras_volumetric_weight = fields.Char(string='Aras Kargo Volumetric Weight', readonly=True)

    delivery_aras_recipient_name = fields.Char(string='Aras Kargo Recipient Name', readonly=True)
    delivery_aras_recipient_date = fields.Char(string='Aras Kargo Recipient Date', readonly=True)
    delivery_aras_recipient_hour = fields.Char(string='Aras Kargo Recipient Hour', readonly=True)

    delivery_aras_status = fields.Char(string='Aras Kargo Status', readonly=True)
    delivery_aras_status_en = fields.Char(string='Aras Kargo Status EN', readonly=True)
    delivery_aras_status_code = fields.Selection(string='Aras Kargo Status Code', selection=[
        ('1', 'At departure branch'),
        ('2', 'On the way'),
        ('3', 'At arrival branch'),
        ('4', 'On delivery'),
        ('5', 'Partial Delivery'),
        ('6', 'Delivered'),
        ('7', 'Redirected'),
    ], readonly=True)

    delivery_aras_collection_type = fields.Char(string='Aras Kargo Collection Type', readonly=True)
    delivery_aras_collection_amount = fields.Monetary(string='Aras Kargo Collection Amount', currency_field='delivery_aras_currency_id', readonly=True)
    delivery_aras_collection_cancel = fields.Selection(string='Aras Kargo Collection Cancel', selection=[('1', 'Yes'), ('0', 'No')], readonly=True)

    delivery_aras_payment_type = fields.Selection(string='Aras Kargo Payment Type', selection=[('ÜG', 'Sender pays'), ('ÜA', 'Receiver pays')], readonly=True)
    delivery_aras_payment_amount = fields.Monetary(string='Aras Kargo Payment Amount', currency_field='delivery_aras_currency_id', readonly=True)
    delivery_aras_payment_date = fields.Char(string='Aras Kargo Payment Date', readonly=True)

    delivery_aras_return_reason = fields.Char(string='Aras Kargo Return Reason', readonly=True)
    delivery_aras_undelivered_reason = fields.Char(string='Aras Kargo Undelivered Reason', readonly=True)
    delivery_aras_transfer_reason = fields.Char(string='Aras Kargo Transfer Reason', readonly=True)
    delivery_aras_transfer_code = fields.Char(string='Aras Kargo Transfer Code', readonly=True)
    delivery_aras_transfer_description = fields.Char(string='Aras Kargo Transfer Description', readonly=True)

    def update_delivery_aras_state(self, domain=None):
        domain = list(domain) if domain else []
        domain += [
            ('delivery_aras_ok', '=', True),
            ('carrier_tracking_ref', '!=', False),
            ('delivery_aras_status_code', '!=', '6'),
        ]
        if self:
            reference = ','.join(map(str, self.ids))
            domain.append(('id', 'in', self.ids))
        else:
            reference = 'Cronjob'
            date_start = self.env['ir.config_parameter'].sudo().get_param('delivery.aras.date.start', False)
            if date_start:
                domain.append(('create_date', '>', date_start))

        pickings = self.search(domain)
        if not pickings:
            return True
        
        active_pickings = self._cleanup_stale_aras_trackings(pickings)
        if not active_pickings:
            return True

        ctx = dict(self.env.context, reference=reference)

        if self:
            active_pickings.with_context(ctx)._update_delivery_aras_state()
            return True

        job = active_pickings.with_context(ctx)._update_delivery_aras_state()
        return job

    @api.model
    def _update_delivery_aras_state(self):
        if not self:
            return
        reference = self.env.context.get('reference')
        chunk_size = int(self.env.context.get('aras_chunk_size', 50))
        orchestrate = self.env.context.get('aras_orchestrate', True)
        if orchestrate and len(self) > chunk_size:
            groups = {}
            for picking in self:
                key = picking.carrier_id.delivery_aras_connector_id.id or 'default'
                groups.setdefault(key, self.env['stock.picking'])
                groups[key] |= picking
            for connector_id, picking_ids in groups.items():
                refs = picking_ids.mapped('carrier_tracking_ref')
                for i in range(0, len(refs), chunk_size):
                    ref_slice = refs[i:i+chunk_size]
                    subset = picking_ids.filtered(lambda p, rs=set(ref_slice): p.carrier_tracking_ref in rs)
                    desc = _('Aras Cargo chunk (%s) %s-%s') % (connector_id, i+1, i+len(ref_slice))
                    subset.with_context(reference=reference, aras_orchestrate=False).with_delay(channel='root.aras', description=desc)._process_delivery_aras_state_chunk(connector_id)
            return True

        connector_ids = {}
        for picking in self:
            key = picking.carrier_id.delivery_aras_connector_id.id or 'default'
            connector_ids.setdefault(key, self.env['stock.picking'])
            connector_ids[key] |= picking
        for connector_id, picking_ids in connector_ids.items():
            picking_ids._process_delivery_aras_state_chunk(connector_id)
        return True

    def _cleanup_stale_aras_trackings(self, pickings):
        cleanup_days = int(self.env['ir.config_parameter'].sudo().get_param('delivery.aras.cleanup.days', '14'))
        cleanup_date = datetime.now() - timedelta(days=cleanup_days)
        
        stale_pickings = pickings.filtered(
            lambda p: (
                (p.delivery_aras_date_query and p.delivery_aras_date_query < cleanup_date) or
                (not p.delivery_aras_date_query and p.delivery_aras_date and p.delivery_aras_date < cleanup_date) or
                (not p.delivery_aras_date_query and not p.delivery_aras_date and p.create_date < cleanup_date)
            ) and 
            p.delivery_aras_status_code not in ['6'] and
            p.carrier_tracking_ref
        )
        if stale_pickings:
            stale_pickings.write({
                'carrier_tracking_ref': False,
                'delivery_aras_integration_code': False,
                'delivery_aras_customer_code': False,
                'delivery_aras_waybill_number': False,
            })
            
            for picking in stale_pickings:
                picking.message_post(
                    body=_('Aras Cargo tracking reference automatically cleaned. Reason: Record not updated for %d days.') % cleanup_days
                )
        
        active_pickings = pickings - stale_pickings
        return active_pickings

    def _process_delivery_aras_state_chunk(self, connector_id=None):
        if not self:
            return False
        _logger.error('bir kere girdi 2')
        reference = self.env.context.get('reference')
        params = {'reference': ','.join(self.mapped('carrier_tracking_ref'))}
        connectors = self.env['syncops.connector'].sudo().browse(connector_id) if connector_id != 'default' else self.env['syncops.connector']
        result = self.env['syncops.connector'].sudo()._execute('delivery_get_order', params=params, reference=reference, connectors=connectors) or []
        for res in result:
            try:
                picking = self.filtered(lambda p: p.carrier_tracking_ref == res['customer_code'])
                if not picking:
                    continue

                update_values = {
                    'delivery_aras_integration_code': res['customer_code'],
                    'delivery_aras_customer_code': res['customer_code'],
                    'delivery_aras_waybill_number': res['waybill_number'],
                    'delivery_aras_sender': res['sender'],
                    'delivery_aras_receiver': res['receiver'],
                    'delivery_aras_link_reference': res['link_reference'],
                    'delivery_aras_tracking_reference': res['tracking_reference'],
                    'delivery_aras_departure_branch_name': res['departure_branch_name'],
                    'delivery_aras_departure_branch_phone': res['departure_branch_phone'],
                    'delivery_aras_arrival_branch_name': res['arrival_branch_name'],
                    'delivery_aras_arrival_branch_phone': res['arrival_branch_phone'],
                    'delivery_aras_departure_date': res['departure_date'],
                    'delivery_aras_departure_hour': res['departure_hour'],
                    'delivery_aras_quantity': res['quantity'],
                    'delivery_aras_volumetric_weight': res['volumetric_weight'],
                    'delivery_aras_payment_type': res['payment_type'],
                    'delivery_aras_amount': res['amount'] and float(res['amount']) or 0,
                    'delivery_aras_reference': res['reference'],
                    'delivery_aras_recipient_name': res['recipient_name'],
                    'delivery_aras_recipient_date': res['recipient_date'],
                    'delivery_aras_recipient_hour': res['recipient_hour'],
                    'delivery_aras_type_code': res['type_code'],
                    'delivery_aras_arrival_code': res['arrival_code'],
                    'delivery_aras_status_code': res['status_code'],
                    'delivery_aras_collection_cancel': res['collection_cancel'],
                    'delivery_aras_status': res['status'],
                    'delivery_aras_export_code': res['export_code'],
                    'delivery_aras_delivery_code': res['delivery_code'],
                    'delivery_aras_status_en': res['status_en'],
                    'delivery_aras_collection_amount': res['collection_amount'] and float(res['collection_amount']) or 0,
                    'delivery_aras_collection_type': res['collection_type'],
                    'delivery_aras_value_date': res['value_date'],
                    'delivery_aras_payment_amount': res['payment_amount'] and float(res['payment_amount']) or 0,
                    'delivery_aras_payment_date': res['payment_date'],
                    'delivery_aras_undelivered_reason': res['undelivered_reason'],
                    'delivery_aras_return_reason': res['return_reason'],
                    'delivery_aras_transfer_reason': res['transfer_reason'],
                    'delivery_aras_transfer_code': res['transfer_code'],
                    'delivery_aras_transfer_description': res['transfer_description'],
                    'delivery_aras_date': datetime.strptime(res['date'], '%Y%m%d %H:%M:%S') - timedelta(hours=3),
                }
                
                picking.write(update_values)

            except psycopg2.errors.SerializationFailure:
                self.env.cr.rollback()
                continue

            except Exception as e:
                _logger.error('An error occurred when getting Aras Cargo delivery orders: %s\n%s' % (e, json.dumps(res, default=str, indent=4, ensure_ascii=False)))

            self.env.cr.commit()
        
        now = fields.Datetime.now().strftime(DTF)
        for picking in self:
            self.env.cr.execute('UPDATE stock_picking SET delivery_aras_date_query=%s WHERE id=%s', (now, picking.id))
        
        return True

    def cancel_shipment(self):
        for picking in self:
            res = self.env['syncops.connector'].sudo()._execute('delivery_patch_order_cancel', params={'reference': picking.carrier_tracking_ref})
            if not res:
                raise ValidationError(_('An error occured. Please check the logs for further detail.'))

            for r in res:
                if not r['result_code'] == '0':
                    raise ValidationError(r['result_message'])

            picking.write({
                'delivery_aras_integration_code': False,
                'delivery_aras_customer_code': False,
                'delivery_aras_waybill_number': False,
                'delivery_aras_sender': False,
                'delivery_aras_receiver': False,
                'delivery_aras_link_reference': False,
                'delivery_aras_tracking_reference': False,
                'delivery_aras_departure_branch_name': False,
                'delivery_aras_departure_branch_phone': False,
                'delivery_aras_arrival_branch_name': False,
                'delivery_aras_arrival_branch_phone': False,
                'delivery_aras_departure_date': False,
                'delivery_aras_departure_hour': False,
                'delivery_aras_quantity': False,
                'delivery_aras_volumetric_weight': False,
                'delivery_aras_payment_type': False,
                'delivery_aras_amount': False,
                'delivery_aras_reference': False,
                'delivery_aras_recipient_name': False,
                'delivery_aras_recipient_date': False,
                'delivery_aras_recipient_hour': False,
                'delivery_aras_type_code': False,
                'delivery_aras_arrival_code': False,
                'delivery_aras_status_code': False,
                'delivery_aras_collection_cancel': False,
                'delivery_aras_status': False,
                'delivery_aras_export_code': False,
                'delivery_aras_delivery_code': False,
                'delivery_aras_status_en': False,
                'delivery_aras_collection_amount': False,
                'delivery_aras_collection_type': False,
                'delivery_aras_value_date': False,
                'delivery_aras_payment_amount': False,
                'delivery_aras_payment_date': False,
                'delivery_aras_undelivered_reason': False,
                'delivery_aras_return_reason': False,
                'delivery_aras_transfer_reason': False,
                'delivery_aras_transfer_code': False,
                'delivery_aras_transfer_description': False,
                'delivery_aras_date': False,
            })
            self.env.cr.commit()

        return super(StockPicking, self).cancel_shipment()
