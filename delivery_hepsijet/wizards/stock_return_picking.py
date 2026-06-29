# -*- coding: utf-8 -*-
import uuid
import random
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.model
    def default_get(self, fields):
        res = super(StockReturnPicking, self).default_get(fields)
        picking = self.env['stock.picking']
        if 'picking_id' in res:
            picking = picking.browse(res['picking_id'])
        if not picking and 'picking' in self.env.context:
            picking = self.env.context.get('picking')

        if picking.carrier_id.delivery_type == 'hepsijet':
            res.update({
                'delivery_hepsijet_ok': True,
                'delivery_hepsijet_partner_id': picking.partner_id.id,
                'delivery_hepsijet_carrier_id': picking.carrier_id.id,
                'delivery_hepsijet_connector_id': picking.syncops_connector_id.id or picking.carrier_id.delivery_hepsijet_connector_id.id,
                'delivery_hepsijet_company_id': picking.company_id.id,
                'delivery_hepsijet_date_start': datetime.now().date(),
                'delivery_hepsijet_date_end': datetime.now().date() + timedelta(days=picking.carrier_id.delivery_hepsijet_return_day_range),
            })
            #res['delivery_hepsijet_date_suitable'] = self._get_return_date({
            #    "start_date": res['delivery_hepsijet_date_start'].strftime("%Y-%m-%d"),
            #    "end_date": res['delivery_hepsijet_date_end'].strftime("%Y-%m-%d"),
            #    "city": picking.partner_id.state_id.name,
            #    "town": picking.partner_id.city,
            #}, reference=str(picking.id))
        return res

    delivery_hepsijet_ok = fields.Boolean(string='Is HepsiJet')
    delivery_hepsijet_date_start = fields.Date(string='HepsiJet Start Date')
    delivery_hepsijet_date_end = fields.Date(string='HepsiJet End Date')
    delivery_hepsijet_date_compute = fields.Boolean(string='HepsiJet Compute Date')
    delivery_hepsijet_date_suitable = fields.Date(string='HepsiJet Suitable Date')
    delivery_hepsijet_partner_id = fields.Many2one('res.partner', string='Partner')
    delivery_hepsijet_connector_id = fields.Many2one('syncops.connector')
    delivery_hepsijet_carrier_id = fields.Many2one('delivery.carrier')
    delivery_hepsijet_company_id = fields.Many2one('res.company')

    def _get_return_date(self, params, reference='', msg=False):
        connectors = self.delivery_hepsijet_connector_id
        result, message = self.env['syncops.connector'].sudo()._execute('delivery_get_return_date', params=params, reference=reference, connectors=connectors, message=True)
        if result is None:
            if msg:
                raise ValidationError(message)
                #raise ValidationError(_('Suitable dates cannot be retrieved.'))
            return False
        return result[0]['data']

    @api.onchange('delivery_hepsijet_date_compute')
    def action_get_return_date(self):
        if self.env.context.get('button') and self.delivery_hepsijet_ok:
            self.delivery_hepsijet_date_suitable = self._get_return_date({
                "start_date": self.delivery_hepsijet_date_start.strftime("%Y-%m-%d"),
                "end_date": self.delivery_hepsijet_date_end.strftime("%Y-%m-%d"),
                "city": self.delivery_hepsijet_partner_id.state_id.name,
                "town": self.delivery_hepsijet_partner_id.city,
            }, reference=str(self.picking_id.id or ''), msg=True)

    def create_returns(self):
        if self.env.context.get('skip_carrier'):
            return super(StockReturnPicking, self).create_returns()

        receiver = self.delivery_hepsijet_partner_id
        sender = self.picking_id.with_context(location=self.location_id)._hepsijet_get_sender()
        order_id = ''

        if self.delivery_hepsijet_ok:
            if self.delivery_hepsijet_date_suitable:
                delivery = self.delivery_hepsijet_carrier_id
                env_code = 'prod' if delivery.prod_environment else 'test'
                company_name = getattr(delivery, 'delivery_hepsijet_%s_company_name' % env_code, '')
                abbreviation_code = getattr(delivery, 'delivery_hepsijet_%s_abbreviation_code' % env_code, '')
                application_code = getattr(delivery, 'delivery_hepsijet_%s_application_code' % env_code, '')
                address_code = getattr(delivery, 'delivery_hepsijet_%s_address_code' % env_code, '')
                address_code_return = getattr(delivery, 'delivery_hepsijet_%s_address_code_return' % env_code, '')
                username = getattr(delivery, 'delivery_hepsijet_%s_username' % env_code, '')
                password = getattr(delivery, 'delivery_hepsijet_%s_password' % env_code, '')
                company_id = getattr(delivery, 'delivery_hepsijet_%s_company_id' % env_code, '')
                order_id = delivery._hepsijet_get_order_id(delivery.delivery_hepsijet_prefix_product_return)

                params = {
                    "company": {
                        "name": company_name,
                    },
                    "delivery": {
                        "totalParcels": len(self.product_return_moves),
                        "desi": sum(self.product_return_moves.mapped('product_id.weight')) or 1,
                        "deliverySlotOriginal": "0",
                        "deliveryDateOriginal": self.delivery_hepsijet_date_suitable.strftime("%Y-%m-%d"), 
                        "deliveryType": "RETURNED",
                        "product": {
                            "productCode": "HX_STD"
                        },
                        "senderAddress": {
                            "country": {
                                "name": receiver.country_id.name
                            },
                            "city": {
                                "name": receiver.state_id.name
                            },
                            "town": {
                                "name": receiver.city
                            },
                            "district": {
                                "name": receiver.street
                            },
                            "addressLine1": self.delivery_hepsijet_carrier_id._hepsijet_get_address(receiver),
                        },
                        "receiver": {
                            "firstName": receiver.name,
                            "lastName": receiver.name,
                            "phone1": receiver.phone,
                            "phone2": receiver.mobile,
                            "email": receiver.email,
                        },
                        "recipientAddress": {
                            "country": {
                                "name": sender.country_id.name or ''
                            },
                            "city": {
                                "name": sender.state_id.name or ''
                            },
                            "town": {
                                "name": sender.city or ''
                            },
                            "district": {
                                "name": sender.street or ''
                            },
                            "addressLine1": self.delivery_hepsijet_carrier_id._hepsijet_get_address(sender),
                        },
                        "recipientPerson": self.delivery_hepsijet_company_id.name,
                        "recipientPersonPhone1": self.delivery_hepsijet_company_id.phone,
                    },
                    "warehouse": {
                        "code" : self.location_id.warehouse_id.delivery_hepsijet_code or ''
                    }
                }

                params.update({
                    'username': username,
                    'password': password,
                    'companyId': company_id,
                    'abbreviationCode': abbreviation_code,
                    'applicationCode': application_code,
                    'addressCode': address_code_return or address_code or '',
                    'orderId': order_id,
                })

                syncops_log_ref = str(uuid.uuid4())
                connectors = self.delivery_hepsijet_connector_id
                result = self.env['syncops.connector'].sudo()._execute('delivery_post_order_return', params=params, reference=syncops_log_ref, connectors=connectors)
                if result is None:
                    raise ValidationError(_('An error occured. Please check the logs for further detail.'))

                result = result[0]
                if result.get('status') == 'FAIL':
                    raise ValidationError(result['message'])
                elif 'data' not in result or 'customerDeliveryNo' not in result['data']:
                    raise ValidationError(_('An error occured. Please check the logs for further detail.'))

                values = {
                    'carrier_state': False, 
                    'carrier_id': self.delivery_hepsijet_carrier_id.id,
                    'partner_id': self.delivery_hepsijet_partner_id.id,
                    'scheduled_date': self.delivery_hepsijet_date_suitable,
                    'carrier_tracking_ref': result['data']['customerDeliveryNo'],
                    'syncops_log_ref': syncops_log_ref,
                }
                res = super(StockReturnPicking, self.with_context(values=values)).create_returns()
                if 'res_id' in res:
                    self.env['stock.picking'].browse(res['res_id']).write(values)
                return res
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('HepsiJet Return Date'),
                    'res_model': 'stock.return.picking.hepsijet.warning',
                    'context': {'default_return_id': self.id},
                    'view_mode': 'form',
                    'target': 'new',
                }
        return super(StockReturnPicking, self).create_returns()
