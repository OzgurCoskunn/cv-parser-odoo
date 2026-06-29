# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class FsmTaskServiceChange(models.TransientModel):
    _name = 'fsm.task.service.change'
    _description = 'Field Service Management: Change Task Service Type'

    task_ids = fields.Many2many('fsm.task', 'fsm_task_service_change_rel', 'wizard_id', 'task_id', required=True)
    type_id = fields.Many2one('fsm.service.type', string='Service Type', required=True)
    button_action_id = fields.Many2one('fsm.button.action')

    def _confirm(self):
        if self.button_action_id:
            button = self.button_action_id.flow_stage_button_id
            defaults = {
                **self.env.context.get('defaults', {}),
                str(self.button_action_id.id): {
                    'type_id': self.type_id.id,
                }
            }
            action = button.with_context(defaults=defaults)._run_action(self.task_ids)
            if isinstance(action, dict) and 'action' in action:
                return action['action']

    def confirm(self):
        action = self._confirm()
        if action:
            return action

        for task in self.task_ids:
            if task.stage_id.type in ('2', '3'):
                raise UserError(_('You cannot change service type for this task in which stage type is "Closed" or "Cancelled".'))
        for task in self.task_ids:
            task.with_context(no_reason=True).write({'service_type_id': self.type_id.id})
        return {'type': 'fsm.reload'}
