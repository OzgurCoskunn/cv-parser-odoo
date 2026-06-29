# -*- coding: utf-8 -*-
from odoo import models, fields, _


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('ptt', 'Ptt Kargo')], ondelete={'ptt': 'set default'})
    delivery_ptt_connector_id = fields.Many2one('syncops.connector', 'Ptt Kargo Connector')

    def toggle_prod_environment(self):
        super().toggle_prod_environment()
        for delivery in self:
            if delivery.delivery_type == 'ptt':
                delivery.delivery_ptt_connector_id.environment = delivery.prod_environment

    def ptt_send_shipping(self, pickings):
        result = []
        for picking in pickings:
            params = {
                'receiver_name': picking.partner_id.name,
                'receiver_address': picking.partner_id._display_address(without_company=True),
                'city': picking.partner_id.state_id.code,
                'district': picking.partner_id.city,
                'phone': picking.partner_id.phone,
                'weight': sum([x.product_id.weight * x.product_uom_qty for x in picking.move_ids_without_package]),
                'ref': picking._delivery_ptt_generate_barcode(),
            }
            res = self.env['syncops.connector'].sudo()._execute('delivery_post_order', params=params, reference=str(picking.id), connectors=self.delivery_ptt_connector_id)
            if not res:
                picking.write({
                    'delivery_ptt_connector_ok': True,
                    'delivery_ptt_connector_state': False,
                    'delivery_ptt_connector_message': _('An error occured. Please check the logs for further detail.'),
                })
            else:
                r = res[0]
                if r['error_code'] != '1':
                    picking.write({
                        'delivery_ptt_connector_ok': True,
                        'delivery_ptt_connector_state': False,
                        'delivery_ptt_connector_message': r.get('description') or _('Connector process failed.'),
                    })
                else:
                    r = r['result'][0]
                    result.append(r)
                    picking.write({
                        'carrier_id': self.id,
                        'carrier_tracking_ref': r.get('barkod', False) or False,
                        'delivery_ptt_tracking_url': r.get('donguAciklama', False),
                        'carrier_doc_id': res[0].get('document_name', False) or False,
                        'delivery_ptt_connector_ok': True,
                        'delivery_ptt_connector_state': True,
                        'delivery_ptt_connector_message': _('Connector process succeeded.'),
                    })

        if not result:
            return [{'exact_price': 0, 'tracking_number': False}]
        for r in result:
            r.update({'exact_price': 0, 'tracking_number': r['barkod']})
        return result

    def ptt_get_tracking_link(self, picking):
        return picking.delivery_ptt_tracking_url 
