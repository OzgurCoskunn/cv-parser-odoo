# -*- coding: utf-8 -*-
import json
import time
import logging
from http.client import responses
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class DeliveryLog(models.Model):
    _name = 'delivery.log'
    _description = 'Delivery Logs'
    _order = 'id DESC'

    def _compute_state(self):
        for log in self:
            log.state = log.status and 'success' or 'error'

    def _compute_response_badge(self):
        for log in self:
            log.response_badge = log.response_code and str(log.response_code)[0] or False

    def _compute_request_curl(self):
        for log in self:
            if log.request_data:
                try:
                    url = '%s%s' % (log.get_base_url(), log.request_url)
                    data = log.request_data
                    method = log.request_method
                    headers = json.loads(log.request_headers)
                    headers = " -H ".join(['"{0}: {1}"'.format(k, v) for k, v in headers.items()])
                    command = "curl -X {method} -H {headers} -d '{data}' {url}"
                    log.request_curl = command.format(method=method, headers=headers, data=data, url=url) 
                except:
                    log.request_curl = False
            else:
                log.request_curl = False

    @api.depends('reference', 'environment', 'response_data', 'request_data')
    def _compute_data_formatted(self):
        for line in self:
            try:
                line.request_data_formatted = json.dumps(json.loads(line.request_data), default=str, indent=4, ensure_ascii=False)
                line.response_data_formatted = json.dumps(json.loads(line.response_data), default=str, indent=4, ensure_ascii=False)
            except:
                line.request_data_formatted = line.request_data
                line.response_data_formatted = line.response_data

    def _prepare_curl(self, url, method, headers, payload):
        command = "curl -X {method} -H {headers} -d '{data}' {url}"
        data = "{" + ", ".join(['"{0}":"{1}"'.format(k,v) for k,v in payload.items()]) + "}"
        headers = " -H ".join(['"{0}: {1}"'.format(k, v) for k, v in headers.items()])
        return command.format(method=method, headers=headers, data=data, url=url) 

    company_id = fields.Many2one('res.company', string='Company', readonly=True, copy=False, index=True, default=lambda self: self.env.company)
    picking_id = fields.Many2one('stock.picking', string='Delivery', readonly=True, copy=False, index=True)
    reference = fields.Char(string='Reference', readonly=True, copy=False)
    environment = fields.Selection([('T', 'Test'), ('P', 'Production')], string='Environment', readonly=True, copy=False)
    state = fields.Selection([('error', 'Error'), ('success', 'Success')], string='State', compute='_compute_state')
    status = fields.Boolean(string='Success', readonly=True, copy=False)
    message = fields.Text(string='Message', readonly=True, copy=False, default=lambda self: _('Request is invalid'))
    duration = fields.Float(string='Duration', digits=(16, 2), readonly=True, copy=False)
    request_method = fields.Selection([
        ('post', 'POST'),
        ('get', 'GET'),
        ('put', 'PUT'),
        ('delete', 'DELETE'),
        ('webhook', 'WEBHOOK'),
    ], string='Request Method', readonly=True, copy=False, default='post')
    request_url = fields.Text(string='Request Url', readonly=True, copy=False, default='/execute')
    request_curl = fields.Text(string='Request cURL', readonly=True, copy=False, compute='_compute_request_curl')
    request_headers = fields.Text(string='Request Headers', readonly=True, copy=False, default='{}')
    request_data = fields.Text(string='Request Data', readonly=True, copy=False, default='{}')
    request_data_formatted = fields.Text(string='Formatted Request Data', readonly=True, copy=False, default='{}', compute="_compute_data_formatted")
    response_code = fields.Integer(string='Response Code', readonly=True, copy=False, default=400)
    response_data = fields.Text(string='Response Data', readonly=True, copy=False, default='{}')
    response_message = fields.Char(string='Response Message', readonly=True, copy=False, default='Ok')
    response_data_formatted = fields.Text(string='Formatted Response Data', readonly=True, copy=False, default='{}', compute="_compute_data_formatted")
    response_badge = fields.Char(string='Response Badge', compute='_compute_response_badge')
    debug_ok = fields.Boolean(string='Show Debug', readonly=True, copy=False)
    debug_message = fields.Text(string='Debug Message', readonly=True, copy=False)

    def _compute_display_name(self):
        for log in self:
            log.display_name = 'Log #%s' % log.id

    def action_toggle_debug(self):
        self.sudo().write({'debug_ok': not self.debug_ok})

    def _log_sql_value(self, value):
        if isinstance(value, str):
            return "$$%s$$" % value
        elif isinstance(value, int):
            return "%s" % value
        else:
            return "NULL"

    def _log(self, log):
        code = log.get('code', 200)
        try:
            with self.env.cr.savepoint():
                now = time.time()
                values = {
                    'company_id': self.env.company.id,
                    'status': log.get('status', True),
                    'message': log.get('message', _('Request is successful')),
                    'duration': now - log.get('now', now),
                    'debug_message': log.get('debug', False),
                    'request_url': log.get('url', '{}'),
                    'request_method': log.get('method', '{}'),
                    'request_data': log.get('request', '{}'),
                    'request_headers': log.get('headers', '{}'),
                    'response_message': responses.get(int(code), ''),
                    'response_data': log.get('response', '{}'),
                    'reference': log.get('reference', False) or None,
                    'picking_id': log.get('picking_id', False) or None,
                    'response_code': code,
                    'environment': log.get('environment', 'P'),
                }

                if self.env.context.get('no_log'):
                    log.update(values)
                else:
                    keys = values.keys()
                    vals = values.values()
                    self.env.cr.execute('''
                        INSERT INTO delivery_log (%s, create_uid, write_uid, create_date, write_date)
                        VALUES (%s, 1, 1, NOW() at time zone 'UTC', NOW() at time zone 'UTC')
                        ''' % (', '.join(keys), ', '.join(map(self._log_sql_value, vals)))
                    )
        except:
            _logger.error('Log cannot be saved. Response code was %s and details as follows:\n%s' % (code, json.dumps(log, default=str, indent=4)))
