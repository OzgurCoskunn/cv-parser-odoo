# -*- coding: utf-8 -*-

from odoo import models, fields, api


class FsmTaskDeliverySelect(models.TransientModel):
    _name = 'fsm.task.delivery.select'
    _description = 'Field Service Management: Select Delivery Carrier'

    @api.depends('task_ids')
    def _compute_carrier_ids(self):
        for wizard in self:
            wizard.carrier_ids = self.env['delivery.carrier'].sudo().search([('delivery_type', 'not in', ('fixed', 'base_on_rule'))])

    task_ids = fields.Many2many('fsm.task', 'fsm_task_delivery_select_rel', 'wizard_id', 'task_id')
    carrier_id = fields.Many2one('delivery.carrier', domain='[("id", "=", carrier_ids)]', required=True)
    carrier_ids = fields.Many2many('delivery.carrier', compute='_compute_carrier_ids')
    button_id = fields.Many2one('fsm.flow.stage.button')
    button_action_id = fields.Many2one('fsm.button.action')

    def _confirm(self):
        if self.button_action_id:
            button = self.button_action_id.flow_stage_button_id
            defaults = {
                **self.env.context.get('defaults', {}),
                str(self.button_action_id.id): {
                    'carrier_id': self.carrier_id.id,
                }
            }
            action = button.with_context(defaults=defaults)._run_action(self.task_ids)
            if isinstance(action, dict) and 'action' in action:
                return action['action']

    def confirm(self):
        action = self._confirm()
        if action:
            return action

        return self.button_id.with_context(carrier_id=self.carrier_id.id)._run_action(self.task_ids)
