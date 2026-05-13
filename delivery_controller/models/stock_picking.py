# -*- coding: utf-8 -*-
from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delivery_method_ok = fields.Boolean(string='Delivery Method')

    def action_delivery_method_toggle(self):
        for line in self:
            if line.delivery_method_ok:
                line.delivery_method_ok = False
                if line.carrier_id and line.state != 'done':
                    line.carrier_id = False
            else:
                line.delivery_method_ok = True
                if not line.carrier_id and line.state != 'done':
                    line.carrier_id = self.env['delivery.carrier'].search([('preferred', '=', True)], limit=1).id
