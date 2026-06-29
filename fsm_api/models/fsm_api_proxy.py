# -*- coding: utf-8 -*-
import re
import json
import time
import logging
import traceback

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import test_python_expr
from ..services import PARAMTYPEMAP as PARAMTYPE, RESPONSETYPE, PROXY, NAMESPACE

_logger = logging.getLogger(__name__)


class FsmApiProxy(models.Model):
    _name = 'fsm.api.proxy'
    _description = 'Field Service Management: API Proxies'
    _order = 'sequence'

    def _register_hook(self):
        try:
            self._update_service()
        except:
            _logger.error(traceback.format_exc())

    def _update_service(self, services=None):
        db = self.env.cr.dbname.replace('-', '_').replace('.', '_')
        if db not in PROXY:
            PROXY[db] = {}

        if self:
            proxies = self
        else:
            proxies = self.env['fsm.api.proxy'].search([])

        for proxy in proxies:
            pid = proxy.id
            if pid not in PROXY[db]:
                PROXY[db][pid] = {'schema': {}, 'service': {}}

            if not services:
                services = proxy.service_ids

            for service in services:
                typ = '0'
                sid = service.id
                if sid not in PROXY[db][pid]['service']:
                    PROXY[db][pid]['service'][sid] = {}
                if service.code:
                    name = '%s_%s_%s_%s' % (db, pid, sid, typ)
                    code = re.sub(r'(\n)', r'\1  ', service.code)
                    func = 'def %s(context):\n  ' % (name) + code.strip()
                    exec(func, NAMESPACE)
                    PROXY[db][pid]['service'][sid][typ] = NAMESPACE[name]
                else:
                    if '0' in PROXY[db][pid]['service']:
                        del PROXY[db][pid]['service'][sid][typ]
                for response in service.response_ids:
                    typ = response.type
                    if response.code:
                        name = '%s_%s_%s_%s' % (db, pid, sid, typ)
                        code = re.sub(r'(\n)', r'\1  ', response.code)
                        func = 'def %s(context):\n  ' % (name) + code.strip()
                        exec(func, NAMESPACE)
                        PROXY[db][pid]['service'][sid][typ] = NAMESPACE[name]
                    else:
                        if typ in PROXY[db][pid]['service']:
                            del PROXY[db][pid]['service'][sid][typ]

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    image = fields.Image(related='provider_id.image')
    sequence = fields.Integer(string='Priority', default=10)
    provider_id = fields.Many2one('fsm.api.proxy.provider', required=True)
    type = fields.Selection(related='provider_id.type', store=True, required=True, readonly=False)
    code = fields.Char(related='provider_id.code', store=True, required=True, readonly=False)
    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict', index=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, ondelete='restrict')
    model_ids = fields.One2many('fsm.api.proxy.service.model', 'proxy_id', string='Models', copy=True)
    service_ids = fields.One2many('fsm.api.proxy.service', 'proxy_id', string='Services', copy=True)
    type_ids = fields.One2many('fsm.api.proxy.type', 'proxy_id', string='Types', copy=True)
    bank_ids = fields.One2many('fsm.api.proxy.bank', 'proxy_id', string='Banks', copy=True)
    status_ids = fields.One2many('fsm.api.proxy.status', 'proxy_id', string='Status Codes', copy=True)
    city_ids = fields.One2many('fsm.api.proxy.city', 'proxy_id', string='Cities', copy=True)
    town_ids = fields.One2many('fsm.api.proxy.town', 'proxy_id', string='Towns', copy=True)
    type_ok = fields.Boolean('Map Types')
    bank_ok = fields.Boolean('Map Banks')
    status_ok = fields.Boolean('Map Statuses')
    city_ok = fields.Boolean('Map Cities')
    town_ok = fields.Boolean('Map Towns')
    auth_type = fields.Selection([
        ('basic', 'Basic Auth'),
        ('bearer', 'Bearer Token'),
        ('param_basic', 'Send as Parameter'),
    ], string='Authorization Type')

    def action_toggle_active(self):
        self.active = not self.active

    @api.onchange('provider_id')
    def onchange_provider_id(self):
        if not self.provider_id:
            self.update({
                'type': False,
                'code': False,
                'type_ok': False,
                'bank_ok': False,
                'city_ok': False,
                'town_ok': False,
                'status_ok': False,
                'auth_type': False,
            })


