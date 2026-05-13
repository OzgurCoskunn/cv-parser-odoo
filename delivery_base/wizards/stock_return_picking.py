# -*- coding: utf-8 -*-
from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def create_returns_without_carrier(self):
            return self.with_context(skip_carrier=True).create_returns()
