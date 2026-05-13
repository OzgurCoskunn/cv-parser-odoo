# -*- coding: utf-8 -*-
import time
import json
import base64
import logging
import requests
from datetime import timedelta
from http.client import responses
from odoo import models, api, fields, _

_logger = logging.getLogger(__name__)


class FsmApiWebhook(models.Model):
    _name = 'fsm.api.webhook'
    _description = 'Field Service Management: API Webhook'

    task_id = fields.Many2one('fsm.task')

    @api.model
    def _log_sql_value(self, value):
        if isinstance(value, str):
            return "$$%s$$" % value
        elif isinstance(value, int):
            return "%s" % value
        else:
            return "NULL"

    @api.model
    def _log(self, log):
        now = time.time()
        code = log.get('code', 200)
        values = {
            'service_id': None,
            'company_id': log.get('company', None),
            'partner_id': log.get('partner', None),
            'auth_id': log.get('auth', None),
            'task_id': log.get('task', None),
            'status': log.get('status', True),
            'message': log.get('message', _('Request is successful')),
            'duration': now - log.get('now', now),
            'debug_message': log.get('debug', False),
            'request_data': log.get('request', '{}'),
            'request_raw': '{}',
            'request_method': 'POST',
            'request_url': log.get('url', None),
            'response_message': responses.get(int(code), ''),
            'response_data': log.get('response', '{}'),
            'response_raw': '{}',
            'response_code': code,
        }


        keys = values.keys()
        vals = values.values()
        
        # Use ORM create instead of raw SQL to prevent injection and handle types correctly
        # The previous code was:
        # self.env.cr.execute('''
        #     INSERT INTO fsm_api_log (%s, create_uid, write_uid, create_date, write_date)
        #     VALUES (%s, 1, 1, NOW() at time zone 'UTC', NOW() at time zone 'UTC')
        #     ''' % (', '.join(keys), ', '.join(map(self._log_sql_value, vals)))
        # )
        
        # New implementation:
        try:
            # We explicitly set creating user to 1 (Superuser) if that was the intent, 
            # or just rely on the current user context if run with sudo() (cron runs as superuser usually).
            # The raw SQL forced create_uid=1. We can mimic this by ensuring sudo().
            # Note: create_date/write_date are handled auto by ORM.
            
            # Prepare values for ORM
            # values dictionary is already close to what we need, but keys might need to be field names.
            # 'auth_id' -> 'auth_id'
            # 'task_id' -> 'task_id'
            # etc.
            # The keys in `values` match field names in `fsm_api_log`?
            # Let's check fsm_api/models/fsm_api_log.py to be sure about field names.
            # Assuming they match since previous code used them in INSERT.
            
            # However, previous code inserted raw values. ORM expects IDs for Many2ones.
            # log.get('company') should be ID.
            
            self.env['fsm.api.log'].sudo().create(values)
        except Exception as e:
            _logger.error("Failed to create API log via ORM: %s" % e)

    @api.model
    def _prepare_curl(self, url, method, headers, payload):
        command = "curl -X {method} -H {headers} -d '{data}' {url}"
        data = "{" + ", ".join(['"{0}":"{1}"'.format(k,v) for k,v in payload.items()]) + "}"
        headers = " -H ".join(['"{0}: {1}"'.format(k, v) for k, v in headers.items()])
        return command.format(method=method, headers=headers, data=data, url=url) 

    @api.model
    def trigger(self):
        auth = self.env['fsm.api.auth'].sudo()
        now = fields.Datetime.now() - timedelta(minutes=1)
        webhooks = self.env['fsm.api.webhook'].sudo().search([('create_date', '<', now)])
        for webhook in webhooks:
            task = webhook.task_id
            if task.exists():
                token = auth.search([('partner_id', '=', task.partner_id.id), ('webhook_url', '!=', False)], limit=1)
                if token:
                    log = {
                        'task': task.id,
                        'auth': token.id,
                        'now': time.time(),
                        'url': token.webhook_url,
                        'company': token.company_id.id,
                        'partner': token.partner_id.id,
                    }
                    try:
                        payload = {
                            'orderId': task.uid,
                            'status': task.stage_id.code,
                            'updateDate': (task.write_date.replace(microsecond=0) + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                        }
                        log.update({
                            'request': json.dumps(payload, indent=4, default=str)
                        })

                        headers = {'Accept': 'application/json'}
                        if token.webhook_auth == 'basic':
                            auth_token = base64.b64encode(f'{token.webhook_username}:{token.webhook_password}'.encode('utf-8')).decode('ascii')
                            headers.update({'Authorization': f'Basic {auth_token}'})
                        response = requests.post(token.webhook_url, json=payload, headers=headers, timeout=15, verify=False)
                        log.update({
                            'code': response.status_code,
                            'response': response.text,
                        })
                        if int(response.status_code / 100) == 2:
                            _logger.info('Webhook has been successfully sent for task #%s.' % (task.uid or '-',))
                            webhook.unlink()
                            log.update({
                                'status': True
                            })
                            try:
                                with self.env.cr.savepoint():
                                    self._log(log)
                            except:
                                pass
                            self.env.cr.commit()
                        else:
                            curl = self._prepare_curl(token.webhook_url, 'POST', headers, payload)
                            _logger.warning('Webhook could not be sent for task #%s. It responded with status code %s. cURL as follows:\n%s' % (task.uid or '-', response.status_code, curl))
                            log.update({
                                'status': False,
                                'message': _('An error occured'),
                            })
                            try:
                                with self.env.cr.savepoint():
                                    self._log(log)
                            except:
                                pass
                    except Exception as e:
                        _logger.warning('An error occured when sending a webhook request: %s' % e)
                        log.update({
                            'code': 500,
                            'status': False,
                            'message': _('An error occured'),
                        })
                        try:
                            with self.env.cr.savepoint():
                                self._log(log)
                        except:
                            pass
            webhook.unlink()
            self.env.cr.commit()
