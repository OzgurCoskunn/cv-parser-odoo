# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    barcode_warehouse_create_method = fields.Selection(related='company_id.barcode_warehouse_create_method', readonly=False)
    barcode_save_before_closing = fields.Boolean(related='company_id.barcode_save_before_closing', readonly=False)

    @api.onchange('barcode_warehouse_create_method')
    def _onchange_barcode_warehouse_create_method(self):
        picking_types = self.env['stock.picking.type'].search([])
        for picking_type in picking_types:
            picking_type.barcode_lot_create_method = self.barcode_warehouse_create_method
