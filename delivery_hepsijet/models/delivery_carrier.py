# -*- coding: utf-8 -*-
import re
import random
from markupsafe import Markup
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class DeliveryCarrierHepsijetContract(models.Model):
    _name = 'delivery.carrier.hepsijet.contract'
    _description = 'Delivery: HepsiJet Contracts'
    _order = 'sequence, id desc'

    name = fields.Char(required=True)
    code = fields.Char()
    version = fields.Char()
    body = fields.Html(sanitize=False)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def render(self, picking, body=None):
        if not body:
            body = self.body

        return self.env['mail.render.mixin']._render_template(body, picking._name, picking.ids, engine='qweb')[picking.id]


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    @api.depends('delivery_type')
    def _compute_delivery_hepsijet_contract_product_id(self):
        for delivery in self:
            if delivery.delivery_type == 'hepsijet':
                delivery.delivery_hepsijet_contract_product_id = self.env.ref('delivery_hepsijet.product_contract').id
            else:
                delivery.delivery_hepsijet_contract_product_id = False

    delivery_type = fields.Selection(selection_add=[('hepsijet', 'HepsiJet')], ondelete={'hepsijet': 'set default'})
    delivery_hepsijet_return_day_range = fields.Integer('HepsiJet Return Day Range', default=7)
    delivery_hepsijet_connector_id = fields.Many2one('syncops.connector', 'HepsiJet Connector')
    delivery_hepsijet_contract_id = fields.Many2one('delivery.carrier.hepsijet.contract')
    delivery_hepsijet_contract_product_id = fields.Many2one('product.product', compute='_compute_delivery_hepsijet_contract_product_id')

    delivery_hepsijet_prod_company_name = fields.Char('Delivery HepsiJet Production Company Name')
    delivery_hepsijet_prod_contract_application_code = fields.Char(string='Delivery HepsiJet Production Contract Application Code')
    delivery_hepsijet_prod_address_code = fields.Char(string='Delivery HepsiJet Production Address Code')
    delivery_hepsijet_prod_address_code_return = fields.Char('Delivery HepsiJet Production Return Address Code')
    delivery_hepsijet_prod_abbreviation_code = fields.Char(string='Delivery HepsiJet Production Abbreviation Code')

    delivery_hepsijet_prefix_contract = fields.Char(string='Delivery HepsiJet Contract Prefix')
    delivery_hepsijet_prefix_product = fields.Char(string='Delivery HepsiJet Product Prefix')
    delivery_hepsijet_prefix_egyg = fields.Char(string='Delivery HepsiJet EGYG Prefix')
    delivery_hepsijet_prefix_egyg_return = fields.Char(string='Delivery HepsiJet EGYG Return Prefix')
    delivery_hepsijet_prefix_product_return = fields.Char(string='Delivery HepsiJet Return Product Prefix')
    delivery_hepsijet_prefix_product_contract = fields.Char(string='Delivery HepsiJet Product Contract Prefix')

    delivery_hepsijet_test_company_name = fields.Char('Delivery HepsiJet Test Company Name')
    delivery_hepsijet_test_contract_application_code = fields.Char(string='Delivery HepsiJet Test Contract Application Code')
    delivery_hepsijet_test_address_code = fields.Char(string='Delivery HepsiJet Test Address Code')
    delivery_hepsijet_test_address_code_return = fields.Char('Delivery HepsiJet Test Return Address Code')
    delivery_hepsijet_test_abbreviation_code = fields.Char(string='Delivery HepsiJet Test Abbreviation Code')

    delivery_hepsijet_prod_username = fields.Char(string='Delivery HepsiJet Production Username')
    delivery_hepsijet_prod_password = fields.Char(string='Delivery HepsiJet Production Password')
    delivery_hepsijet_prod_company_id = fields.Char(string='Delivery HepsiJet Production Company ID')

    delivery_hepsijet_test_username = fields.Char(string='Delivery HepsiJet Test Username')
    delivery_hepsijet_test_password = fields.Char(string='Delivery HepsiJet Test Password')
    delivery_hepsijet_test_company_id = fields.Char(string='Delivery HepsiJet Test Company ID')

    def _hepsijetNormalizeDistrict(self, district):
        if 'Mh.' not in district or 'Mah.' not in district:
            return district + ' Mah.'
        return district

    @api.model
    def _hepsijet_get_address(self, partner):
        address = []
        if partner.street:
            address.append(self._hepsijetNormalizeDistrict(partner.street))
        if partner.street2:
            address.append(partner.street2)
        if partner.street3:
            address.append(partner.street3)
        if partner.city:
            address.append(partner.city)
        if partner.state_id:
            #if partner.city:
            #    address.append('/')
            address.append(partner.state_id.name)
        #if partner.country_id:
        #    #if partner.city or partner.state_id:
        #    #    address.append('/')
        #    address.append(partner.country_id.name)
        return ' '.join(address)

    def _hepsijet_get_order_id(self, prefix=''):
        if not prefix:
            prefix = ''
        order_id = prefix + ''.join(random.choice('0123456789') for _ in range(18 - len(prefix)))
        if self.env['stock.picking'].sudo().search_count([('carrier_tracking_ref', '=', order_id)]):
            return self._hepsijet_get_order_id(prefix)
        return order_id

    def _hepsijet_get_contract_id(self, env_code):
        contract_code = getattr(self, 'delivery_hepsijet_%s_contract_application_code' % env_code, '')
        contract_id = contract_code + ''.join(random.choice('0123456789') for _ in range(12))
        if self.env['stock.picking'].sudo().search_count([('carrier_tracking_ref', '=', contract_id)]):
            return self._hepsijet_get_contract_id(env_code)
        return contract_id

    def toggle_prod_environment(self):
        super().toggle_prod_environment()
        for delivery in self:
            if delivery.delivery_type == 'hepsijet':
                delivery.delivery_hepsijet_connector_id.environment = delivery.prod_environment

    def action_view_hepsijet_contracts(self):
        return self.env.ref('delivery_hepsijet.action_contract').sudo().read()[0]

    def hepsijet_render_contract(self, picking, code=None):
        if picking.delivery_hepsijet_egyg_picking_id or picking.delivery_hepsijet_egyg_picking_res_id:
            domain = [('code', '=', 'EGYG')]
        else:
            domain = [('code', '!=', 'EGYG')]
        if code:
            domain += [('code', '=', code)]
        contract = self.env['delivery.carrier.hepsijet.contract'].sudo().search(domain, limit=1)
        if contract:
            body = contract.render(picking)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            rcontext = {'mode': 'print', 'base_url': base_url}
            #header = self.env['ir.actions.report']._render_template("web.internal_layout", values=rcontext)
            #header = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=Markup(header.decode())))

            body = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=Markup(body)))
            return self.env['ir.actions.report']._run_wkhtmltopdf(
                [body.decode()],
                landscape=False,
                #header=header.decode(),
                specific_paperformat_args={
                    'data-report-margin-top': 10,
                    'data-report-margin-bottom': 10,
                    'data-report-header-spacing': 10,
                }
            )
        return None

    def hepsijet_send_shipping(self, pickings):
        result = dict(exact_price=0, tracking_number=False)
        processed = set()
        offset = 3 # Turkiye Timezone +3
        now = datetime.now() + timedelta(hours=offset)
        env_code = 'prod' if self.prod_environment else 'test'
        abbreviation_code = getattr(self, 'delivery_hepsijet_%s_abbreviation_code' % env_code, '')
        address_code = getattr(self, 'delivery_hepsijet_%s_address_code' % env_code, '')
        address_code_return = getattr(self, 'delivery_hepsijet_%s_address_code_return' % env_code, '')
        username = getattr(self, 'delivery_hepsijet_%s_username' % env_code, '')
        password = getattr(self, 'delivery_hepsijet_%s_password' % env_code, '')
        company_id = getattr(self, 'delivery_hepsijet_%s_company_id' % env_code, '')
        contract_code = getattr(self, 'delivery_hepsijet_%s_contract_application_code' % env_code, '')
        order_id = ''

        def prepare_contract_values(picking):
            if not picking:
                return {}

            receiver = picking._hepsijet_get_receiver()
            try:
                name, surname = receiver.name.rsplit(' ', 1)
            except:
                raise ValidationError(_('Partner name or surname cannot be found.'))

            vat = re.sub(r'\D', '', receiver.vat or '')
            return {
                'contract': {
                    'name': name,
                    'surname': surname,
                    'identityNo': vat,
                    'gsmNo': picking.partner_id.phone or '',
                    'arrivalTime': {
                        'startDate': '%s+%s:00' % (now.isoformat(), str(offset).zfill(2)),
                        'endDate': '%s+%s:00' % ((now + timedelta(days=10)).isoformat(), str(offset).zfill(2)),
                    },
                    'address': {
                        'county': picking.partner_id.city or '',
                        'city': picking.partner_id.state_id.name,
                        'district': picking.partner_id.street or '',
                        'addressText': self._hepsijet_get_address(picking.partner_id)
                    },
                },
            }

        def prepare_egyg_values(picking):
            if not picking:
                return {}

            record = picking
            sender = picking._hepsijet_get_sender()
            receiver = picking._hepsijet_get_receiver()

            partner = receiver
            try:
                partner_name, partner_surname = partner.name.rsplit(' ', 1)
            except:
                partner_name, partner_surname = partner.name, partner.name

            res = picking.delivery_hepsijet_egyg_picking_res_id
            if res:
                record = res
                receiver, sender = sender, receiver

            return {
                "serviceType": [
                    "SYNCEGYG"
                ],
                "delivery": {
                    "totalParcels": "1",
                    "desi": picking.weight or 1,
                    "deliverySlotOriginal": "0",
                    "deliveryDateOriginal": (res.delivery_tracking_ids and res.delivery_tracking_ids[0]['date_promised'] or now).strftime("%Y-%m-%d"), 
                    "deliveryType": "RETURNED" if res else "RETAIL",
                    "product": {
                        "productCode": "HX_STD"
                    },
                    "senderAddress": {
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
                        "addressLine1": self._hepsijet_get_address(sender),
                    },
                    "receiver": {
                        "firstName": partner_name,
                        "lastName": partner_surname,
                        "phone1": partner.phone or '',
                        "phone2": partner.mobile or '',
                        "email": partner.email or '',
                    },
                    "recipientAddress": {
                        "country": {
                            "name": receiver.country_id.name
                        },
                        "city": {
                            "name": receiver.state_id.name
                        },
                        "town": {
                            "name": receiver.city or ''
                        },
                        "district": {
                            "name": receiver.street or ''
                        },
                        "addressLine1": self._hepsijet_get_address(receiver)
                    },
                    "recipientPerson": receiver.name,
                    "recipientPersonPhone1": receiver.phone or '',
                    "relationCode": record._hepsijet_get_relation_code(contract_code),
                    "customerOrderId": record._hepsijet_get_customer_order_id(),
                },
                "warehouse": {
                    "code" : picking.location_id.warehouse_id.delivery_hepsijet_code or ''
                },
            }

        def prepare_product_values(picking):
            if not picking:
                return {}

            sender = picking._hepsijet_get_sender()
            receiver = picking._hepsijet_get_receiver()
            try:
                name, surname = receiver.name.rsplit(' ', 1)
            except:
                raise ValidationError(_('Partner name or surname cannot be found.'))

            values = {
                "delivery": {
                    "totalParcels": "1",
                    "desi": picking.weight or 1,
                    "deliverySlotOriginal": "3",
                    "deliveryDateOriginal": now.strftime("%Y-%m-%d"), 
                    "deliveryType": "RETAIL",
                    "product": {
                        "productCode": "HX_STD"
                    },
                    "senderAddress": {
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
                        "addressLine1": self._hepsijet_get_address(sender),
                    },
                    "receiver": {
                        "firstName": name,
                        "lastName": surname,
                        "phone1": picking.partner_id.phone or '',
                        "phone2": picking.partner_id.mobile or '',
                        "email": picking.partner_id.email or '',
                    },
                    "recipientAddress": {
                        "country": {
                            "name": picking.partner_id.country_id.name
                        },
                        "city": {
                            "name": picking.partner_id.state_id.name
                        },
                        "town": {
                            "name": picking.partner_id.city or ''
                        },
                        "district": {
                            "name": picking.partner_id.street or ''
                        },
                        "addressLine1": self._hepsijet_get_address(picking.partner_id)
                    },
                    "recipientPerson": '%s %s' % (name, surname),
                    "recipientPersonPhone1": picking.partner_id.phone or '',
                },
                "warehouse": {
                    "code" : picking.location_id.warehouse_id.delivery_hepsijet_code or ''
                },
            }

            if picking.delivery_hepsijet_contract_picking_id:
                line = picking.move_ids and picking.move_ids[0]
                values['delivery']['deliveryContent'] = {
                    'sku': 'HBV%s' % str(line and line.product_id.id or 0).zfill(10),
                    'description': line and line.product_id.display_name or '-',
                    'quantity': line and line.product_qty or 1,
                    'desi': 1,
                    'indivisibleQuantity': False,
                }

            service_type = []
            if picking.weight > float(41):
                service_type.append("TMH")
            elif picking.delivery_hepsijet_pod:
                service_type.append("POD")
            elif picking.delivery_hepsijet_contract_picking_id:
                service_type.append("PRODUCTCONTRACT")
            values['serviceType'] = service_type

            #delivery_time = '0'
            #if now.date() == date.date() or (now + timedelta(days=1)).date() == date.date():
            #    if 0 <= date.hour < 13:
            #        delivery_time = '1'
            #    elif 13 <= date.hour < 18:
            #        delivery_time = '2'
            #    elif 18 <= date.hour < 24:
            #        delivery_time = '3'
            values['delivery']['deliverySlotOriginal'] = "0"
            return values

        res = None
        for p in pickings:
            if p.id in processed:
                continue

            if p.delivery_hepsijet_contract_picking_id:
                picking_product = p
                picking_contract = p.delivery_hepsijet_contract_picking_id
            elif p.delivery_hepsijet_contract_picking_res_id:
                picking_product = p.delivery_hepsijet_contract_picking_res_id
                picking_contract = p
            else:
                if p.delivery_hepsijet_contract_ok:
                    picking_product = self.env['stock.picking']
                    picking_contract = p
                else:
                    picking_product = p
                    picking_contract = self.env['stock.picking']

            if picking_contract and not picking_contract.delivery_hepsijet_contract_only:
                raise UserError(_('You cannot send products along with contract.'))

            if picking_product and picking_contract and picking_contract.state in ('draft', 'waiting', 'confirmed', 'assigned'):
                picking_contract.action_assign()
                picking_contract.move_ids.write({'quantity_done': 1})
                picking_contract.with_context(no_shipping=True).button_validate()

            if picking_contract and picking_product and picking_product.state in ('draft', 'waiting', 'confirmed', 'assigned'):
                picking_product.action_assign()
                picking_product.move_ids.write({'quantity_done': 1})
                picking_product.with_context(no_shipping=True).button_validate()

            processed.add(picking_product.id)
            processed.add(picking_contract.id)

            params = {}
            reference = []
            if picking_product:
                reference.append(str(picking_product.id))
                params.update({
                    "company": {"name": getattr(self, 'delivery_hepsijet_%s_company_name' % env_code, '')},
                    'addressCode': address_code,
                })
                if picking_product.delivery_hepsijet_egyg_ok:
                    order_id = self._hepsijet_get_order_id(self.delivery_hepsijet_prefix_egyg)
                    params.update(prepare_egyg_values(picking_product))
                    if params['delivery']['deliveryType'] == 'RETURNED':
                        order_id = self._hepsijet_get_order_id(self.delivery_hepsijet_prefix_egyg_return)
                        params.update({'addressCode': address_code_return})
                else:
                    order_id = self._hepsijet_get_order_id(self.delivery_hepsijet_prefix_product)
                    params.update(prepare_product_values(picking_product))
            if picking_contract:
                if picking_product:
                    order_id = self._hepsijet_get_order_id(self.delivery_hepsijet_prefix_product_contract)
                else:
                    order_id = self._hepsijet_get_order_id(self.delivery_hepsijet_prefix_contract)
                reference.append(str(picking_contract.id))
                params.update({'contractId': self._hepsijet_get_contract_id(env_code)})
                params.update(prepare_contract_values(picking_contract))

            (picking_product | picking_contract).write({'delivery_hepsijet_connector_ok': True})
            params.update({
                'username': username,
                'password': password,
                'companyId': company_id,
                'abbreviationCode': abbreviation_code,
                'orderId': order_id
            })

            connectors = (picking_product | picking_contract).mapped('syncops_connector_id')[:1] or self.delivery_hepsijet_connector_id
            res, message = self.env['syncops.connector'].sudo()._execute('delivery_post_order', params=params, reference=','.join(reference), connectors=connectors, message=True)
            if not res:
                raise ValidationError(message)
                (picking_product | picking_contract).write({
                    'delivery_hepsijet_connector_state': False,
                    'delivery_hepsijet_connector_message': message,
                })
            else:
                if not picking_product.syncops_connector_id:
                   picking_product.write({'syncops_connector_id': self.delivery_hepsijet_connector_id.id})
                if not picking_contract.syncops_connector_id:
                   picking_contract.write({'syncops_connector_id': self.delivery_hepsijet_connector_id.id})
                r = res[0]
                if r['status'] == 'FAIL':
                    (picking_product | picking_contract).write({
                        'delivery_hepsijet_connector_state': False,
                        'delivery_hepsijet_connector_message': r.get('message') or _('Connector process failed.'),
                    })
                else:
                    r = r['data']
                    picking_product.write({
                        'carrier_id': self.id,
                        'delivery_hepsijet_connector_state': True,
                        'delivery_hepsijet_connector_message': _('Connector process succeeded.'),
                        'carrier_tracking_ref': r.get('customerDeliveryNo', False),
                    })
                    picking_contract.write({
                        'carrier_id': self.id,
                        'delivery_hepsijet_connector_state': True,
                        'delivery_hepsijet_connector_message': _('Connector process succeeded.'),
                        'delivery_hepsijet_contract_id': params.get('contractId', False),
                        'carrier_tracking_ref': r.get('customerContractNo', False),
                    })
                    if picking_product and picking_contract:
                        result['tracking_number'] = None
                    elif picking_product:
                        result['tracking_number'] = r.get('customerDeliveryNo', False)
                    elif picking_contract:
                        result['tracking_number'] = r.get('customerContractNo', False)
        self.env.cr.commit()
        return [result]

    def hepsijet_get_tracking_link(self, picking):
        return 'https://hepsijet.com/gonderi-takibi/{}'.format(picking.carrier_tracking_ref)
