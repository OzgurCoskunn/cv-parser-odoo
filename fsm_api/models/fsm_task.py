# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, SUPERUSER_ID
from odoo.modules.registry import Registry

_logger = logging.getLogger(__name__)


class FsmTask(models.Model):
    _inherit = 'fsm.task'

    def _compute_api_log(self):
        for task in self:
            task.api_log_count = len(task.api_log_ids)
            task.api_log_done = len(task.api_log_ids.filtered(lambda l: int(l.response_code / 100) == 2))

    api_log_ids = fields.One2many('fsm.api.log', 'task_id', string='API Logs')
    api_log_done = fields.Integer(compute='_compute_api_log')
    api_log_count = fields.Integer(compute='_compute_api_log')

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)

        try:
            with self.env.cr.savepoint():
                tasks.sudo().create_api_log()
        except Exception as e:
            _logger.error('An error occured when creating API log: %s' % e)

        dbname = self.env.cr.dbname
        context = self.env.context
        @self.env.cr.postcommit.add
        def webhook():
            db_registry = Registry(dbname)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, context)
                env['fsm.api.webhook'].create([{'task_id': task.id} for task in tasks])

        return tasks

    def _write(self, vals):
        res = super()._write(vals)
        if 'stage_id' in vals or 'reason_id' in vals:
            dbname = self.env.cr.dbname
            context = self.env.context
            @self.env.cr.postcommit.add
            def webhook():
                db_registry = Registry(dbname)
                with db_registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, context)
                    try:
                        env['fsm.api.webhook'].create([{'task_id': task.id} for task in self])
                    except:
                        pass
        return res

    def create_api_log(self):
        pass

    def action_view_api_log(self):
        action = self.env.ref('fsm_api.action_api_log').sudo().read()[0]
        action['domain'] = [('id', 'in', self.api_log_ids.ids)]
        return action
