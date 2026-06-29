# -*- coding: utf-8 -*-

from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_tracking_hepsijet_ids = fields.One2many('delivery.tracking', 'sale_order_id', string='HepsiJet Delivery Tracking Status', domain=[('carrier_id.delivery_type', '=', 'hepsijet')])

    def action_retrigger_stock(self):
        for order in self:
            pickings_to_reset = order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
            if pickings_to_reset:
                pickings_to_reset.write({'syncops_connector_id': False})
        self.order_line._action_launch_stock_rule()