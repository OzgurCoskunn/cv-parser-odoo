# -*- coding: utf-8 -*-
from odoo import models, fields


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    #def send_shipping(self, pickings):
    #    self.ensure_one()
    #    if pickings.env.context.get('shipping'):
    #        return pickings.env.context['shipping']
    #    return super().send_shipping(pickings)

    delivery_status_mapping_ids = fields.One2many('delivery.status.mapping', 'carrier_id', string='Delivery Status Mappings')

    def render_contract(self, picking, code=None):
        self.ensure_one()
        if hasattr(self, '%s_render_contract' % self.delivery_type):
            return getattr(self, '%s_render_contract' % self.delivery_type)(picking, code=code)
        return None
