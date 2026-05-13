# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    barcode_warehouse_create_method = fields.Selection([
        ('no', 'None'),
        ('warning', 'Warning'),
        ('block', 'Block'),
    ], string='Barcode Warehouse Operations Line Creation Method', default='no')
    barcode_save_before_closing = fields.Boolean(string='Barcode Save Before Closing')

    def write(self, values):
        res = super().write(values)
        if 'barcode_warehouse_create_method' in values:
            types = self.env['stock.picking.type'].search([('company_id', 'in', self.ids)])
            types.write({'barcode_lot_create_method': values['barcode_warehouse_create_method']})
        return res
