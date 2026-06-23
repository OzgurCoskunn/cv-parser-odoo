# -*- coding: utf-8 -*-
import math
import uuid
import json
import time
import base64
import logging
import traceback
import marshmallow
from http.client import responses

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request, Response
from odoo.addons.fsm import TaskError
from odoo.tools.mimetypes import guess_mimetype
from odoo.addons.base_rest_datamodel.restapi import Datamodel

from ..response import Response200, Response400, Response401, Response403, Response404, Response422, Response500
from ..services import PARAMTYPE

SALEORDER_REASON = {
    'TEKLİF': 'C1077',
    'SİPARİŞ': 'C1076',
    'HAZIR': 'C1078',
    'TESLİM ALINDI': 'C1050',
    'TESLİM EDİLDİ': 'C1053',
    'İADE EDİLDİ': 'C1054',
    'İPTAL': 'C1073',
}

_logger = logging.getLogger(__name__)


class FsmApiSpec(models.Model):
    _name = 'fsm.api.spec'
    _description = 'Field Service Management: API Specification'
    _order = 'sequence, id desc'

    name = fields.Char(required=True)
    version = fields.Char()
    description = fields.Text()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    collection = fields.Char()
    service_ids = fields.One2many('fsm.api.spec.service', 'spec_id', string='Services')
    type_ids = fields.Many2many('fsm.type', 'fsm_api_spec_type_rel', 'spec_id', 'type_id', string='Types')
    stage_ids = fields.Many2many('fsm.stage', 'fsm_api_spec_stage_rel', 'spec_id', 'stage_id', string='Stages')
    reason_ids = fields.Many2many('fsm.reason', 'fsm_api_spec_reason_rel', 'spec_id', 'reason_id', string='Reasons')
    product_ids = fields.Many2many('product.product', 'fsm_api_spec_product_rel', 'spec_id', 'product_id', string='Products', domain='[("fsm_ok", "=", True)]')
    type_all = fields.Boolean(default=True, string='All Types')
    stage_all = fields.Boolean(default=True, string='All Stages')
    reason_all = fields.Boolean(default=True, string='All Reasons')
    product_all = fields.Boolean(default=True, string='All Products')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def get_description(self):
        if not self.description:
            return ''

        type_desc = ''
        type_all = self.type_ids.search([]) if self.type_all else self.type_ids
        if type_all:
            type_table = [
                '**İş Emri Türleri** (_orderType_)\n',
                '| **DEĞER** | **AÇIKLAMA** |',
                '|--|--|',
            ]
            for type in type_all:
                type_table.append('| %s | %s |' % (type.code or '', type.description or ''))
            type_desc = '\n'.join(type_table)

        stage_desc = ''
        stage_all = self.stage_ids.search([]) if self.stage_all else self.stage_ids
        if stage_all:
            stage_table = [
                '**İş Emri Durumları** (_status_)\n',
                '| **DEĞER** | **AÇIKLAMA** |',
                '|--|--|',
            ]
            for stage in stage_all:
                stage_table.append('| %s | %s |' % (stage.code or '', stage.description or ''))
            stage_desc = '\n'.join(stage_table)

        product_desc = ''
        product_all = self.product_ids.search([('fsm_ok', '=', True)]) if self.product_all else self.product_ids
        if product_all:
            product_table = [
                '**Ürün Modelleri** (_model_)\n',
                '| **DEĞER** | **AÇIKLAMA** |',
                '|--|--|',
            ]
            for product in product_all:
                product_table.append('| %s | %s |' % (product.default_code or '', product.name or ''))
            product_desc = '\n'.join(product_table)

        reason_desc = ''
        reason_all = self.reason_ids.search([]) if self.reason_all else self.reason_ids
        if reason_all:
            reason_table = [
                '**Durum Kodları** (_statusCode_)\n',
                '| **DURUM KODU** | **HTTP KODU** | **DURUM MESAJI** |',
                '|--|--|--|',
            ]
            for reason in reason_all:
                reason_table.append('| %s | %s | %s |' % (reason.code or '', reason.status or '', reason.name or ''))
            reason_desc = '\n'.join(reason_table)

        return self.description \
            .replace('{{type}}', type_desc)\
            .replace('{{stage}}', stage_desc) \
            .replace('{{reason}}', reason_desc) \
            .replace('{{product}}', product_desc)

    def get_reasons(self):
        reason_all = self.reason_ids.search([]) if self.reason_all else self.reason_ids
        return {reason.code: {'code': str(reason.status), 'desc': reason.name} for reason in reason_all if reason.code}

    def _get_reason(self, name, code=None, desc=None):
        reasons = self.get_reasons()
        reason = reasons.get(name, {})
        code = reason.get('code', code) or '200'
        desc = desc or reason.get('desc', desc) or ''
        return name, code, desc

    def _get_error(self, error, log):
        if isinstance(error, ValidationError):
            return '400', {
                'errors': [{
                    'code': 'C1400',
                    'message': str(error),
                }]
            }
        elif isinstance(error, UserError):
            return '400', {
                'errors': [{
                    'code': 'C1400',
                    'message': str(error),
                }]
            }
        elif isinstance(error, Response400):
            reason_name, reason_code, reason_desc = self._get_reason(error.code, error.status, error.reason)
            return reason_code, {
                'errors': [{
                    'code': reason_name,
                    'message': reason_desc,
                }]
            }
        elif isinstance(error, Response401):
            reason_name, reason_code, reason_desc = self._get_reason(error.code, error.status, error.reason)
            return reason_code, {
                'errors': [{
                    'code': reason_name,
                    'message': reason_desc,
                }]
            }
        elif isinstance(error, Response403):
            reason_name, reason_code, reason_desc = self._get_reason(error.code, error.status, error.reason)
            return reason_code, {
                'errors': [{
                    'code': reason_name,
                    'message': reason_desc,
                }]
            }
        elif isinstance(error, Response404):
            reason_name, reason_code, reason_desc = self._get_reason(error.code, error.status, error.reason)
            return reason_code, {
                'errors': [{
                    'code': reason_name,
                    'message': reason_desc,
                }]
            }
        elif isinstance(error, Response422):
            reason_name, reason_code, reason_desc = self._get_reason(error.code, error.status, error.reason)
            return reason_code, {
                'errors': [{
                    'code': reason_name,
                    'message': reason_desc,
                    'details': [{
                        'field': detail['field'],
                        'issue': detail['issue']
                    } for detail in error.detail]
                }]
            }
        elif isinstance(error, Response500):
            debug = traceback.format_exc()
            log.update({'debug': debug})
            _logger.error(debug)

            reason_name, reason_code, reason_desc = self._get_reason(error.code, error.status, error.reason)
            return reason_code, {
                'errors': [{
                    'code': reason_name,
                    'message': reason_desc,
                }]
            }
        else:
            debug = traceback.format_exc()
            log.update({'debug': debug})
            _logger.error(debug)

            reason_name, reason_code, reason_desc = self._get_reason('C1500', '500')
            return reason_code, {
                'errors': [{
                    'code': reason_name,
                    'message': reason_desc,
                }]
            }

    def execute(self, service_code, *args, **kwargs):
        service = self.env['fsm.api.spec.service'].sudo().search([('spec_id', '=', self.id), ('code', '=', service_code)], limit=1)
        if not service:
            return self._get_error(Response404('C1404', _('Service does not exist')), {})

        return service._execute(*args, **kwargs)


