# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class FsmStageReason(models.TransientModel):
    _name = 'fsm.stage.reason'
    _description = 'Field Service Management: Stage Reason'

    @api.depends('task_ids')
    def _compute_reason_ids(self):
        for wizard in self:
            reason_ids = self.env.context.get('reason_ids', [])
            if not reason_ids:
                reason_ids = wizard.task_ids.mapped('flow_stage_id.reason_ids').ids
            wizard.reason_ids = [(6, 0, reason_ids)]

    @api.depends('task_ids')
    def _compute_contact_ids(self):
        for wizard in self:
            if wizard.task_one and wizard.stage_type == '2':
                wizard.contact_ids = [(6, 0, wizard.task_ids.merchant_id.child_ids.filtered(lambda c: c.type == 'contact').ids)]
            else:
                wizard.contact_ids = False

    @api.depends('stage_success', 'reason_id', 'reason_desc')
    def _compute_reason_fields(self):
        for wizard in self:
            field_reason_id = 0
            field_reason_desc = 0
            if wizard.stage_id.stage_id.type == '2':
                if wizard.reason_id:
                    field_reason_id = 2
                    if wizard.reason_id.description:
                        field_reason_desc = 1
                else:
                    field_reason_id = 1
                    field_reason_desc = 2
            else:
                field_reason_id = 2
                if wizard.reason_id.description:
                    field_reason_desc = 1

            wizard.field_reason_id = field_reason_id
            wizard.field_reason_desc = field_reason_desc

    task_ids = fields.Many2many('fsm.task', 'fsm_task_stage_reason_rel', 'wizard_id', 'task_id', required=True)
    task_one = fields.Boolean()
    stage_success = fields.Boolean(default=True)
    stage_success_readonly = fields.Boolean(default=False)
    stage_id = fields.Many2one('fsm.flow.stage')
    stage_type = fields.Selection(related='stage_id.stage_id.type')
    reason_id = fields.Many2one('fsm.reason', domain='[("id", "in", reason_ids)]')
    reason_ids = fields.Many2many('fsm.reason', compute='_compute_reason_ids')
    reason_desc_ok = fields.Boolean(related='reason_id.description')
    reason_desc = fields.Text(string='Description')
    merchant_id = fields.Many2one('res.partner', related='task_ids.merchant_id')
    contact_id = fields.Many2one('res.partner', domain='[("id", "in", contact_ids)]')
    contact_ids = fields.Many2many('res.partner', compute='_compute_contact_ids')
    field_reason_id = fields.Integer(compute='_compute_reason_fields')
    field_reason_desc = fields.Integer(compute='_compute_reason_fields')
    button_action_id = fields.Many2one('fsm.button.action')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        ids = self.env.context.get('active_ids', [])
        res.update({'task_one': len(ids) == 1})
        return res

    def _confirm(self):
        if self.button_action_id:
            button = self.button_action_id.flow_stage_button_id
            defaults = {
                **self.env.context.get('defaults', {}),
                str(self.button_action_id.id): {
                    'stage_id': self.stage_id.id,
                    'reason_id': self.reason_id.id,
                    'reason_desc': self.reason_desc,
                    'stage_success': self.stage_success,
                }
            }
            action = button.with_context(defaults=defaults)._run_action(self.task_ids)
            if isinstance(action, dict) and 'action' in action:
                return action['action']

    def confirm(self):
        action = self._confirm()
        if action:
            return action
 
        values = self.env.context.get('values', {})
        if self.stage_type == '2':
            if self.reason_id:
                if self.reason_desc_ok and self.reason_desc:
                    reason = '<strong class="text-info">%s</strong> <em>(%s)</em>' % (self.reason_id.name, self.reason_desc)
                else:
                    reason = '<strong class="text-info">%s</strong>' % self.reason_id.name
            else:
                if self.reason_desc:
                    reason = '<em>%s</em>' % self.reason_desc
                else:
                    reason = '<em>%s</em>' % _('No reason specified')
            values.update({
                'close_done': True,
                'close_date': fields.Datetime.now(),
                'close_success': self.stage_success,
                'close_contact_id': self.contact_id.id,
                'reason_id': self.reason_id.id,
                'reason_desc': self.reason_desc_ok and self.reason_desc if self.reason_id else self.reason_desc,
            })
            if self.stage_success:
                for task in self.task_ids:
                    task.message_post(body=_('Task has been successfully closed.'))
            else:
                for task in self.task_ids:
                    task.message_post(body=_('Task has been unsuccessfully closed: %s') % (reason,))
            self.task_ids.with_context(no_reason=True).sudo().write(values)
        else:
            values.update({
                'reason_id': self.reason_id.id,
                'reason_desc': self.reason_desc_ok and self.reason_desc if self.reason_id else self.reason_desc,
            })
            self.task_ids.with_context(no_reason=True).sudo().write(values)
            stage_new = self.stage_id.display_name
            for task in self.task_ids:
                stage_old = task.flow_stage_id.display_name
                task.message_post(body=_('Stage has been changed from <em>%s</em> to <em>%s</em>: <strong class="text-info">%s</strong>') % (stage_old, stage_new, self.reason_id.name))

        return {'type': 'fsm.reload'}
        #return {'type': 'ir.actions.client', 'tag': 'reload'}
