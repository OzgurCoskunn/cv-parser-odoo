# -*- coding: utf-8 -*-
import random

from odoo import models, fields, _
from odoo.exceptions import ValidationError

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('yurtici', 'Yurtiçi Kargo')], ondelete={'yurtici': 'set default'})
    delivery_yurtici_connector_id = fields.Many2one('syncops.connector', 'Yurtiçi Kargo Connector')
    delivery_yurtici_return_connector_id = fields.Many2one('syncops.connector', 'Yurtiçi Kargo Return Connector')

    def toggle_prod_environment(self):
        super().toggle_prod_environment()
        for delivery in self:
            if delivery.delivery_type == 'yurtici':
                delivery.delivery_yurtici_connector_id.environment = delivery.prod_environment
                if delivery.delivery_yurtici_return_connector_id:
                    delivery.delivery_yurtici_return_connector_id.environment = delivery.prod_environment

    def yurtici_send_shipping(self, pickings):
        result = []
        for picking in pickings:
            partner = picking._yurtici_get_partner()
            params = {
                'reference': ''.join(random.choice('0123456789') for _ in range(10)),
                'dispatch_number': getattr(picking, 'document_number', picking.name),
                'receiver_name': partner.name,
                'receiver_address': partner._display_address(without_company=True),
                'receiver_phone': partner.phone,
                'receiver_mobile': partner.mobile,
                'receiver_city': partner.state_id.name,
                'tax_office_id': picking.company_id.vat,
                'cargo_count': picking.number_of_packages or 1,
            }
            connectors = picking.syncops_connector_id or self.delivery_yurtici_connector_id
            res, message = self.env['syncops.connector'].sudo()._execute('delivery_post_order', params=params, reference=str(picking.id), connectors=connectors, message=True)
            if not res:
                raise ValidationError(message)
                picking.write({
                    'delivery_yurtici_connector_ok': True,
                    'delivery_yurtici_connector_state': False,
                    'delivery_yurtici_connector_message': message,
                })
            else:
                r = res[0]
                if r['flag'] != '0':
                    picking.write({
                        'delivery_yurtici_connector_ok': True,
                        'delivery_yurtici_connector_state': False,
                        'delivery_yurtici_connector_message': r.get('result') or _('Connector process failed.'),
                    })
                else:
                    r = r['data'][0]
                    result.append(r)
                    picking.write({
                        'carrier_id': self.id,
                        'carrier_tracking_ref': r.get('cargoKey', False) or False,
                        'delivery_yurtici_connector_ok': True,
                        'delivery_yurtici_connector_state': True,
                        'delivery_yurtici_connector_message': _('Connector process succeeded.'),
                    })

        if not picking.syncops_connector_id:
            picking.write({'syncops_connector_id': self.delivery_yurtici_connector_id.id})

        self.env.cr.commit()
        if not result:
            return [{'exact_price': 0, 'tracking_number': False}]
        for r in result:
            r.update({'exact_price': 0, 'tracking_number': r['cargoKey']})
        return result

    def yurtici_get_tracking_link(self, picking):
        return 'https://www.yurticikargo.com/tr/online-servisler/gonderi-sorgula?code={}'.format(picking.carrier_doc_id)
