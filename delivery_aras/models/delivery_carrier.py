# -*- coding: utf-8 -*-
import random
from odoo import models, fields, _
from odoo.exceptions import ValidationError


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    def _compute_delivery_aras_currency(self):
        currency = self.env['res.currency'].sudo().with_context(active_test=False).search([('name', '=', 'TRY')])
        for delivery in self:
            delivery.delivery_aras_currency_id = currency.id

    delivery_type = fields.Selection(selection_add=[('aras', 'Aras Kargo')], ondelete={'aras': 'set default'})
    delivery_aras_payor_type_code = fields.Selection(string='Aras Kargo Payor Type Code', selection=[('1', 'Counterparty Payment'), ('0', 'Consignee Payment')])
    delivery_aras_cod_ok = fields.Selection(string='Aras Kargo Cash on Delivery', selection=[('1', 'Yes'), ('0', 'No')])
    delivery_aras_cod_collection_type = fields.Selection(string='Aras Kargo Cash on Delivery Collection Type', selection=[('1', 'Cash'), ('6', 'Credit Card')])
    delivery_aras_cod_amount = fields.Monetary(string='Aras Kargo Cash on Delivery Amount', currency_field='delivery_aras_currency_id')
    delivery_aras_cod_billing_type = fields.Char(string='Aras Kargo Cash on Delivery Billing Type', default=0)
    delivery_aras_currency_id = fields.Many2one('res.currency', string='Aras Kargo Currency', readonly=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, compute='_compute_delivery_aras_currency')
    delivery_aras_connector_id = fields.Many2one('syncops.connector', string='Aras Kargo Connector')

    def aras_send_shipping(self, pickings):
        result = []
        for picking in pickings:
            random_number = ''.join(random.choice('0123456789') for _ in range(15))
            params = {
                'reference': random_number,
                'dispatch_number': getattr(picking, 'document_number', picking.name),
                'invoice_number': picking.delivery_aras_invoice_number,
                'receiver_name': picking.delivery_aras_receiver_name,
                'receiver_address': picking.delivery_aras_receiver_address,
                'receiver_phone': picking.delivery_aras_receiver_phone,
                'receiver_city': picking.delivery_aras_receiver_city,
                'receiver_town': picking.delivery_aras_receiver_town,
                'piece_count': picking.delivery_aras_piece_count,
                'is_cod': picking.delivery_aras_cod_ok,
                'payor_type_code': picking.delivery_aras_payor_type_code,
                'piece_details': [{'PieceDetail': []}],
                'warehouse_code' : picking.location_id.warehouse_id.delivery_aras_code or ''
            }
            for i, product in enumerate(picking.move_ids_without_package):
                product.delivery_aras_product_barcode = random_number + '{:02}'.format(i)
                params['piece_details'][0]['PieceDetail'].append({
                    'ProductNumber': product.product_id.id,
                    'Weight': max(product.product_id.weight, 2),
                    'VolumetricWeight': max(product.product_id.volume, 2),
                    'BarcodeNumber': random_number + '{:02}'.format(i),
                })
            connector = picking.carrier_id.delivery_aras_connector_id
            res = self.env['syncops.connector'].sudo()._execute('delivery_post_order', params=params, connectors=connector)
            if not res:
                raise ValidationError(_('An error occured. Please check the logs for further detail.'))

            for r in res:
                if not r['result_code'] == '0':
                    raise ValidationError(r['result_message'])
                r.update({'exact_price': 0})

            result.extend(res)
        return result
