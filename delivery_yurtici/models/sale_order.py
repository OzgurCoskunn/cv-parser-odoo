# -*- coding: utf-8 -*-

from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_tracking_yurtici_ids = fields.One2many('delivery.tracking', 'sale_order_id', string='Yurtiçi Kargo Delivery Tracking Status', domain=[('carrier_id.delivery_type', '=', 'yurtici')])
