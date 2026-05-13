# -*- coding: utf-8 -*-
from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    delivery_aras_product_barcode = fields.Char(string='Aras Kargo Product Barcode')
