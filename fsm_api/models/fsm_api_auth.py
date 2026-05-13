# -*- coding: utf-8 -*-
import uuid
import secrets
from odoo import models, fields, api


class FsmApiAuth(models.Model):
    _name = 'fsm.api.auth'
    _description = 'Field Service Management: API Authorization'
    _order = 'sequence, id desc'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    api_key = fields.Char(string='API Key', readonly=True, copy=False)
    secret_key = fields.Char(string='Secret Key', readonly=True, copy=False)
    project_id = fields.Many2one('fsm.project', string='Project')
    webhook_url = fields.Char(string='Webhook URL', readonly=False, copy=False)
    webhook_auth = fields.Selection([
        ('basic', 'Basic Auth'),
        ('bearer', 'Bearer Token'),
        ('oauth2', 'OAuth 2.0'),
    ], string='Webhook Authorization')
    webhook_username = fields.Char('Webhook Authorization Username')
    webhook_password = fields.Char('Webhook Authorization Password')
    partner_id = fields.Many2one('res.partner', required=True, copy=False)
    customer_id = fields.Many2one('res.partner', copy=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.update({
                'api_key': str(uuid.uuid4()),
                'secret_key': secrets.token_hex(16),
            })
        return super().create(vals_list)

    @api.model
    def onchange_partner(self):
        self.project_id = False
