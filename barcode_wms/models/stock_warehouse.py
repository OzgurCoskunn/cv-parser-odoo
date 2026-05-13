# -*- coding: utf-8 -*-
from odoo import models, fields


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    user_ids = fields.Many2many('res.users', string='Operation Users')
    internal_location_ids = fields.One2many('stock.location', 'warehouse_id', domain=[('usage', '=', 'internal')])
