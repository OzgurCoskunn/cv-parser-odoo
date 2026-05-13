# -*- coding: utf-8 -*-
from odoo import models, api


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def _action_done(self, feedback=False, attachment_ids=None):
        ids = {act.res_id: act.activity_type_id.id for act in self if act.res_model == 'fsm.task'}
        res = super(MailActivity, self)._action_done(feedback=feedback, attachment_ids=attachment_ids)
        for task_id, activity_id in ids.items():
            self.env['fsm.auto'].run_activities(task_id, activity_id, 'done')
        return res

    def write(self, values):
        ids = {act.res_id: act.activity_type_id.id for act in self if act.res_model == 'fsm.task' and act.state == 'overdue'}
        res = super(MailActivity, self).write(values)
        for task_id, activity_id in ids.items():
            self.env['fsm.auto'].run_activities(task_id, activity_id, 'expire')
        return res

    def unlink(self):
        ids = {act.res_id: act.activity_type_id.id for act in self if act.res_model == 'fsm.task'}
        res = super(MailActivity, self).unlink()
        for task_id, activity_id in ids.items():
            self.env['fsm.auto'].run_activities(task_id, activity_id, 'cancel')
        return res

    @api.onchange('res_id')
    def onchange_res_id(self):
        if self.res_model == 'fsm.task':
            task = self.env['fsm.task'].browse(self.res_id)
            if task.flow_stage_id:
                ids = task.flow_stage_id.activity_ids.ids
                self.activity_type_id = ids and ids[0] or False
                return {'domain': {'activity_type_id': [('id', 'in', ids)]}}
