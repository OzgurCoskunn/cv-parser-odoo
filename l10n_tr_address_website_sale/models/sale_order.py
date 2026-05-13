# -*- coding: utf-8 -*-
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    def write(self, values):
        if 'partner_id' in values and not values['partner_id'] or \
           'partner_invoice_id' in values and not values['partner_invoice_id']:
            return True

        if 'partner_invoice_id' in values and 'website_id' in self.env.context:
            partner = self.env['res.partner'].sudo().browse(values['partner_invoice_id'])
            parent = partner.commercial_partner_id
            values['partner_invoice_id'] = parent.id
        return super().write(values)
