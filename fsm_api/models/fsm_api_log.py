# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, _


class FsmApiLog(models.Model):
    _name = 'fsm.api.log'
    _description = 'Field Service Management: API Logs'
    _order = 'id DESC'

    def _compute_state(self):
        for log in self:
            log.state = log.status and 'success' or 'error'

    def _compute_request_curl(self):
        for log in self:
            if log.request_data:
                try:
                    url = log.request_url
                    data = log.request_data
                    method = log.request_method or 'GET'
                    authorization = '%s:%s' % (log.auth_id.api_key, log.auth_id.secret_key)
                    authorization = base64.b64encode(authorization.encode('utf-8')).decode('ascii')
                    headers = {"Content-Type": "application/json", "Authorization": "Basic %s" % authorization}
                    headers = " -H ".join(['"{0}: {1}"'.format(k, v) for k, v in headers.items()])
                    command = "curl -X {method} -H {headers} -d '{data}' {url}"
                    log.request_curl = command.format(method=method, headers=headers, data=data, url=url) 
                except:
                    log.request_curl = False
            else:
                log.request_curl = False

    def _compute_response_badge(self):
        for log in self:
            log.response_badge = log.response_code and str(log.response_code)[0] or False

    def _prepare_curl(self, url, method, headers, payload):
        command = "curl -X {method} -H {headers} -d '{data}' {url}"
        data = "{" + ", ".join(['"{0}":"{1}"'.format(k,v) for k,v in payload.items()]) + "}"
        headers = " -H ".join(['"{0}: {1}"'.format(k, v) for k, v in headers.items()])
        return command.format(method=method, headers=headers, data=data, url=url) 

    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True, copy=False, index=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, copy=False, index=True, default=lambda self: self.env.company)
    task_id = fields.Many2one('fsm.task', string='Task', readonly=True, copy=False, index=True)
    auth_id = fields.Many2one('fsm.api.auth', string='Token', readonly=True, copy=False, index=True)
    service_id = fields.Many2one('fsm.api.spec.service', string='Service', readonly=True, copy=False, index=True)
    #reference = fields.Char(string='Reference', readonly=True, copy=False)
    #environment = fields.Selection([('T', 'Test'), ('P', 'Production')], string='Environment', readonly=True, copy=False)
    state = fields.Selection([('error', 'Error'), ('success', 'Success')], string='State', compute='_compute_state')
    status = fields.Boolean(string='Success', readonly=True, copy=False)
    duration = fields.Float(string='Duration', digits=(16, 2), readonly=True, copy=False)
    message = fields.Text(string='Message', readonly=True, copy=False, default=lambda self: _('Request is successful'))
    debug_ok = fields.Boolean(string='Show Debug')
    debug_message = fields.Text(string='Debug Message')
    request_method = fields.Selection(related='service_id.method', string='Request Method', readonly=False, store=True, copy=False, default='POST')
    request_curl = fields.Text(string='Request cURL', readonly=True, copy=False, compute='_compute_request_curl')
    request_url = fields.Text(string='Request URL', readonly=True, copy=False, default='/api')
    request_data = fields.Text(string='Request Data', readonly=True, copy=False, default='{}')
    request_raw = fields.Text(string='Raw Request Data', readonly=True, copy=False, default='{}')
    response_code = fields.Integer(string='Response Code', readonly=True, copy=False, default=200)
    response_message = fields.Char(string='Response Message', readonly=True, copy=False, default='Ok')
    response_data = fields.Text(string='Response Data', readonly=True, copy=False, default='{}')
    response_raw = fields.Text(string='Raw Response Data', readonly=True, copy=False, default='{}')
    response_badge = fields.Char(string='Response Badge', compute='_compute_response_badge')

    def _compute_display_name(self):
        for log in self:
            log.display_name = 'Log #%s' % log.id

    def action_toggle_debug(self):
        self.sudo().write({'debug_ok': not self.debug_ok})
