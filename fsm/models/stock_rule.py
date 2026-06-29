# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.osv.expression import AND


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _search_rule(self, route_ids, packaging_uom_id, product_id, warehouse_id, domain):
        location = self.env.context.get('location')
        if location:
            domain = AND([[('location_src_id', '=', location.id)], domain])
        return super()._search_rule(route_ids, packaging_uom_id, product_id, warehouse_id, domain)

