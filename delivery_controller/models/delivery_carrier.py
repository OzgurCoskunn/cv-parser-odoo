# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import ValidationError


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    preferred = fields.Boolean(string='Preferred')

    def send_shipping(self, pickings):
        if self.env.context.get('no_shipping'):
            return [{'exact_price': 0, 'tracking_number': pickings[0]['carrier_tracking_ref'] or ''}]
        return super().send_shipping(pickings)

        # Code which is overriden
        self.ensure_one()
        if hasattr(self, '%s_send_shipping' % self.delivery_type):
            return getattr(self, '%s_send_shipping' % self.delivery_type)(pickings)

        # Code which overrides before
        self.ensure_one()
        if hasattr(self, '%s_send_shipping' % self.delivery_type):
            res = getattr(self, '%s_send_shipping' % self.delivery_type)(pickings)
            if res[0].get('tracking_number') is not False:
                return res

            carriers = self.env['delivery.carrier'].search([
                ('preferred', '=', True),
                ('id', '!=', self.id),
            ])
            for carrier in carriers:
                if hasattr(carrier, '%s_send_shipping' % carrier.delivery_type):
                    res = getattr(carrier, '%s_send_shipping' % carrier.delivery_type)(pickings)
                    if res[0].get('tracking_number') is not False:
                        pickings.write({'carrier_id': carrier.id})
                        return res

            raise ValidationError(_('Any preferred delivery method could not been initiated.'))