class FsmApiProxyService(models.Model):
    _name = 'fsm.api.proxy.service'
    _description = 'Field Service Management: API Proxy Services'
 
    @api.depends('service_id')
    def _compute_name(self):
        for service in self:
            service.name = service.service_id.name

    code = fields.Text()
    name = fields.Char(compute='_compute_name', store=True)
    proxy_type = fields.Selection(related='proxy_id.type', store=True)
    proxy_id = fields.Many2one('fsm.api.proxy', ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', related='proxy_id.partner_id', store=True)
    company_id = fields.Many2one(related='proxy_id.company_id', store=True)
    service_id = fields.Many2one('fsm.api.spec.service', string='Service', required=True)
    input_ids = fields.One2many('fsm.api.proxy.service.input', 'service_id', string='Inputs', copy=True)
    output_ids = fields.One2many('fsm.api.proxy.service.output', 'service_id', string='Outputs', copy=True)
    response_ids = fields.One2many('fsm.api.proxy.service.response', 'service_id', string='Responses', copy=True)
    soap_ref = fields.Char(string='SOAP Method')

    def get_ref(self):
        return self.soap_ref if self.proxy_id.type == 'soap' else self.service_id.ref

    @api.constrains('code')
    def _check_code(self):
        for service in self:
            if service.code:
                msg = test_python_expr(expr=service.code.strip(), mode='exec')
                if msg:
                    raise ValidationError(msg)

    def write(self, values):
        res = super().write(values)
        if 'code' in values:
            proxies = self.mapped('proxy_id')
            for proxy in proxies:
                proxy._update_service(self)
        return res

    @api.model_create_multi
    def create(self, values_list):
        res = super().create(values_list)
        proxies = res.mapped('proxy_id')
        for proxy in proxies:
            proxy._update_service(self)
        return res

    def _execute(self, params={}):
        self.ensure_one()
        self = self.with_context(lang='tr_TR')
        log = self.env.context.get('log', {})
        log.update({'now': time.time()})
        dbname = self.env.cr.dbname.replace('-', '_').replace('.', '_')

        context = {
            'response': {},
            'env': self.env,
            'params': params,
            'proxy': self.proxy_id.sudo(),
            'service': self.service_id.sudo().with_context(log=log),
        }
        try:
            req = PROXY[dbname][self.proxy_id.id]['service'][self.id]['0']
        except:
            req = None

        status, response = '200', {}
        if req:
            try:
                req(context)
                status, response = context.get('response', (status, response))
            except Exception as e:
                status, response = self.service_id.spec_id._get_error(e, log)

            if status != '200':
                try:
                    log.update({
                        'status': False,
                        'code': status,
                        'message': response['errors'][0]['message'],
                    })
                except:
                    _logger.error('Log cannot be saved. Response code was %s and details as follows:\n%s' % (status, json.dumps(response, default=str, indent=4, ensure_ascii=False)))

            try:
                res = PROXY[dbname][self.proxy_id.id]['service'][self.id][status]
            except:
                res = None
            if res:
                context.update({'response': response})
                res(context)
                response = context.get('response', response)

            if isinstance(response, dict):
                log.update({'response': json.dumps(response, indent=4, default=str, ensure_ascii=False)})
            else:
                log.update({'response': '', 'req': ''})

        self.service_id._log(log)
        return status, response

    @api.onchange('service_id')
    def onchange_service_id(self):
        self.soap_ref = self.service_id.soap_ref

    def get_json_schema(self, io):

        def value():
            return {'type': 'object', 'properties': {}, 'required': []}

        def set(v, f):
            v['properties'].update({
                f.name: {
                    'type': PARAMTYPE.get(f.type, f.type),
                    'description': f.description or '',
                }
            })
            if f.required:
                v['required'].append(f.name)

            if f.type in ('list', 'dict'):
                s = f.model_id and f.model_id.field_ids or f.field_ids
                if f.type == 'list':
                    v['properties'][f.name].update({
                        'items': value(),
                    })
                    for i in s:
                        set(v['properties'][f.name]['items'], i)
                else:
                    v['properties'][f.name].update({
                        **value()
                    })
                    for i in s:
                        set(v['properties'][f.name], i)

            else:
                v['properties'][f.name].update({
                    'example': f.example or '',
                })

        values = value()
        for field in getattr(self, '%s_ids' % io):
            set(values, field)
        return values


class FsmApiProxyServiceIO(models.AbstractModel):
    _name = 'fsm.api.proxy.service.io'
    _inherit = 'fsm.api.spec.service.io'
    _description = 'Field Service Management: API Proxy Service IO'
    _inverse_field = 'proxy_id'

    proxy_id = fields.Many2one('fsm.api.proxy')
    parent_id = fields.Many2one(comodel_name='fsm.api.proxy')
    model_id = fields.Many2one(comodel_name='fsm.api.proxy.service.model', domain="[('proxy_id', '=', parent_id), ('field_id', '=', False)]")
    service_id = fields.Many2one(comodel_name='fsm.api.proxy.service')


class FsmApiProxyServiceInput(models.Model):
    _name = 'fsm.api.proxy.service.input'
    _inherit = 'fsm.api.proxy.service.io'
    _description = 'Field Service Management: API Proxy Service Inputs'

    proxy_id = fields.Many2one(related='service_id.proxy_id')
    field_id = fields.Many2one(comodel_name='fsm.api.proxy.service.input')
    field_ids = fields.One2many(comodel_name='fsm.api.proxy.service.input')


class FsmApiProxyServiceOutput(models.Model):
    _name = 'fsm.api.proxy.service.output'
    _inherit = 'fsm.api.proxy.service.io'
    _description = 'Field Service Management: API Proxy Service Outputs'

    proxy_id = fields.Many2one(related='service_id.proxy_id')
    field_id = fields.Many2one(comodel_name='fsm.api.proxy.service.output')
    field_ids = fields.One2many(comodel_name='fsm.api.proxy.service.output')


class FsmApiProxyServiceModel(models.Model):
    _name = 'fsm.api.proxy.service.model'
    _inherit = 'fsm.api.proxy.service.io'
    _description = 'Field Service Management: API Proxy Service Models'

    field_id = fields.Many2one(comodel_name='fsm.api.proxy.service.model')
    field_ids = fields.One2many(comodel_name='fsm.api.proxy.service.model')


class FsmApiProxyServiceResponse(models.Model):
    _name = 'fsm.api.proxy.service.response'
    _description = 'Field Service Management: API Proxy Service Response'
    _order = 'type'

    @api.depends('type')
    def _compute_badge(self):
        for response in self:
            response.badge = response.type and response.type[0] or False

    service_id = fields.Many2one('fsm.api.proxy.service')
    type = fields.Selection(RESPONSETYPE, default='200', required=True)
    badge = fields.Char(compute='_compute_badge')
    name = fields.Char(required=True)
    code = fields.Text()

    @api.constrains('code')
    def _check_code(self):
        for response in self:
            if response.code:
                msg = test_python_expr(expr=response.code.strip(), mode='exec')
                if msg:
                    raise ValidationError(msg)


class FsmApiProxyType(models.Model):
    _name = 'fsm.api.proxy.type'
    _description = 'Field Service Management: API Proxy Types'

    @api.depends('company_id')
    def _compute_direction(self):
        for line in self:
            line.direction = '→'

    name = fields.Char(string='Code', required=True)
    proxy_id = fields.Many2one('fsm.api.proxy', ondelete='cascade', index=True)
    company_id = fields.Many2one(related='proxy_id.company_id', store=True)
    type_id = fields.Many2one('fsm.type', string='Type', required=True)
    direction = fields.Char(compute='_compute_direction')



class FsmApiProxyBank(models.Model):
    _name = 'fsm.api.proxy.bank'
    _description = 'Field Service Management: API Proxy Bank Codes'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    proxy_id = fields.Many2one('fsm.api.proxy', ondelete='cascade', index=True)
    company_id = fields.Many2one(related='proxy_id.company_id', store=True)


class FsmApiProxyStatus(models.Model):
    _name = 'fsm.api.proxy.status'
    _description = 'Field Service Management: API Proxy Status Codes'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    proxy_id = fields.Many2one('fsm.api.proxy', ondelete='cascade', index=True)
    company_id = fields.Many2one(related='proxy_id.company_id', store=True)


class FsmApiProxyCity(models.Model):
    _name = 'fsm.api.proxy.city'
    _description = 'Field Service Management: API Proxy City Codes'

    name = fields.Char(related='state_id.name')
    code = fields.Char(required=True)
    state_id = fields.Many2one('res.country.state', ondelete='cascade', required=True)
    proxy_id = fields.Many2one('fsm.api.proxy', ondelete='cascade', index=True)
    company_id = fields.Many2one(related='proxy_id.company_id', store=True)


class FsmApiProxyTown(models.Model):
    _name = 'fsm.api.proxy.town'
    _description = 'Field Service Management: API Proxy Town Codes'

    @api.depends('town_id')
    def _compute_state_id(self):
        for town in self:
            town.state_id = town.town_id.state_id.id

    name = fields.Char(related='town_id.name')
    code = fields.Char(required=True)
    state_id = fields.Many2one('res.country.state', string='City', compute='_compute_state_id', readonly=False)
    town_id = fields.Many2one('res.country.town', ondelete='cascade', required=True, domain='[("state_id", "=", state_id)]')
    proxy_id = fields.Many2one('fsm.api.proxy', ondelete='cascade', index=True)
    company_id = fields.Many2one(related='proxy_id.company_id', store=True)


class FsmApiProxyProvider(models.Model):
    _name = 'fsm.api.proxy.provider'
    _description = 'Field Service: API Proxy Providers'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    code = fields.Char(required=True)
    image = fields.Image()
    type = fields.Selection([('rest', 'REST'), ('soap', 'SOAP')], required=True)
