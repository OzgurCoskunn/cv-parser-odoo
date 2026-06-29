# -*- coding: utf-8 -*-
import json
from odoo import models, fields, _, api


class DeliveryLog(models.Model):
    _name = 'delivery.log'
    _description = 'Delivery Logs'
    _order = 'id DESC'

    
    def _compute_state(self):
        for log in self:
            log.state = log.status and 'success' or 'error'

    @api.depends('request_data', 'log', 'response_data')
    def _compute_data_formatted(self):
        for line in self:
            try:
                parsed_request_data = json.loads(line.request_data)
                line.request_raw = json.dumps(parsed_request_data, default=str, indent=4, ensure_ascii=False)
                parsed_response_data = json.loads(line.response_data)
                line.response_raw = json.dumps(parsed_response_data, default=str, indent=4, ensure_ascii=False)
            except Exception:
                line.request_raw = line.request_data
                line.response_raw = line.response_data

            line.log_traceback = line.log.replace("\\n", "\n") if line.log else ''


    company_id = fields.Many2one('res.company', string='Company', readonly=True, copy=False, index=True, default=lambda self: self.env.company)
    events = fields.Selection([
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('ACCEPT', 'Accept'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('DELIVER', 'Deliver'),
        ('FAILED_ATTEMPT', 'Failed Attempt'),
        ('RETURN_SERVICE', 'Return Service'),
        ('CANCEL', 'Cancel'),
        ('CANCUNDELIVEREL', 'Cancel Undeliverable'),
        ('COLLECTED', 'Collected'),
        ('TRANSFERRING_COLLECT', 'Transferring Collect'),
        ('TRANSFERRING_TRANSFER', 'Transferring Transfer'),
        ('WAITING_FOR_DISPATCH', 'Waiting for Dispatch'),
        ('DELIVERING', 'Delivering'),
        ('UNDELIVERED', 'Undelivered'),
        ('RETRY', 'Retry'),
        ('SIGNING', 'Signing'),
        ('SIGNED', 'Signed'),
        ('NOT_SIGNED', 'Not Signed'),
        ('DISPATCHING', 'Dispatching'),
        ('UNABLE_TO_COLLECT', 'Unable to Collect'),
        #elif status == 'RETURN_TO_SELLER':
        ('DELIVERED', 'Delivered'),
        ('Satıcıya iade edildi', 'Satıcıya iade edildi'),
    ], string='Event', readonly=True, copy=False, index=True, default='execute')
    reference = fields.Char(string='Reference', readonly=True, copy=False)
    state = fields.Selection([('error', 'Error'), ('success', 'Success')], string='State', compute='_compute_state')
    status = fields.Boolean(string='Success', readonly=True, copy=False)
    message = fields.Text(string='Message', readonly=True, copy=False, default=lambda self: _('Request is invalid'))
    request_data = fields.Text(string='Request Data', readonly=True, copy=False, default='{}')
    request_raw = fields.Text(string='Raw Request Data', readonly=True, copy=False, default='{}')
    response_data = fields.Text(string='Response Data', readonly=True, copy=False, default='{}')
    response_raw = fields.Text(string='Raw Response Data', readonly=True, copy=False, default='{}')
    log = fields.Text(string='Log', readonly=True)
    log_traceback = fields.Text(string='Log Traceback', compute='_compute_data_formatted')
    is_webhook = fields.Boolean(string='Webhook', readonly=True, copy=False, default=False)

    def _compute_display_name(self):
        for log in self:
            log.display_name = 'Log #%s' % log.id
    
    def _log(self, data={}, error='', reference='', event='', company=None, tb='', wb=False):
        try:
            json_data = json.dumps(data, ensure_ascii=False, default=str)
            request_data = json_data if not wb else '{}'
            response_data = json_data if wb else '{}'
            status = False if error else True

            self.env.cr.execute('''
                INSERT INTO delivery_log (
                    company_id,
                    reference,
                    message,
                    events,
                    request_data,
                    response_data,
                    log,
                    status,
                    create_uid,
                    write_uid,
                    create_date,
                    write_date
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, 1, NOW() at time zone 'UTC', NOW() at time zone 'UTC')
            ''', (
                company.id if company else self.env.company.id,
                reference,
                str(error),
                event,
                request_data,
                response_data,
                tb,
                status
            ))
        except Exception as e:
            self.env.cr.rollback()
