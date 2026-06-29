# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class FsmReasonChange(models.TransientModel):
    _name = 'fsm.reason.change'
    _description = 'Field Service Management: Change Reason'

    @api.depends('task_ids')
    def _compute_reason_ids(self):
        for wizard in self:
            wizard.reason_ids = wizard.task_ids.mapped('flow_stage_id.reason_ids').ids

    @api.depends('reason_id')
    def _compute_reason_desc(self):
        for wizard in self:
            wizard.reason_desc_ok = wizard.reason_id.description

    task_ids = fields.Many2many('fsm.task', 'fsm_task_reason_change_rel', 'wizard_id', 'task_id', required=True)
    reason_id = fields.Many2one('fsm.reason', required=True, domain='[("id", "in", reason_ids)]')
    reason_desc = fields.Text(string='Description')
    reason_desc_ok = fields.Boolean(compute='_compute_reason_desc')
    reason_ids = fields.Many2many('fsm.reason', compute='_compute_reason_ids')
    button_action_id = fields.Many2one('fsm.button.action')

    def _confirm(self):
        if self.button_action_id:
            button = self.button_action_id.flow_stage_button_id
            defaults = {
                **self.env.context.get('defaults', {}),
                str(self.button_action_id.id): {
                    'reason_id': self.reason_id.id,
                    'reason_desc': self.reason_desc,
                }
            }
            action = button.with_context(defaults=defaults)._run_action(self.task_ids)
            if isinstance(action, dict) and 'action' in action:
                return action['action']

    def confirm(self):
        action = self._confirm()
        if action:
            return action

        self.task_ids.write({'reason_id': self.reason_id.id, 'reason_desc': self.reason_desc})
        for task in self.task_ids:
            task.message_post(body=_('Stage reason has been updated: <strong class="text-info">%s <em>%s</em></strong>') % (self.reason_id.name, self.reason_id.code))
        return {'type': 'fsm.reload'}
