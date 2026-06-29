# -*- coding: utf-8 -*-
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_picking_tracking_url(self):
        self.ensure_one()
        picking = self.env['stock.picking'].search([
            ('sale_id', '=', self.id),
            ('carrier_id', '!=', False),
            ('carrier_tracking_url', '!=', False),
        ], order='id desc', limit=1)

        if picking:
            return {
                'type': 'ir.actions.act_url',
                'url': picking.carrier_tracking_url,
                'target': 'new',
            }
        return {}
