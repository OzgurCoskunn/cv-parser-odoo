# -*- coding: utf-8 -*-
from odoo import models, fields


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    delivery_aras_code = fields.Char(string='Aras Kargo Code')
