# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class FsmStageChange(models.TransientModel):
    _name = 'fsm.stage.change'
    _description = 'Field Service Management: Change Stage'

    @api.depends('task_ids')
    def _compute_stage_ids(self):
        for wizard in self:
            wizard.stage_ids = wizard.task_ids[0].flow_id.stage_ids.ids

    task_ids = fields.Many2many('fsm.task', 'fsm_task_stage_change_rel', 'wizard_id', 'task_id', required=True)
    stage_id = fields.Many2one('fsm.flow.stage', required=True, domain='[("id", "in", stage_ids)]')
    stage_ids = fields.Many2many('fsm.flow.stage', compute='_compute_stage_ids')
    button_action_id = fields.Many2one('fsm.button.action')

    def _confirm(self):
        if self.button_action_id:
            button = self.button_action_id.flow_stage_button_id
            defaults = {
                **self.env.context.get('defaults', {}),
                str(self.button_action_id.id): {
                    'stage_id': self.stage_id.id,
                }
            }
            action = button.with_context(defaults=defaults)._run_action(self.task_ids)
            if isinstance(action, dict) and 'action' in action:
                return action['action']

    def confirm(self):
        action = self._confirm()
        if action:
            return action

        self.task_ids.write({'flow_stage_id': self.stage_id.id})
        return {'type': 'fsm.reload'}
