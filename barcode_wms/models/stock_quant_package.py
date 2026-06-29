# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    @api.model
    def print_package(self, move):
        package = self.search([('name', '=', move)])
        if package:
            return package.print(package.id)
        


    def print(self, package_id):
        package_report = self.env.ref('stock.action_report_quant_package_barcode_small')
        
        return package_report.report_action(package_id)