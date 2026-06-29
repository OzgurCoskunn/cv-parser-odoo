# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    fsm_subpartner_id = fields.Many2one('res.partner', string='Field Service Subpartner')

    @api.model
    def _get_inventory_fields_write(self):
        return super()._get_inventory_fields_write() + ['fsm_subpartner_id']

    @api.model
    def get_user_action(self):
        view = self.sudo().env.ref('stock.view_stock_quant_tree')
        if view:
            return {
                'name': _('Products'),
                'type': 'ir.actions.act_window',
                'target': 'fullscreen',
                'res_model': 'stock.quant',
                'views': [(view.id, 'tree')],
                'context': {
                    'create': False,
                    'edit': False,
                    'delete': False,
                    'group_by': ['location_id', 'product_id'],
                }
            }
        return False

    @api.model
    def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, strict=False):
        quants = self.env.context.get('quants')
        if quants:
            return quants
        return super()._update_reserved_quantity(product_id, location_id, quantity, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