class FsmApiSpecService(models.Model):
    _name = 'fsm.api.spec.service'
    _description = 'Field Service Management: API Specification Services'
    _order = 'sequence'

    @api.depends('reason_valid_all', 'reason_valid_ids')
    def _compute_info(self):
        for service in self:
            info = ''
            infos = []
            reasons = not service.reason_valid_all and len(service.reason_valid_ids)
            if reasons:
                infos.append('%s reasons selected' % reasons)
            info = ', '.join(infos)
            if info:
                info += '.'
            service.info = info

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
        ('HEAD', 'HEAD'),
        ('OPTIONS', 'OPTIONS'),
    ], default='GET')
    ref = fields.Char()
    path = fields.Char()
    code = fields.Text()
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], default=False)
    info = fields.Char(compute='_compute_info')
    spec_id = fields.Many2one('fsm.api.spec', ondelete='cascade')
    model_ids = fields.One2many('fsm.api.spec.service.model', 'service_id')
    reason_current_ids = fields.Many2many('fsm.reason', 'fsm_api_spec_service_reason_current_rel', 'service_id', 'reason_id', string='Reasons Filter')
    reason_valid_all = fields.Boolean('All Reasons Valid', default=True)
    reason_valid_ids = fields.Many2many('fsm.reason', 'fsm_api_spec_service_reason_valid_rel', 'service_id', 'reason_id', string='Reasons Valid')
    soap_ref = fields.Char(string='SOAP Method')

    def _auth(self, username=False, password=False):
        if not username:
            username = self.env.context.get('username')

        if not password:
            password = self.env.context.get('password')

        if not username and not password:
            headers = request.httprequest.headers
            auth = headers.get('Authorization')
            if not auth:
                raise Response401('C1401')

            code = auth.split(' ', 1)[1]
            keys = base64.b64decode(code).decode('utf-8')
            username, password = keys.split(':', 1)
        token = self.env['fsm.api.auth'].sudo().search([('api_key', '=', username), ('secret_key', '=', password)], limit=1)
        if not token.exists():
            raise Response401('C1401')

        log = self.env.context.get('log', {})
        log.update({'auth': token.id, 'partner': token.partner_id.id})
        return token

    def _check(self, *ps):
        details = []
        def serialize(field, issues):
            if isinstance(issues, dict):
                for f, i in issues.items():
                    node = field
                    field, issues = serialize('%s > %s' % (field, f), i)
                    field = node
            elif isinstance(issues, list):
                for issue in issues:
                    details.append({
                        'field': field,
                        'issue': issue,
                    })
            return field, issues

        for p in ps:
            if isinstance(p, marshmallow.exceptions.ValidationError):
                details = []
                message = _('Required field is missing or schema incompatible field has been specified.')
                for field, issues in p.messages.items():
                    serialize(field, issues)
                raise Response422('C1441', details, message)

    def _check_reason(self, task=None, code=None):
        if code and not self.reason_valid_all and code not in self.reason_valid_ids.mapped('code'):
            raise Response400('C1400', _('This status code cannot be used in this service.'))
        if task and task.reason_code in self.reason_current_ids.mapped('code'):
            raise Response400('C1400', _('You cannot use this service, because task has been reasoned with "%s (%s)".') % (task.reason_name, task.reason_code))

    def _args(self, log, *args, **kwargs):
        result = []
        path_model = Datamodel('fsm.%s.path' % self.code.lower())
        param_model = Datamodel('fsm.%s.request' % self.code.lower())

        try:
            schema = path_model.to_json_schema(self, None, 'input')
            keys = schema['properties'].keys()
            paths = dict(zip(keys, args))
            logger = json.dumps(paths, indent=4, default=str, ensure_ascii=False)
            log['request'] = '%s%s' % ('\n\n' if log.get('request') else '', logger)

            paths = path_model.from_params(self, paths, raise_exception=False)
            self._check(paths)
            result.extend(args)
        except KeyError:
            pass

        try:
            logger = json.dumps({**kwargs}, indent=4, default=str, ensure_ascii=False)
            log['request'] = '%s%s' % ('\n\n' if log.get('request') else '', logger)

            params = param_model.from_params(self, kwargs, raise_exception=False)
            self._check(params)
            result.append(params)
        except KeyError:
            pass

        return tuple(result)

    def _log_sql_value(self, value):
        if isinstance(value, str):
            return "$$%s$$" % value
        elif isinstance(value, int):
            return "%s" % value
        else:
            return "NULL"

    def _log(self, log):
        now = time.time()
        code = log.get('code', 200)
        values = {
            'service_id': self.id,
            'company_id': self.env.company.id,
            'partner_id': log.get('partner'),
            'auth_id': log.get('auth'),
            'task_id': log.get('task'),
            'status': log.get('status', True),
            'message': log.get('message', _('Request is successful')),
            'duration': now - log.get('now', now),
            'debug_message': log.get('debug', False),
            'request_data': log.get('request', '{}'),
            'request_method': request.httprequest.method,
            'request_raw': log.get('req', request.httprequest.get_data() or '{}'),
            'request_url': request.httprequest.url,
            'response_message': responses.get(int(code), ''),
            'response_data': log.get('response', '{}'),
            'response_raw': log.get('res', '{}'),
            'response_code': code,
        }

        if self.env.context.get('no_log'):
            log.update(values)
        else:
            keys = values.keys()
            vals = values.values()
            self.env.cr.execute('''
                INSERT INTO fsm_api_log (%s, create_uid, write_uid, create_date, write_date)
                VALUES (%s, 1, 1, NOW() at time zone 'UTC', NOW() at time zone 'UTC')
                ''' % (', '.join(keys), ', '.join(map(self._log_sql_value, vals)))
            )

    def _execute(self, *args, **kwargs):
        self = self.with_context(lang='tr_TR')
        log = self.env.context.get('log', {})
        log.update({'now': time.time()})
        task = False

        try:
            token = self._auth()
            log.update({'auth': token.id, 'partner': token.partner_id.id})
            if self.code == 'createWorkorder':
                params, = self._args(log, *args, **kwargs)

                project, project_item = False, False
                if hasattr(params, 'project') and params.project:
                    project = self.env['fsm.project'].sudo().search([
                        ('state', '=', 'confirm'),
                        ('uid', '=', params.project.id),
                    ])
                    if not project:
                        project_item = self.env['fsm.project.item'].sudo().search([
                            ('state', '=', 'confirm'),
                            ('uid', '=', params.project.id),
                        ])
                        if len(project_item) > 1:
                            raise Response404('C1404', _('There are more than one project exist.'))
                        project = project_item.project_id
                    if len(project) > 1:
                        raise Response404('C1404', _('There are more than one project exist.'))
                else:
                    project = token.project_id
                if not project:
                    raise Response404('C1404', _('Project cannot be found.'))

                partner = project.partner_id
                value = {
                    'project_id': project.id,
                    'partner_id': partner.id,
                    'channel': params.get('channel', False),
                    'order_uid': params.get('customerOrderId', False),
                    'description': params.get('orderDescription', False),
                }

                if project_item:
                    value.update({'project_item_id': project_item.id, 'sla_id': project_item.sla_id.id})

                if not project_item and getattr(params, 'sla', None):
                    sla = project.sla_ids.filtered(lambda p: p.code == params.sla)
                    if not sla:
                        raise Response404('C1404', _('SLA cannot be found.'))
                    value.update({'sla_id': sla[0]['id']})
                
                if not value.get('sla_id'):
                    raise Response404('C1404', _('SLA cannot be found.'))

                order_types = project.type_ids.mapped('type_id.code')
                order_type = params.get('orderType')
                if order_type in self.env.context.get('proxy', {}).get('types', {}):
                    order_type = self.env.context['proxy']['types'][order_type]
                if order_type not in order_types:
                    raise Response400('C1400', _('This type code cannot be used for this project.'))

                type = self.env['fsm.type'].sudo().search([('code', '=', order_type)], limit=1)
                if not type:
                    raise Response404('C1404', _('Type cannot be found.'))
                value.update({'type_id': type.id})

                merchant, merchant_service = self._get_merchant(params.get('merchant'))
                value.update({'merchant_id': merchant.id, 'merchant_service_id': merchant_service.id})

                products = params.get('products', [])
                if products:
                    vals = []
                    for product in products:
                        val = {}
                        prod = False
                        if product.get('model'):
                            prod = self.env['product.product'].sudo().search([('fsm_ok', '=', True), ('default_code', '=', product.get('model'))], limit=1)
                            if prod:
                                val.update({'product_id': prod.id})
                            else:
                                raise Response404('C1404', _('No product found with name "%s".') % product.get('model', ''))

                        if product.get('subpartner'):
                            subpartners = project.subpartner_ids.mapped('name')
                            if product.get('subpartner') not in subpartners:
                                raise Response404('C1434', '%s alt iş ortağı projede tanımlı değildir.' % (product.get('subpartner'),))

                        if product.get('serialNumber'):
                            domain = [('name', '=', product.get('serialNumber'))]
                            if prod:
                                domain.append(('product_id', '=', prod.id))
                            lot = self.env['stock.lot'].sudo().search(domain, limit=1)
                            if not lot:
                                raise Response404('C1434', '%s modeline ve %s seri numarasına sahip ürün stoklarıda bulunmamaktadır. Lütfen bilgilerinizi kontrol ederek tekrar deneyiniz veya destek ekibimizle iletişime geçiniz.' % (product.get('model'), product.get('serialNumber')))
                            if lot.fsm_partner_id.id != partner.id:
                                raise Response404('C1434', '%s modeline ve %s seri numarasına sahip ürün stoklarıda bulunmamaktadır. Lütfen bilgilerinizi kontrol ederek tekrar deneyiniz veya destek ekibimizle iletişime geçiniz.' % (product.get('model'), product.get('serialNumber')))

                            val.update({'product_lot_id': lot.id})
                            if not prod:
                                prod = lot.product_id
                                val.update({'product_id': prod.id})

                        if product.get('serialReference'):
                            val.update({'product_lot_ref': product.get('serialReference')})

                        if product.get('productType'):
                            val.update({'product_type': product.get('productType')})

                        if product.get('operatingSystem'):
                            val.update({'product_os': product.get('operatingSystem')})

                        if product.get('orderType'):
                            val.update({'product_order_type': product.get('orderType')})

                        if product.get('operationType'):
                            val.update({'product_operation_type': product.get('operationType')})

                        if product.get('subpartner'):
                            val.update({'product_subpartner': product.get('subpartner')})

                        if product.get('operator'):
                            val.update({'product_operator': product.get('operator')})

                        vals.append(val)

                    value.update({
                        'product_ids': [(0, 0, val) for val in vals]
                    })

                setup = params.get('setup', {})
                if setup:
                    value.update({
                        'setup_uid': setup.get('setupId', False),
                        'setup_key': setup.get('setupKey', False),
                        'setup_merchant_uid': setup.get('merchantId', False),
                    })

                    applications = setup.get('applications', [])
                    if applications:
                        application_vals = []
                        for application in applications:
                            application_vals.append((0, 0, {
                                'name': application.get('name', False),
                                'description': application.get('description', False),
                                'version': application.get('version', False),
                            }))
                        value.update({'setup_application_ids': application_vals})

                material = params.get('material', {})
                if material:
                    mat = self.env['product.product'].sudo().search([('fsm_ok', '=', True), ('name', '=', material.get('name'))], limit=1)
                    if mat:
                        value.update({'material_id': mat.id})
                    else:
                        raise Response404('C1404', _('No material found with name "%s".') % material.get('name', ''))

                    value.update({
                        'material_id': mat.id,
                        'material_name': material.get('name', False),
                        'material_serial': material.get('serialNumber', False),
                        'material_count': material.get('count', False),
                    })

                document = params.get('document', {})
                if document:
                    value.update({
                        'document_uid': document.get('id', False),
                        'document_type': document.get('type', False),
                        'document_name': document.get('name', False),
                        'document_info_vat': document.get('information', {}).get('identityNumber', False),
                        'document_info_name': document.get('information', {}).get('identityName', False),
                        'document_info_birthday': document.get('information', {}).get('birthday', False),
                        'document_info_birthplace': document.get('information', {}).get('placeOfBirth', False),
                        'document_info_iban': document.get('information', {}).get('iban', False),
                    })
                    if document.get('information', {}).get('details', []):
                        value.update({
                            'document_info_detail_ids': [(0, 0, {
                                'name': val.get('key'),
                                'value': val.get('value'),
                            }) for val in document.get('information', {}).get('details', [])]
                        })

                defaults = {
                    'default_type_id': type.id,
                    'default_project_id': project.id,
                    'default_partner_id': project.partner_id.id,
                    'default_project_item_id': project_item and project_item.id or False,
                }

                try:
                    with self.env.cr.savepoint():
                        task = self.env['fsm.task'].sudo().with_context(**defaults).create(value)
                        task.flush_recordset()
                except TaskError as e:
                    raise Response400('C1400', str(e))

                response = Response200('C1200', {
                    'customerOrderId': params.get('customerOrderId', ''),
                    'parentOrderId': task.uid if task.child_ids else '',
                    'workOrders': [{
                        'orderId': task.uid,
                        'orderType': task.type_id.code,
                    }] + [{
                        'orderId': subtask.uid,
                        'orderType': subtask.type_id.code,
                    } for subtask in task.child_ids],
                })

            elif self.code == 'getWorkorder':
                orderId, = self._args(log, *args, **kwargs)
                task = self.env['fsm.task'].sudo().search([('uid', '=', orderId)], limit=1)
                if not task:
                    raise Response404('C1404', _('Workorder cannot be found.'))

                base_url = task.get_base_url()
                sla_tickets = task.partner_ticket_ids
                sla_status = all((t.stage_time_work_left or 0) < 0 for t in sla_tickets) and 'SLA_DISI' or 'SLA_ICI'

                values = {
                    'orderId': task.uid or '',
                    'customerOrderId': task.order_uid or '',
                    'orderType': task.type_id.code or '',
                    'orderDescription': task.description or '',
                    'slaStatus': sla_status,
                    'status': task.stage_id.code or '',
                    'statusCode': task.reason_code or '',
                    'statusMessage': task.reason_name or '',
                    'statusDetail': task.reason_desc or '',
                    'rating': '',
                    'merchant': {},
                    'appointments': [],
                    'setup': {},
                    'products': [{
                        'productType': product.product_type or '',
                        'serialNumber': product.product_lot_id.name or '',
                        'model': product.product_id.default_code or '',
                        'orderType': product.product_order_type or '',
                        'operationType': product.product_operation_type or '',
                        'operator': product.product_operator or '',
                        'productStatus': product.product_state or '',
                        #'image': '',
                        'accesories': [],
                    } for product in task.product_ids],
                    'cargoDelivery': {},
                    'serviceDocuments': [],
                }
                
                documents = task._get_mail_thread_data_attachments()
                if documents:
                    documents.generate_access_token()
                    for document in documents:
                        if document.fsm_document_type == 'itf':
                            document_type = 'İşlem Takip Formu'
                        else:
                            document_type = 'Belge'
                        values['serviceDocuments'].append({
                            'id': document.access_token,
                            'documentType': document_type,
                            'serialNumber': document.fsm_document_serial or '',
                            'documentPath': '%s/fsm/%s/document/%s' % (base_url, task.uid, document.access_token),
                        })

                if task.project_item_id:
                    values.update({
                        'project': {
                            'id': task.project_item_id.uid or '',
                        }
                    })

                if task.create_date:
                    values.update({
                        'createDate': task.create_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    })

                if task.due_date:
                    values.update({
                        'dueDate': task.due_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    })

                if task.service_type_id:
                    values.update({
                        'serviceType': task.service_type_id.code or '',
                    })

                if task.appointment_ids:
                    task.appointment_ids.mapped('document_ids').generate_access_token()
                    base_url = task.get_base_url()
                    values.update({
                        'appointments': [{
                            'id': appointment.uid or '',
                            'createDate': appointment.create_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                            'appointmentDate': appointment.date.strftime('%Y-%m-%dT%H:%M:%SZ') or None,
                            'contactName': appointment.partner_id.name or '',
                            'code': appointment.reason_id.code or '',
                            'message': appointment.reason_id.name or '',
                            'detail': appointment.reason_desc or '',
                            'documents': ['%s/web/content/%s?access_token=%s' % (base_url, document.id, document.access_token) for document in appointment.document_ids if document.access_token]
                        } for appointment in task.appointment_ids],
                    })

                if task.delivery_ids:
                    deliveries = task.delivery_ids.filtered(lambda d: d.carrier_id and d.state in ('assigned', 'done'))
                    if deliveries:
                        delivery = deliveries[-1]
                        values.update({
                            'cargoDelivery': {
                                'id': delivery.carrier_doc_id or '',
                                'carrier': delivery.carrier_id.name or '',
                            },
                        })
                        if hasattr(delivery, 'delivery_tracking_ids'):
                            trackings = delivery.delivery_tracking_ids
                            if trackings:
                                tracking = trackings[-1]
                                values['cargoDelivery'].update({
                                    'promisedDate': tracking.date_promised and tracking.date_promised.strftime('%Y-%m-%dT%H:%M:%SZ') or None,
                                    'transactionDate': tracking.transaction_datetime and tracking.transaction_datetime.strftime('%Y-%m-%dT%H:%M:%SZ') or None,
                                    'statusCode': tracking.status,
                                    'statusMessage': tracking.state,
                                    'statusDetail': tracking.transaction,
                                    'transactionHistory': [{
                                        'transactionDate': t.transaction_datetime and t.transaction_datetime.strftime('%Y-%m-%dT%H:%M:%SZ') or None,
                                        'statusCode': t.status,
                                        'statusMessage': t.state,
                                        'statusDetail': t.transaction,
                                        'nonDeliveryReason': t.delivery_return_reason or None,
                                        'nonDeliveryReasonMessage': t.delivery_return_reason_message or None,
                                    } for t in trackings]
                                })

                if task.setup_uid:
                    values['setup'].update({
                        'setupId': task.setup_uid or '',
                        'setupKey': task.setup_key or '',
                        'merchantId': task.setup_merchant_uid or '',
                        'applications': [{
                            'name': application.name or '',
                            'description': application.description or '',
                            'version': application.version or '',
                        } for application in task.setup_application_ids],
                    })

                if task.merchant_service_ok:
                    merchant = task.merchant_service_id
                else:
                    merchant = task.merchant_id
                if merchant:
                    values['merchant'].update({
                        'serviceAddress': {
                            'contactName': merchant.contact_id.name or '',
                            'phoneNumber': merchant.phone or '',
                            'mobile': merchant.mobile or '',
                            'email': merchant.email or '',
                            'city': {
                                'id': int(merchant.state_id.code) or 0,
                                'name': merchant.state_id.name or '',
                            },
                            'town': {
                                'id': int(merchant.town_id.code) or 0,
                                'name': merchant.town_id.name or '',
                            },
                            'district': {
                                'id': int(merchant.district_id.code) or 0,
                                'name': merchant.district_id.name or '-',
                            },
                            'address': merchant.street or '',
                            'zipCode': merchant.zip or '',
                            'latitude': merchant.partner_latitude and str(merchant.partner_latitude) or '',
                            'longitude': merchant.partner_longitude and str(merchant.partner_longitude) or '',
                            'uavtCode': merchant.uavt_code or '',
                        },
                    })

                if task.close_done:
                    values.update({
                        'orderResult': {
                            'contactName': task.merchant_id.contact_id.name or None,
                            'result': task.close_success and 'BASARILI' or 'BASARISIZ',
                            'actionDate': task.write_date and task.write_date.strftime('%Y-%m-%dT%H:%M:%SZ') or None,
                            'completeDate': task.close_date and task.close_date.strftime('%Y-%m-%dT%H:%M:%SZ') or None,
                        },
                    })

                response = Response200('C1200', values)

            elif self.code == 'approveWorkorder':
                orderId, params = self._args(log, *args, **kwargs)
                task = self.env['fsm.task'].sudo().search([('uid', '=', orderId)], limit=1)
                if not task:
                    raise Response404('C1404', _('Workorder cannot be found.'))

                if task.stage_type == '2':
                    if task.approval_state:
                        msg = task.approval_state == '0' and _('approved') or _('rejected')
                        raise Response400('C1400', _('Workorder has been %s already.') % msg)

                    self._check_reason(code=params.code)
                    approval_state = '0' if params.code == 'C1100' else '1'
                    reason = self.env['fsm.reason'].sudo().search([('code', '=', params.code)], limit=1)
                    values = {
                        'reason_id': reason.id,
                        'reason_code': reason.code,
                        'reason_name': reason.name,
                        'approval_state': approval_state,
                        'approval_desc': getattr(params, 'message', False),
                    }

                    try:
                        with self.env.cr.savepoint():
                            task.with_context(no_reason=True).sudo().write(values)
                            task.flush_recordset()
                    except TaskError as e:
                        raise Response400('C1400', str(e))

                    if approval_state == '0':
                        message = _('Workorder has been approved.')
                    else:
                        message = _('Workorder has been rejected.')
                    if task.approval_desc:
                        message += ' <em>%s</em>' % task.approval_desc
                    if task.reason_code:
                        message += ' <em>(%s)</em>' % task.reason_code
                    task.message_post(body=message)

                    response = Response200('C1200', {
                        'code': task.reason_code or '',
                        'message': task.approval_desc or '',
                    })

                elif task.stage_type == '1':
                    if not params.code == 'C1101':
                        raise Response400('C1400', _('This status code cannot be used in "%s" stage.') % task.stage_id.code)

                    reason = self.env['fsm.reason'].sudo().search([('code', '=', params.code)], limit=1)
                    values = {
                        'reason_id': reason.id,
                        'reason_code': reason.code,
                        'reason_name': getattr(params, 'message', False) or reason.name,
                    }

                    try:
                        with self.env.cr.savepoint():
                            task.with_context(no_reason=True).sudo().write(values)
                    except TaskError as e:
                        raise Response400('C1400', str(e))

                    message = _('Workorder has been continuing.')
                    if task.reason_name:
                        message += ' <em>%s</em>' % task.reason_name
                    if task.reason_code:
                        message += ' <em>(%s)</em>' % task.reason_code
                    task.message_post(body=message)

                    response = Response200('C1200', {
                        'code': task.reason_code or '',
                        'message': task.reason_name or '',
                    })

                else:
                    raise Response400('C1400', _('This service cannot be used in "%s" stage.') % task.stage_id.code)

            elif self.code == 'cancelWorkorder':
                orderId, = self._args(log, *args, **kwargs)
                task = self.env['fsm.task'].sudo().search([('uid', '=', orderId)], limit=1)
                if not task:
                    raise Response404('C1404', _('Workorder cannot be found.'))

                flow_stage = task.flow_id.stage_ids.filtered(lambda s: s.stage_id.type == '3')
                if not flow_stage:
                    raise Response500('C1500', _('Workorder could not be cancelled. A server error occured.'))

                self._check_reason(task=task)

                code = 'C1103'
                reason = self.env['fsm.reason'].sudo().search([('code', '=', code)], limit=1)
                task.with_context(no_reason=True).sudo().write({
                    'flow_stage_id': flow_stage[0].id,
                    'reason_id': reason.id,
                    'reason_code': reason.code,
                    'reason_name': reason.name,
                })
                response = Response200(code, {
                    'code': code,
                    'message': reason.name or _('Workorder has been cancelled.'),
                })

            elif self.code == 'getInventoryCity':
                cityId, params = self._args(log, *args, **kwargs)
                projects = token.project_id.filtered(lambda p: p.state == 'confirm')
                limit = getattr(params, 'limit', 10) or 10
                offset = getattr(params, 'offset', 0) or 0
                locations = self.env['stock.location'].sudo().search([('fsm_state_id.code', '=', str(cityId).zfill(2)), ('warehouse_id', 'in', projects.mapped('warehouse_ids').ids)])
                domain = [] if self.spec_id.product_all else [('product_id', 'in', self.spec_id.product_all.ids)]
                domain += [
                    ('location_id', 'in', locations.ids),
                    ('product_id', 'in', projects.mapped('product_ids').ids),
                    ('product_id.fsm_ok', '=', True)
                ]
                count = self.env['stock.quant'].sudo().search_count(domain)
                products = self.env['stock.quant'].sudo().search(domain, offset=offset, limit=limit)
                size = len(products)
                if not products:
                    raise Response404('C1404', _('Product does not exist.'))

                response = Response200('C1200', {
                    'totalCount': count,
                    'pagination': {
                        'offset': offset,
                        'pageCount': math.ceil(count/size) if size else 0,
                        'pageSize': size,
                    },
                    'products': [{
                        'serialNumber': product.lot_id.name or '',
                        'model': product.product_id.default_code or '',
                        'operatingSystem': product.product_id.fsm_os or '',
                        'owner': product.owner_id.name or '',
                        'subpartner': product.fsm_subpartner_id.name or '',
                        'location': product.location_id.display_name or '',
                    } for product in products]
                }) 

            elif self.code == 'getInventoryCityProduct':
                cityId, model, params = self._args(log, *args, **kwargs)
                limit = getattr(params, 'limit', 10) or 10
                offset = getattr(params, 'offset', 0) or 0
                projects = token.project_id.filtered(lambda p: p.state == 'confirm')
                locations = self.env['stock.location'].sudo().search([('fsm_state_id.code', '=', str(cityId).zfill(2)), ('warehouse_id', 'in', projects.mapped('warehouse_ids').ids)])
                domain = [] if self.spec_id.product_all else [('product_id', 'in', self.spec_id.product_all.ids)]
                domain += [
                    ('location_id', 'in', locations.ids),
                    ('product_id', 'in', projects.mapped('product_ids').ids),
                    ('product_id.default_code', '=', model),
                    ('product_id.fsm_ok', '=', True),
                    ('product_id.fsm_product_type', '!=', 'MALZEME'),
                ]
                count = self.env['stock.quant'].sudo().search_count(domain)
                products = self.env['stock.quant'].sudo().search(domain, offset=offset, limit=limit)
                size = len(products)
                if not products:
                    raise Response404('C1404', _('Product does not exist.'))

                response = Response200('C1200', {
                    'totalCount': count,
                    'pagination': {
                        'offset': offset,
                        'pageCount': math.ceil(count/size) if size else 0,
                        'pageSize': size,
                    },
                    'products': [{
                        'serialNumber': product.lot_id.name or '',
                        'model': product.product_id.default_code or '',
                        'operatingSystem': product.product_id.fsm_os or '',
                        'owner': product.owner_id.name or '',
                        'subpartner': product.fsm_subpartner_id.name or '',
                        'location': product.location_id.display_name or '',
                    } for product in products]
                })

            elif self.code == 'getInventoryCityMaterial':
                cityId, model, params = self._args(log, *args, **kwargs)
                projects = token.project_id.filtered(lambda p: p.state == 'confirm')
                locations = self.env['stock.location'].sudo().search([('fsm_state_id.code', '=', str(cityId).zfill(2)), ('warehouse_id', 'in', projects.mapped('warehouse_ids').ids)])

                limit = getattr(params, 'limit', 10) or 10
                offset = getattr(params, 'offset', 0) or 0
                domain = [
                    ('location_id', 'in', locations.ids),
                    ('product_id.fsm_ok', '=', True),
                    ('product_id.default_code', '=', model),
                    ('product_id.fsm_product_type', '=', 'MALZEME'),
                ]
                count = self.env['stock.quant'].sudo().search_count(domain)
                materials = self.env['stock.quant'].sudo().search(domain, offset=offset, limit=limit)
                size = len(materials)
                if not materials:
                    raise Response404('C1404', _('Product does not exist.'))

                response = Response200('C1200', {
                    'totalCount': count,
                    'pagination': {
                        'offset': offset,
                        'pageCount': math.ceil(count/size) if size else 0,
                        'pageSize': size,
                    },
                    'materials': [{
                        'name': material.product_id.name or '',
                        'serialNumber': material.lot_id.name or '',
                        'count': int(material.quantity) or 0,
                        'location': material.location_id.display_name or '',
                    } for material in materials]
                })

            elif self.code == 'createSaleOrder':
                params, = self._args(log, *args, **kwargs)
                if getattr(params, 'customer', None):
                    partner, partner_invoice, partner_shipping = self._get_partner(params.customer)
                else:
                    partner = token.customer_id or token.partner_id
                    partner_invoice = token.customer_id or token.partner_id
                    partner_shipping = token.customer_id or token.partner_id

                lines = []
                warehouse = False
                company = self.env.company
                orders = self.env['sale.order'].sudo()
                products = params.get('products', [])
                for product in products:
                    prod = self.env['product.product'].sudo().search([('default_code', '=', product.model)], limit=1)
                    if not prod:
                        raise Response404('C1404', _('Product "%s" cannot be found.') % product.model)

                    line_values = {
                        'product_id': prod.id,
                        'name': prod.name,
                        'product_uom_qty': product.quantity,
                    }

                    if not warehouse:
                        warehouse = orders._get_fsm_warehouse_id(token.partner_id, company)
                    if not warehouse:
                        raise Response404('C1404', _('Warehouse cannot be found for %s.') % token.partner_id.name)

                    lines.append((0, 0, line_values))

                with self.env.cr.savepoint():
                    order = orders.create({
                        'partner_id': partner.id,
                        'partner_invoice_id': partner_invoice and partner_invoice.id or partner.id,
                        'partner_shipping_id': partner_shipping and partner_shipping.id or partner.id,
                        'access_token': str(uuid.uuid4()),
                        'order_line': lines,
                        'fsm_ok': True,
                        'fsm_ref': params.get('customerOrderId', False),
                        'fsm_channel': params.get('channel', False),
                        'fsm_warehouse_id': warehouse and warehouse.id,
                    })
                    order.flush_recordset()

                products = []
                for line in order.order_line:
                    if line.fsm_reserved_lot_ids:
                        for lot in line.fsm_reserved_lot_ids:
                            products.append({
                                'model': line.product_id.default_code,
                                'serialNumber': lot.name or '',
                            })
                    else:
                        products.append({
                            'model': line.product_id.default_code,
                            'serialNumber': '',
                        })

                response = Response200('C1200', {
                    'orderId': order.name,
                    'customerOrderId': params.get('customerOrderId', ''),
                    'products': products,
                })

            elif self.code == 'approveSaleOrder':
                orderId, params = self._args(log, *args, **kwargs)
                order = self.env['sale.order'].sudo().search([('name', '=', orderId)], limit=1)
                if not order:
                    raise Response404('C1404', _('Any sale order cannot found related to requested order number. Please check the order number and try again.'))

                if order.state in ('sale', 'done'):
                    raise Response400('C1400', _('This order has already been approved.'))

                value = {}
                if getattr(params, 'customer', None):
                    partner, partner_invoice, partner_shipping = self._get_partner(params.customer)
                    value.update({
                        'partner_id': partner.id,
                        'partner_invoice_id': partner_invoice and partner_invoice.id or partner.id,
                        'partner_shipping_id': partner_shipping and partner_shipping.id or partner.id,
                    })

                if getattr(params, 'customerOrderId', None):
                    value.update({'fsm_ref': params.customerOrderId or False})

                if getattr(params, 'channel', None):
                    value.update({'fsm_channel': params.channel or False})


                details = []
                for detail in params.get('customer', {}).get('details', []):
                    details.append((0, 0, {
                        'key': detail.get('key', False),
                        'value': detail.get('value', False),
                    }))
                if details:
                    value.update({'fsm_detail_ids': details})
 
                if value:
                    order.write(value)
                    if 'partner_shipping_id' in value and order.picking_ids:
                        for picking in order.picking_ids:
                            if picking.state not in ('done', 'cancel'):
                                picking.write({'partner_id': value['partner_shipping_id']})

                order.action_confirm()

                products = []
                for line in order.order_line:
                    if line.fsm_reserved_lot_ids:
                        for lot in line.fsm_reserved_lot_ids:
                            products.append({
                                'model': line.product_id.default_code,
                                'serialNumber': lot.name or '',
                            })
                    else:
                        products.append({
                            'model': line.product_id.default_code,
                            'serialNumber': '',
                        })

                response = Response200('C1200', {
                    'orderId': order.name,
                    'customerOrderId': order.fsm_ref or None,
                    'products': products,
                })

            elif self.code == 'cancelSaleOrder':
                orderId, = self._args(log, *args, **kwargs)
                order = self.env['sale.order'].sudo().search([('name', '=', orderId)], limit=1)
                if not order:
                    raise Response404('C1404', _('Order cannot be found.'))

                if 'carrier_state' in order.picking_ids._fields:
                    if not all(picking.carrier_state in (False, 'return_to_seller') for picking in order.picking_ids):
                        raise Response400('C1400', _('Due to this sale order has stock moves, you cannot cancel it.'))

                order._action_cancel()
                response = Response200('C1200', {
                    'errors': [{
                        'code': 'C1073',
                        'message': 'Sipariş iş ortağı tarafından iptal edildi'
                    }]
                })

            elif self.code == 'getSaleOrder':
                orderId, = self._args(log, *args, **kwargs)
                order = self.env['sale.order'].sudo().search([('name', '=', orderId)], limit=1)
                if not order:
                    raise Response404('C1404', _('Order cannot be found.'))

                products = []
                for line in order.order_line:
                    if line.move_ids:
                        for m in line.move_ids[-1]:
                            picking = m.picking_id
                            if m.state == 'cancel':
                                status = 'İPTAL'
                            elif m.state in ('draft', 'waiting', 'confirmed', 'partially_available', 'assigned'):
                                status = 'HAZIR'
                            elif m.state == 'done':
                                carrier_status = getattr(picking, 'carrier_state', False)
                                if carrier_status:
                                    if carrier_status in ('return_to_seller'):
                                        status = 'İADE EDİLDİ'
                                    if carrier_status in ('delivered'):
                                        status = 'TESLİM EDİLDİ'
                                    else:
                                        status = 'TESLİM ALINDI'
                                else:
                                    status = 'SİPARİŞ'
                            else:
                                status = 'SİPARİŞ'
                            reason = self.spec_id._get_reason(SALEORDER_REASON.get(status))

                            delivery = {
                                'id': picking.carrier_doc_id or '',
                                'carrier': picking.carrier_id.name or '',
                            }
                            if hasattr(picking, 'delivery_tracking_ids'):
                                trackings = picking.delivery_tracking_ids
                                if trackings:
                                    tracking = trackings[-1]
                                    delivery.update({
                                        'promisedDate': tracking.date_promised and tracking.date_promised.strftime('%Y-%m-%dT%H:%M:%SZ') or None,
                                        'transactionDate': tracking.transaction_datetime and tracking.transaction_datetime.strftime('%Y-%m-%dT%H:%M:%SZ') or None,
                                        'statusCode': tracking.status,
                                        'statusMessage': tracking.state,
                                        'statusDetail': tracking.transaction,
                                        'transactionHistory': [{
                                            'transactionDate': t.transaction_datetime and t.transaction_datetime.strftime('%Y-%m-%dT%H:%M:%SZ') or None,
                                            'statusCode': t.status,
                                            'statusMessage': t.state,
                                            'statusDetail': t.transaction,
                                            'nonDeliveryReason': t.delivery_return_reason or None,
                                            'nonDeliveryReasonMessage': t.delivery_return_reason_message or None,
                                        } for t in trackings]
                                    })

                            product_value = {
                                'model': m.product_id.default_code,
                                'serialNumber': '',
                                'status': status,
                                'statusCode': reason[0],
                                'statusMessage': reason[2],
                                'delivery': delivery,
                            }
                            if m.move_line_ids:
                                for l in m.move_line_ids:
                                    product_value.update({'serialNumber': l.lot_id.name or ''})
                                    products.append({**product_value})
                            else:
                                if m.sale_line_id.fsm_reserved_lot_ids:
                                    for l in m.sale_line_id.fsm_reserved_lot_ids:
                                        product_value.update({'serialNumber': l.name or ''})
                                        products.append({**product_value})
                                else:
                                    product_value.update({'serialNumber': ''})
                                    products.append({**product_value})

                    elif line.state == 'cancel':
                        status = 'İPTAL'
                        reason = self.spec_id._get_reason(SALEORDER_REASON.get(status))
                        product_value = {
                            'model': line.product_id.default_code,
                            'serialNumber': '',
                            'status': status,
                            'statusCode': reason[0],
                            'statusMessage': reason[2],
                            'delivery': {},
                        }
                        if line.fsm_reserved_lot_ids:
                            for lot in line.fsm_reserved_lot_ids:
                                product_value.update({'serialNumber': lot.name or ''})
                                products.append({**product_value})
                        else:
                            product_value.update({'serialNumber': ''})
                            products.append({**product_value})
                        
                    else:
                        status = 'TEKLİF'
                        reason = self.spec_id._get_reason(SALEORDER_REASON.get(status))
                        product_value = {
                            'model': line.product_id.default_code,
                            'serialNumber': '',
                            'status': status,
                            'statusCode': reason[0],
                            'statusMessage': reason[2],
                            'delivery': {},
                        }
                        if line.fsm_reserved_lot_ids:
                            for lot in line.fsm_reserved_lot_ids:
                                product_value.update({'serialNumber': lot.name or ''})
                                products.append({**product_value})
                        else:
                            product_value.update({'serialNumber': ''})
                            products.append({**product_value})

                response = Response200('C1200', {
                    'orderId': order.name,
                    'customerOrderId': order.fsm_ref or None,
                    'products': products,
                })

            elif self.code == 'getInfoOrdertype':
                params, = self._args(log, *args, **kwargs)
                limit = getattr(params, 'limit', 10) or 10
                offset = getattr(params, 'offset', 0) or 0
                domain = [] if self.spec_id.type_all else [('id', 'in', self.spec_id.type_ids.ids)]
                projects = token.project_id.filtered(lambda p: p.state == 'confirm')
                domain += [('id', 'in', projects.mapped('type_ids.type_id').ids)]
                count = self.env['fsm.type'].sudo().search_count(domain)
                types = self.env['fsm.type'].sudo().search(domain, offset=offset, limit=limit)
                size = len(types)
                if not types:
                    raise Response404('C1404')

                response = Response200('C1200', {
                    'totalCount': count,
                    'pagination': {
                        'offset': offset,
                        'pageCount': math.ceil(count/size) if size else 0,
                        'pageSize': size,
                    },
                    #'orderTypes': [t.code for t in types]
                    'orderTypes': [{
                        'name': t.code,
                    } for t in types]
                })

            elif self.code == 'getInfoProject':
                params, = self._args(log, *args, **kwargs)
                limit = getattr(params, 'limit', 10) or 10
                offset = getattr(params, 'offset', 0) or 0
                project = token.project_id.filtered(lambda p: p.state == 'confirm')
                domain = [('project_id', '=', project.id), ('state', '=', 'confirm')]
                count = self.env['fsm.project.item'].sudo().search_count(domain)
                projects = self.env['fsm.project.item'].sudo().search(domain, offset=offset, limit=limit)
                size = len(projects)
                if not projects:
                    raise Response404('C1404')

                response = Response200('C1200', {
                    'totalCount': count,
                    'pagination': {
                        'offset': offset,
                        'pageCount': math.ceil(count/size) if size else 0,
                        'pageSize': size,
                    },
                    'projects': [{
                        'id': project.uid,
                        'name': project.name,
                        'sla': project.sla_id.code or '',
                        'maximumCount': project.task_maximum or 0,
                        'dateStart': project.date_start.strftime('%Y-%m-%d'),
                        'dateEnd': project.date_end.strftime('%Y-%m-%d'),
                    } for project in projects]
                })

            elif self.code == 'getInfoSubpartner':
                params, = self._args(log, *args, **kwargs)
                limit = getattr(params, 'limit', 10) or 10
                offset = getattr(params, 'offset', 0) or 0
                projects = token.project_id.filtered(lambda p: p.state == 'confirm')
                domain = [('project_id', 'in', projects.ids)]
                count = self.env['fsm.project.subpartner'].sudo().search_count(domain)
                subpartners = self.env['fsm.project.subpartner'].sudo().search(domain, offset=offset, limit=limit, order='project_id desc, sequence asc, partner_id asc')
                size = len(subpartners)
                if not subpartners:
                    raise Response404('C1404')

                response = Response200('C1200', {
                    'totalCount': count,
                    'pagination': {
                        'offset': offset,
                        'pageCount': math.ceil(count/size) if size else 0,
                        'pageSize': size,
                    },
                    'subpartners': [{
                        'name': subpartner.partner_id.name,
                    } for subpartner in subpartners]
                })

            elif self.code == 'getInfoCity':
                params, = self._args(log, *args, **kwargs)
                limit = getattr(params, 'limit', 10) or 10
                offset = getattr(params, 'offset', 0) or 0
                domain = [('country_id.code', '=', 'TR')]
                count = self.env['res.country.state'].sudo().search_count(domain)
                cities = self.env['res.country.state'].sudo().search(domain, offset=offset, limit=limit)
                size = len(cities)
                if not cities:
                    raise Response404('C1404')

                response = Response200('C1200', {
                    'totalCount': count,
                    'pagination': {
                        'offset': offset,
                        'pageCount': math.ceil(count/size) if size else 0,
                        'pageSize': size,
                    },
                    'cities': [{
                        'id': city.code,
                        'name': city.name,
                    } for city in cities]
                })

            elif self.code == 'getInfoTown':
                cityId, params = self._args(log, *args, **kwargs)
                limit = getattr(params, 'limit', 10) or 10
                offset = getattr(params, 'offset', 0) or 0
                domain = [('state_id.country_id.code', '=', 'TR'), ('state_id.code', '=', str(cityId).zfill(2))]
                count = self.env['res.country.town'].sudo().search_count(domain)
                towns = self.env['res.country.town'].sudo().search(domain, offset=offset, limit=limit)
                size = len(towns)
                if not towns:
                    raise Response404('C1404')

                response = Response200('C1200', {
                    'totalCount': count,
                    'pagination': {
                        'offset': offset,
                        'pageCount': math.ceil(count/size) if size else 0,
                        'pageSize': size,
                    },
                    'towns': [{
                        'id': town.code,
                        'name': town.name,
                    } for town in towns]
                })

            elif self.code == 'getInfoDistrict':
                cityId, townId, params = self._args(log, *args, **kwargs)
                limit = getattr(params, 'limit', 10) or 10
                offset = getattr(params, 'offset', 0) or 0
                domain = [('town_id.state_id.country_id.code', '=', 'TR'), ('town_id.state_id.code', '=', str(cityId).zfill(2)), ('town_id.code', '=', str(townId))]
                count = self.env['res.country.district'].sudo().search_count(domain)
                districts = self.env['res.country.district'].sudo().search(domain, offset=offset, limit=limit)
                size = len(districts)
                if not districts:
                    raise Response404('C1404')

                response = Response200('C1200', {
                    'totalCount': count,
                    'pagination': {
                        'offset': offset,
                        'pageCount': math.ceil(count/size) if size else 0,
                        'pageSize': size,
                    },
                    'districts': [{
                        'id': district.code,
                        'name': district.name,
                    } for district in districts]
                })

            elif self.code == 'getInfoZone':
                cityId, townId, params = self._args(log, *args, **kwargs)
                partner = token.partner_id
                limit = getattr(params, 'limit', 10) or 10
                offset = getattr(params, 'offset', 0) or 0
                domain = [
                    ('agreement_id.state', '=', 'confirm'),
                    ('agreement_id.partner_id', '=', partner.id),
                    ('agreement_id.fsm_project_ids.state', '=', 'confirm'),
                    ('agreement_id.fsm_project_ids.partner_id', '=', partner.id),
                    ('fsm_service_zone_id.state_id.country_id.code', '=', 'TR'),
                    ('fsm_service_zone_id.state_id.code', '=', str(cityId).zfill(2)),
                    ('fsm_service_zone_id.town_id.code', '=', str(townId)),
                ]
                count = self.env['sla.agreement.hour'].sudo().search_count(domain)
                hours = self.env['sla.agreement.hour'].sudo().search(domain, offset=offset, limit=limit)
                size = len(hours)
                if not hours:
                    raise Response404('C1404')

                response = Response200('C1200', {
                    'totalCount': count,
                    'pagination': {
                        'offset': offset,
                        'pageCount': math.ceil(count/size) if size else 0,
                        'pageSize': size,
                    },
                    'towns': [{
                        'id': hour.fsm_service_zone_id.town_id.code,
                        'name': hour.fsm_service_zone_id.town_id.name,
                        'agreementName': hour.agreement_id.code,
                        'serviceType': hour.fsm_service_zone_id.type_id.code,
                        'serviceLevel': f'%.{2 if hour.value % 1 else 0}f' % hour.value,
                    } for hour in hours]
                })

            elif self.code == 'getInfoTaxoffice':
                cityId, params = self._args(log, *args, **kwargs)
                limit = getattr(params, 'limit', 10) or 10
                offset = getattr(params, 'offset', 0) or 0
                domain = [('state_id.country_id.code', '=', 'TR'), ('state_id.code', '=', str(cityId).zfill(2))]
                count = self.env['account.tax.office'].sudo().search_count(domain)
                offices = self.env['account.tax.office'].sudo().search(domain, limit=limit, offset=offset)
                size = len(offices)
                if not offices:
                    raise Response404('C1404')

                response = Response200('C1200', {
                    'totalCount': count,
                    'pagination': {
                        'offset': offset,
                        'pageCount': math.ceil(count/size) if size else 0,
                        'pageSize': size,
                    },
                    'taxoffices': [{
                        'id': office.code,
                        'name': office.name,
                    } for office in offices]
                })

            elif self.code == 'getInfoStatuscode':
                params, = self._args(log, *args, **kwargs)
                limit = getattr(params, 'limit', 10) or 10
                offset = getattr(params, 'offset', 0) or 0
                project = token.project_id
                domain = [] if self.spec_id.reason_all else [('id', 'in', self.spec_id.reason_ids.ids)]
                count = self.env['fsm.reason'].sudo().search_count(domain + [('project_ids', 'in', [project.id])])
                if count:
                    domain.append(('project_ids', 'in', [project.id]))
                else:
                    count = self.env['fsm.reason'].sudo().search_count(domain)
                statuscodes = self.env['fsm.reason'].sudo().search(domain, limit=limit, offset=offset)
                size = len(statuscodes)
                if not statuscodes:
                    raise Response404('C1404')

                response = Response200('C1200', {
                    'totalCount': count,
                    'pagination': {
                        'offset': offset,
                        'pageCount': math.ceil(count/size) if size else 0,
                        'pageSize': size,
                    },
                    'statuscodes': [{
                        'code': statuscode.code or None,
                        'message': statuscode.name or None,
                        'httpCode': statuscode.status or None,
                    } for statuscode in statuscodes]
                })

            elif self.code == 'downloadDeliveryContract':
                reference, = self._args(log, *args, **kwargs)

                picking = self.env['stock.picking'].sudo().search([('carrier_tracking_ref', '=', reference)], limit=1)
                if not picking:
                    raise Response404('C1404')

                #pdf = picking.carrier_id.render_contract(picking)
                #response = Response200('', pdf or b'')

                contract = getattr(picking, 'delivery_contract_rendered_id', None)
                if not contract:
                    pdf = picking.carrier_id.render_contract(picking, code=picking.fsm_task_id.document_type)
                    contract = self.env['ir.attachment'].sudo().create({
                        'type': 'binary',
                        'name': _('%s (rendered).pdf') % reference,
                        'mimetype': 'application/pdf',
                        'delivery_contract_rendered': True,
                        'res_model': picking._name,
                        'res_id': picking.id,
                        'datas': base64.b64encode(pdf),
                    })
                response = Response200('', base64.b64decode(contract.datas) or b'')

            elif self.code == 'uploadDeliveryContract':
                reference, __ = self._args(log, *args, **kwargs)
                content = request.httprequest.get_data()

                picking = self.env['stock.picking'].sudo().search([('carrier_tracking_ref', '=', reference)], limit=1)
                if not picking:
                    raise Response404('C1404')

                contract = getattr(picking, 'delivery_contract_signed_id', None)
                contract_signed = not contract
                mimetype = guess_mimetype(base64.b64decode(content))
                extension = '.' + mimetype.split('/')[1]
                if extension == '.svg+xml':
                    extension = '.svg'
                attachment = self.env['ir.attachment'].sudo().create({
                    'type': 'binary',
                    'name': '%s%s%s' % (reference, _(' (signed)') if contract_signed else '', extension),
                    'delivery_contract_signed': contract_signed,
                    'res_model': picking._name,
                    'res_id': picking.id,
                    'mimetype': mimetype,
                    'datas': content,
                })
                response = Response200('', None)

        except Exception as e:
            response = self.spec_id._get_error(e, log)

        if isinstance(response[1], dict):
            log.update({'response': json.dumps(response[1], indent=4, default=str, ensure_ascii=False)})
        else:
            log.update({'response': '', 'req': ''})

        if response[0] != '200':
            log.update({
                'status': False,
                'code': response[0],
                'message': response[1]['errors'][0]['message'],
            })

        if task:
            log.update({'task': task.id})

        try:
            with self.env.cr.savepoint():
                self._log(log)
        except:
            _logger.error('Log cannot be saved. Response code was %s and details as follows:\n%s' % (response[0], json.dumps(response[1], default=str, indent=4)))
        return response

    def _get_merchant(self, params):
        if not params:
            raise Response404('C1404', _('Data is missing.'))

        country = self.env['res.country'].sudo().search([('code', '=', 'TR')])
        if not country:
            raise Response404('C1404', _('Country is missing.'))
            
        if not getattr(params, 'taxNumber', None):
            raise Response422('C1422', [{
                'field': 'taxNumber',
                'issue': _('Field is missing.'),
            }])

        value = {}
        contact_value = {}
        service_value = {}
        service_contact_value = {}
        partner = self.env['res.partner'].sudo()
        proxy = self.env.context.get('proxy', {})

        if getattr(params, 'name', None):
            value.update({'name': params.get('name', False)})

        if getattr(params, 'tableName', None):
            value.update({'table_name': params.get('tableName', False)})

        if getattr(params, 'taxOffice', None) and 'tax_office_id' in partner._fields:
            tax_office_name = params.get('taxOffice', '').split(' ', 1)[0]
            tax_office = self.env['account.tax.office'].sudo().search([('name', 'ilike', '%s%%' % tax_office_name)], limit=1)
            if tax_office:
                value.update({'tax_office_id': tax_office.id})

        address_primary = getattr(params, 'primaryAddress', object())
        address_service = getattr(params, 'serviceAddress', None)

        if getattr(address_primary, 'contactName', None):
            contact_value.update({
                'is_company': False,
                'type': 'contact',
                'name': address_primary.get('contactName', False),
            })

        if getattr(address_primary, 'phoneNumber', None):
            value.update({'phone': address_primary.get('phoneNumber', False)})
        elif getattr(address_primary, 'phoneNumber1', None):
            value.update({'phone': address_primary.get('phoneNumber1', False)})
        if getattr(address_primary, 'phoneNumber2', None) and 'phone2' in partner._fields:
            value.update({'phone2': address_primary.get('phoneNumber2', False)})

        if getattr(address_primary, 'mobileNumber', None):
            value.update({'mobile': address_primary.get('mobileNumber', False)})
        elif getattr(address_primary, 'mobile', None):
            value.update({'mobile': address_primary.get('mobile', False)})

        if getattr(address_primary, 'email', None):
            email = address_primary.get('email', False)
            if email != '_@00.zz':
                value.update({'email': address_primary.get('email', False)})

        if getattr(address_primary, 'mersisNumber', None):
            value.update({'company_registry': address_primary.get('mersisNumber', False)})

        if getattr(address_primary, 'tradeRegistrationNumber', None) and 'trade_reg_number' in partner._fields:
            value.update({'trade_reg_number': address_primary.get('tradeRegistrationNumber', False)})

        if getattr(address_primary, 'city', None):
            name = address_primary.get('city', {}).get('name', 0)
            code = address_primary.get('city', {}).get('id', 0)
            codes = proxy.get('cities', {})
            code = str(code)
            if code:
                if code in codes:
                    code = codes[code]
                code = code.zfill(2)
                city = self.env['res.country.state'].sudo().search([('country_id', '=', country.id), ('code', '=', code)], limit=1)
            else:
                city = self.env['res.country.state'].sudo().search([('country_id', '=', country.id), ('name', '=', name)], limit=1)
            if not city:
                raise Response404('C1404', _('City cannot be found.'))
            elif not codes and city.name != name:
                raise Response400('C1400', _('City name is not matched.'))
            value.update({'state_id': city.id, 'country_id': country.id})

        if getattr(address_primary, 'town', None):
            name = address_primary.get('town', {}).get('name', 0)
            code = address_primary.get('town', {}).get('id', 0)
            codes = proxy.get('towns', {})
            code = str(code)
            if code:
                if code in codes:
                    code = codes[code]
                code = code.zfill(2)
                town = self.env['res.country.town'].sudo().search([('state_id.country_id', '=', country.id), ('code', '=', code)], limit=1)
            else:
                town = self.env['res.country.town'].sudo().search([('state_id.country_id', '=', country.id), ('name', '=', name)], limit=1)
            if not town:
                raise Response404('C1404', _('Town cannot be found.'))
            elif not codes and town.name != name:
                raise Response400('C1400', _('Town name is not matched.'))
            value.update({'town_id': town.id})

        if getattr(address_primary, 'district', None):
            name = address_primary.get('district', {}).get('name', 0)
            code = address_primary.get('district', {}).get('id', 0)
            if code:
                code = str(code).zfill(2)
                district = self.env['res.country.district'].sudo().search([('town_id.state_id.country_id', '=', country.id), ('code', '=', code)], limit=1)
            else:
                district = self.env['res.country.district'].sudo().search([('town_id.state_id.country_id', '=', country.id), ('name', '=', name)], limit=1)
            if not district:
                #raise Response404('C1404', _('District cannot be found.'))
                district = self.env['res.country.district'].sudo().create({'town_id': town.id, 'name': name, 'code': code})
            value.update({'district_id': district.id})

        if getattr(address_primary, 'address', None):
            value.update({'street2': address_primary.get('address', False)})

        if getattr(address_primary, 'zipCode', None):
            value.update({'zip': address_primary.get('zipCode', False)})

        if getattr(address_primary, 'latitude', None):
            value.update({'partner_latitude': address_primary.get('latitude', False)})

        if getattr(address_primary, 'longitude', None):
            value.update({'partner_longitude': address_primary.get('longitude', False)})

        if getattr(address_primary, 'uavtCode', None):
            value.update({'uavt_code': address_primary.get('uavtCode', False)})

        if getattr(address_service, 'name', None):
            service_value.update({
                'is_company': len(params.get('taxNumber', '')) == 10,
                'type': 'service',
                'name': address_service.get('name', False),
            })

        if getattr(address_service, 'tableName', None):
            service_value.update({'table_name': address_service.get('tableName', False)})

        if getattr(address_service, 'contactName', None):
            service_contact_value.update({
                'is_company': False,
                'type': 'contact',
                'name': address_service.get('contactName', False),
            })

        if getattr(address_service, 'phoneNumber', None):
            service_value.update({'phone': address_service.get('phoneNumber', False)})
        elif getattr(address_service, 'phoneNumber1', None):
            service_value.update({'phone': address_service.get('phoneNumber1', False)})
        if getattr(address_service, 'phoneNumber2', None) and 'phone2' in partner._fields:
            service_value.update({'phone2': address_service.get('phoneNumber2', False)})

        if getattr(address_service, 'mobileNumber', None):
            service_value.update({'mobile': address_service.get('mobileNumber', False)})
        elif getattr(address_service, 'mobile', None):
            service_value.update({'mobile': address_service.get('mobile', False)})

        if getattr(address_service, 'email', None):
            email = address_service.get('email', False)
            if email != '_@00.zz':
                service_value.update({'email': address_service.get('email', False)})

        if getattr(address_service, 'mersisNumber', None):
            service_value.update({'company_registry': address_service.get('mersisNumber', False)})

        if getattr(address_service, 'city', None):
            name = address_service.get('city', {}).get('name', 0)
            code = address_service.get('city', {}).get('id', 0)
            codes = proxy.get('cities', {})
            code = str(code)
            if code:
                if code in codes:
                    code = codes[code]
                code = code.zfill(2)
                city = self.env['res.country.state'].sudo().search([('country_id', '=', country.id), ('code', '=', code)], limit=1)
            else:
                city = self.env['res.country.state'].sudo().search([('country_id', '=', country.id), ('name', '=', name)], limit=1)
            if not city:
                raise Response404('C1404', _('City cannot be found.'))
            elif not codes and city.name != name:
                raise Response400('C1400', _('City name is not matched.'))
            service_value.update({'state_id': city.id, 'country_id': country.id})

        if getattr(address_service, 'town', None):
            name = address_service.get('town', {}).get('name', 0)
            code = address_service.get('town', {}).get('id', 0)
            codes = proxy.get('towns', {})
            code = str(code)
            if code:
                if code in codes:
                    code = codes[code]
                code = code.zfill(2)
                town = self.env['res.country.town'].sudo().search([('state_id.country_id', '=', country.id), ('code', '=', code)], limit=1)
            else:
                town = self.env['res.country.town'].sudo().search([('state_id.country_id', '=', country.id), ('name', '=', name)], limit=1)
            if not town:
                raise Response404('C1404', _('Town cannot be found.'))
            elif not codes and town.name != name:
                raise Response400('C1400', _('Town name is not matched.'))
            service_value.update({'town_id': town.id})

        if getattr(address_service, 'district', None):
            name = address_service.get('district', {}).get('name', 0)
            code = address_service.get('district', {}).get('id', 0)
            if code:
                code = str(code).zfill(2)
                district = self.env['res.country.district'].sudo().search([('town_id.state_id.country_id', '=', country.id), ('code', '=', code)], limit=1)
            else:
                district = self.env['res.country.district'].sudo().search([('town_id.state_id.country_id', '=', country.id), ('name', '=', name)], limit=1)
            if not district:
                #raise Response404('C1404', _('District cannot be found.'))
                district = self.env['res.country.district'].sudo().create({'town_id': town.id, 'name': name, 'code': code})
            service_value.update({'district_id': district.id})

        if getattr(address_service, 'address', None):
            service_value.update({'street2': address_service.get('address', False)})

        if getattr(address_service, 'zipCode', None):
            service_value.update({'zip': address_service.get('zipCode', False)})

        if getattr(address_service, 'latitude', None):
            service_value.update({'partner_latitude': address_service.get('latitude', False)})

        if getattr(address_service, 'longitude', None):
            service_value.update({'partner_longitude': address_service.get('longitude', False)})

        if getattr(address_service, 'uavtCode', None):
            service_value.update({'uavt_code': address_service.get('uavtCode', False)})

        partner = getattr(params, 'taxNumber', None) and partner.search([('vat', 'like', '%%%s' % params.get('taxNumber'))], limit=1)
        if partner:
            partner.sudo().write(value)
        else:
            value.update({'is_company': len(params.get('taxNumber', '')) == 10, 'vat': params.get('taxNumber', False)})
            partner = partner.sudo().create(value)

        contact_partner = None
        if contact_value:
            contact_partner = partner.search([
                ('type', '=', 'contact'),
                ('is_company', '=', False),
                ('parent_id', '=', partner.id),
                ('name', '=', contact_value['name']),
            ], limit=1)
            if not contact_partner:
                contact_value.update({'parent_id': partner.id})
                contact_partner = partner.sudo().create(contact_value)
            else:
                contact_partner.sudo().write(contact_value)

        service_partner = partner
        if service_value:
            service_partner = partner.search([
                ('type', '=', 'service'),
                ('parent_id', '=', partner.id),
                ('name', '=', service_value['name']),
                ('is_company', '=', service_value['is_company']),
                ('phone', '=', service_value.get('phone', False)),
                ('mobile', '=', service_value.get('mobile', False)),
                ('email', '=', service_value.get('email', False)),
                ('street', '=', service_value.get('street2', False)),
                ('state_id.code', '=', str(service_value.get('city', {}).get('id', False))),
                ('town_id.code', '=', str(service_value.get('town', {}).get('id', False))),
                ('district_id.code', '=', str(service_value.get('district', {}).get('id', False))),
            ], limit=1)
            if not service_partner:
                service_value.update({'parent_id': partner.id})
                service_partner = partner.sudo().create(service_value)
            else:
                service_partner.sudo().write(service_value)

            if service_contact_value:
                service_contact_partner = service_partner.search([
                    ('type', '=', 'contact'),
                    ('is_company', '=', False),
                    ('parent_id', '=', service_partner.id),
                    ('name', '=', service_contact_value['name']),
                ], limit=1)
                if not service_contact_partner:
                    service_contact_value.update({'parent_id': service_partner.id})
                    service_contact_partner = partner.sudo().create(service_contact_value)
                else:
                    service_contact_partner.sudo().write(service_contact_value)

        return partner, service_partner

    def _get_partner(self, params):
        if not params:
            raise Response404('C1404', _('Data is missing.'))

        country = self.env['res.country'].sudo().search([('code', '=', 'TR')])
        if not country:
            raise Response404('C1404', _('Country is missing.'))
            
        #if not getattr(params, 'taxNumber', None):
        #    raise Response422('C1422', [{
        #        'field': 'taxNumber',
        #        'issue': _('Field is missing.'),
        #    }])

        value = {}
        value_invoice = {}
        value_shipping = {}
        #value_invoice_contact = {}
        #value_shipping_contact = {}
        partner = self.env['res.partner'].sudo()

        if getattr(params, 'isCompany', None):
            value.update({'is_company': params.get('isCompany', False)})

        if getattr(params, 'name', None):
            value.update({'name': params.get('name', False)})

        if getattr(params, 'tableName', None):
            value.update({'table_name': params.get('tableName', False)})

        if getattr(params, 'taxNumber', None):
            value.update({'vat': params.get('taxNumber', False)})

        if getattr(params, 'taxOffice', None) and 'tax_office_id' in partner._fields:
            tax_office_name = params.get('taxOffice', '').split(' ', 1)[0]
            tax_office = self.env['account.tax.office'].sudo().search([('name', 'ilike', '%s%%' % tax_office_name)], limit=1)
            if tax_office:
                value.update({'tax_office_id': tax_office.id})

        address_invoice = getattr(params, 'billingAddress', None)
        address_delivery = getattr(params, 'shippingAddress', None)

        if address_invoice:
            #if getattr(address_invoice, 'contactName', None):
            #    value_invoice_contact.update({
            #        'is_company': False,
            #        'type': 'contact',
            #        'name': address_invoice.get('contactName', False),
            #        'vat': address_invoice.get('identityNumber', False),
            #    })

            if getattr(address_invoice, 'contactName', None):
                value_invoice.update({'name': address_invoice.get('contactName', False)})

            if getattr(address_invoice, 'identityNumber', None):
                value_invoice.update({'vat': address_invoice.get('identityNumber', False)})

            if getattr(address_invoice, 'phoneNumber', None):
                value_invoice.update({'phone': address_invoice.get('phoneNumber', False)})

            if getattr(address_invoice, 'mobile', None):
                value_invoice.update({'mobile': address_invoice.get('mobile', False)})

            if getattr(address_invoice, 'email', None):
                value_invoice.update({'email': address_invoice.get('email', False)})

            if getattr(address_invoice, 'mersisNumber', None):
                value_invoice.update({'company_registry': address_invoice.get('mersisNumber', False)})

            if getattr(address_invoice, 'tradeRegistrationNumber', None) and 'trade_reg_number' in partner._fields:
                value_invoice.update({'trade_reg_number': address_invoice.get('tradeRegistrationNumber', False)})

            if getattr(address_invoice, 'city', None):
                name = address_invoice.get('city', {}).get('name', 0)
                code = str(address_invoice.get('city', {}).get('id', 0)).zfill(2)
                city = self.env['res.country.state'].sudo().search([('country_id', '=', country.id), ('code', '=', code)], limit=1)
                if not city:
                    raise Response404('C1404', _('City cannot be found.'))
                elif city.name != name:
                    raise Response400('C1400', _('City name is not matched.'))
                value_invoice.update({'state_id': city.id, 'country_id': country.id})

            if getattr(address_invoice, 'town', None):
                name = address_invoice.get('town', {}).get('name', 0)
                code = str(address_invoice.get('town', {}).get('id', 0))
                town = self.env['res.country.town'].sudo().search([('state_id.country_id', '=', country.id), ('code', '=', code)], limit=1)
                if not town:
                    raise Response404('C1404', _('Town cannot be found.'))
                elif town.name != name:
                    raise Response400('C1400', _('Town name is not matched.'))
                value_invoice.update({'town_id': town.id})

            if getattr(address_invoice, 'district', None):
                name = address_invoice.get('district', {}).get('name', 0)
                code = str(address_invoice.get('district', {}).get('id', 0))
                district = self.env['res.country.district'].sudo().search([('town_id.state_id.country_id', '=', country.id), ('code', '=', code)], limit=1)
                if not district:
                    #raise Response404('C1404', _('District cannot be found.'))
                    district = self.env['res.country.district'].sudo().create({'town_id': town.id, 'name': name, 'code': code})
                value_invoice.update({'district_id': district.id})

            if getattr(address_invoice, 'address', None):
                value_invoice.update({'street2': address_invoice.get('address', False)})

            if getattr(address_invoice, 'zipCode', None):
                value_invoice.update({'zip': address_invoice.get('zipCode', False)})

            if getattr(address_invoice, 'latitude', None):
                value_invoice.update({'partner_latitude': address_invoice.get('latitude', False)})

            if getattr(address_invoice, 'longitude', None):
                value_invoice.update({'partner_longitude': address_invoice.get('longitude', False)})

            if getattr(address_invoice, 'uavtCode', None):
                value_invoice.update({'uavt_code': address_invoice.get('uavtCode', False)})

        if address_delivery:
            #if getattr(address_delivery, 'contactName', None):
            #    value_shipping_contact.update({
            #        'is_company': False,
            #        'type': 'contact',
            #        'name': address_delivery.get('contactName', False),
            #        'vat': address_delivery.get('identityNumber', False),
            #    })

            if getattr(address_delivery, 'contactName', None):
                value_shipping.update({'name': address_delivery.get('contactName', False)})

            if getattr(address_delivery, 'identityNumber', None):
                value_shipping.update({'vat': address_delivery.get('identityNumber', False)})

            if getattr(address_delivery, 'phoneNumber', None):
                value_shipping.update({'phone': address_delivery.get('phoneNumber', False)})

            if getattr(address_delivery, 'mobile', None):
                value_shipping.update({'mobile': address_delivery.get('mobile', False)})

            if getattr(address_delivery, 'email', None):
                value_shipping.update({'email': address_delivery.get('email', False)})

            if getattr(address_delivery, 'mersisNumber', None):
                value_shipping.update({'company_registry': address_delivery.get('mersisNumber', False)})

            if getattr(address_delivery, 'tradeRegistrationNumber', None) and 'trade_reg_number' in partner._fields:
                value_shipping.update({'trade_reg_number': address_delivery.get('tradeRegistrationNumber', False)})

            if getattr(address_delivery, 'city', None):
                name = address_delivery.get('city', {}).get('name', 0)
                code = str(address_delivery.get('city', {}).get('id', 0)).zfill(2)
                city = self.env['res.country.state'].sudo().search([('country_id', '=', country.id), ('code', '=', code)], limit=1)
                if not city:
                    raise Response404('C1404', _('City cannot be found.'))
                elif city.name != name:
                    raise Response400('C1400', _('City name is not matched.'))
                value_shipping.update({'state_id': city.id, 'country_id': country.id})

            if getattr(address_delivery, 'town', None):
                name = address_delivery.get('town', {}).get('name', 0)
                code = str(address_delivery.get('town', {}).get('id', 0))
                town = self.env['res.country.town'].sudo().search([('state_id.country_id', '=', country.id), ('code', '=', code)], limit=1)
                if not town:
                    raise Response404('C1404', _('Town cannot be found.'))
                elif town.name != name:
                    raise Response400('C1400', _('Town name is not matched.'))
                value_shipping.update({'town_id': town.id})

            if getattr(address_delivery, 'district', None):
                name = address_delivery.get('district', {}).get('name', 0)
                code = str(address_delivery.get('district', {}).get('id', 0))
                district = self.env['res.country.district'].sudo().search([('town_id.state_id.country_id', '=', country.id), ('code', '=', code)], limit=1)
                if not district:
                    #raise Response404('C1404', _('District cannot be found.'))
                    district = self.env['res.country.district'].sudo().create({'town_id': town.id, 'name': name, 'code': code})
                value_shipping.update({'district_id': district.id})

            if getattr(address_delivery, 'address', None):
                value_shipping.update({'street2': address_delivery.get('address', False)})

            if getattr(address_delivery, 'zipCode', None):
                value_shipping.update({'zip': address_delivery.get('zipCode', False)})

            if getattr(address_delivery, 'latitude', None):
                value_shipping.update({'partner_latitude': address_delivery.get('latitude', False)})

            if getattr(address_delivery, 'longitude', None):
                value_shipping.update({'partner_longitude': address_delivery.get('longitude', False)})

            if getattr(address_delivery, 'uavtCode', None):
                value_shipping.update({'uavt_code': address_delivery.get('uavtCode', False)})

        partner = getattr(params, 'taxNumber', None) and partner.search([('vat', 'like', '%%%s' % params.get('taxNumber'))], limit=1)
        if not partner:
            if getattr(params, 'taxNumber', None):
                value.update({'vat': params.get('taxNumber', False)})
            partner = self.env['res.partner'].sudo().create(value)
        else:
            partner.sudo().write(value)

        partner_invoice = None
        if value_invoice:
            partner_invoice = partner.search([
                ('type', '=', 'invoice'),
                ('parent_id', '=', partner.id),
                ('vat', '=', value_invoice.get('vat', False)),
                ('name', '=', value_invoice.get('name', False)),
                ('phone', '=', value_invoice.get('phone', False)),
                ('mobile', '=', value_invoice.get('mobile', False)),
                ('email', '=', value_invoice.get('email', False)),
                ('street', '=', value_invoice.get('street2', False)),
                ('state_id.code', '=', str(value_invoice.get('city', {}).get('id', False))),
                ('town_id.code', '=', str(value_invoice.get('town', {}).get('id', False))),
                ('district_id.code', '=', str(value_invoice.get('district', {}).get('id', False))),
            ], limit=1)
            if not partner_invoice:
                value_invoice.update({'parent_id': partner.id, 'type': 'invoice'})
                partner_invoice = partner.sudo().create(value_invoice)
            else:
                partner_invoice.sudo().write(value_invoice)

        partner_shipping = None
        if value_shipping:
            partner_shipping = partner.search([
                ('type', '=', 'delivery'),
                ('parent_id', '=', partner.id),
                ('vat', '=', value_shipping.get('vat', False)),
                ('name', '=', value_shipping.get('name', False)),
                ('phone', '=', value_shipping.get('phone', False)),
                ('mobile', '=', value_shipping.get('mobile', False)),
                ('email', '=', value_shipping.get('email', False)),
                ('street', '=', value_shipping.get('street2', False)),
                ('state_id.code', '=', str(value_shipping.get('city', {}).get('id', False))),
                ('town_id.code', '=', str(value_shipping.get('town', {}).get('id', False))),
                ('district_id.code', '=', str(value_shipping.get('district', {}).get('id', False))),
            ], limit=1)
            if not partner_shipping:
                value_shipping.update({'parent_id': partner.id, 'type': 'delivery'})
                partner_shipping = partner.sudo().create(value_shipping)
            else:
                partner_shipping.sudo().write(value_shipping)

        return partner, partner_invoice, partner_shipping


