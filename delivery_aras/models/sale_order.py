# -*- coding: utf-8 -*-
from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def get_delivery_aras_data(self, domain):
        data = []
        sale = self.env['sale.order'].search(domain, limit=1)
        for picking in sale.picking_ids:
            if picking.delivery_aras_status:
                products = picking.move_ids_without_package.mapped('product_id')
                for product in products:
                    data.append({
                        'product_id': product.id,
                        'product_code': product.default_code,
                        'sale_id': picking.sale_id.id,
                        'sale_name': picking.sale_id.name,
                        'picking_id': picking.id,
                        'picking_name': picking.name,
                        'date': picking.delivery_aras_date,
                        'customer_code': picking.delivery_aras_customer_code,
                        'waybill_number': picking.delivery_aras_waybill_number,
                        'sender': picking.delivery_aras_sender,
                        'receiver': picking.delivery_aras_receiver,
                        'link_reference': picking.delivery_aras_link_reference,
                        'tracking_reference': picking.delivery_aras_tracking_reference,
                        'export': picking.delivery_aras_export_code,
                        'quantity': picking.delivery_aras_quantity,
                        'volumetric_weight': picking.delivery_aras_volumetric_weight,
                        'departure_branch_name': picking.delivery_aras_departure_branch_name,
                        'departure_hour': picking.delivery_aras_departure_hour,
                        'amount': picking.delivery_aras_amount,
                        'payment_amount': picking.delivery_aras_payment_amount,
                        'payment_type': picking.delivery_aras_payment_type,
                        'collection_amount': picking.delivery_aras_collection_amount,
                        'recipient_name': picking.delivery_aras_recipient_name,
                        'recipient_date': picking.delivery_aras_recipient_date,
                        'recipient_hour': picking.delivery_aras_recipient_hour,
                        'type_code': picking.delivery_aras_type_code,
                        'status': picking.delivery_aras_status,
                        'status_code': picking.delivery_aras_status_code,
                        'delivery_code': picking.delivery_aras_delivery_code,
                        'status_en': picking.delivery_aras_status_en,
                        'value_date': picking.delivery_aras_value_date,
                        'payment_date': picking.delivery_aras_payment_date,
                        'return_reason': picking.delivery_aras_return_reason,
                        'transfer_reason': picking.delivery_aras_transfer_reason,
                        'transfer_code': picking.delivery_aras_transfer_code,
                        'transfer_description': picking.delivery_aras_transfer_description,
                    })
        return data