class FsmApiSpecServiceIO(models.AbstractModel):
    _name = 'fsm.api.spec.service.io'
    _description = 'Field Service Management: API Specification Service IO'
    _order = 'sequence, id'
    _inverse_field = 'spec_id'

    @api.depends('sequence')
    def _compute_parent_id(self):
        for io in self:
            i = io
            while i.field_id:
                i = i.field_id
            io.parent_id = getattr(i, self._inverse_field).id

    example = fields.Char()
    required = fields.Boolean()
    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    description = fields.Char(translate=True)
    type = fields.Selection(PARAMTYPE, default='str')
    service_id = fields.Many2one('fsm.api.spec.service')
    field_id = fields.Many2one('fsm.api.spec.service.io', string='Field')
    field_ids = fields.One2many('fsm.api.spec.service.io', 'field_id', string='Fields')
    model_id = fields.Many2one('fsm.api.spec.service.model')
    model_type = fields.Selection([('dict', 'object'), ('list', 'array')])
    model_field_ids = fields.One2many(related='model_id.field_ids', string='Model Fields')
    spec_id = fields.Many2one('fsm.api.spec')
    parent_id = fields.Many2one('fsm.api.spec', compute='_compute_parent_id')

    @api.onchange('model_type')
    def onchange_model_type(self):
        if self.model_type:
            self.type = self.model_type

class FsmApiSpecServiceInput(models.Model):
    _name = 'fsm.api.spec.service.input'
    _inherit = 'fsm.api.spec.service.io'
    _description = 'Field Service Management: API Specification Service Inputs'

    field_id = fields.Many2one(comodel_name='fsm.api.spec.service.input')
    field_ids = fields.One2many(comodel_name='fsm.api.spec.service.input')

class FsmApiSpecServiceOutput(models.Model):
    _name = 'fsm.api.spec.service.output'
    _inherit = 'fsm.api.spec.service.io'
    _description = 'Field Service Management: API Specification Service Outputs'

    field_id = fields.Many2one(comodel_name='fsm.api.spec.service.output')
    field_ids = fields.One2many(comodel_name='fsm.api.spec.service.output')


class FsmApiSpecServiceModel(models.Model):
    _name = 'fsm.api.spec.service.model'
    _inherit = 'fsm.api.spec.service.io'
    _description = 'Field Service Management: API Specification Service Models'

    field_id = fields.Many2one(comodel_name='fsm.api.spec.service.model')
    field_ids = fields.One2many(comodel_name='fsm.api.spec.service.model')
