# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class FsmTaskUserAssign(models.TransientModel):
    _name = 'fsm.task.user.assign'
    _description = 'Field Service Management: Assign Technician to Task'

    @api.depends('task_ids')
    def _compute_user_ids(self):
        for wizard in self:
            if len(wizard.task_ids):
                try:
                    task = wizard.task_ids[0]._origin
                except:
                    task = wizard.task_ids[0]
                wizard.user_ids = [(6, 0, task.service_zone_id.team_ids.mapped('crm_team_member_ids.user_id').ids)]
            else:
                wizard.user_ids = False

    task_one = fields.Boolean()
    task_ids = fields.Many2many('fsm.task', 'fsm_task_user_assign_rel', 'wizard_id', 'task_id', required=True)
    line_ids = fields.One2many('fsm.task.user.assign.line', 'wizard_id', string='Lines')
    user_id = fields.Many2one('res.users', domain='[("id", "in", user_ids)]')
    user_ids = fields.Many2many('res.users', compute='_compute_user_ids')
    button_action_id = fields.Many2one('fsm.button.action')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        ids = self.env.context.get('active_ids')
        tasks = self.env['fsm.task'].browse(ids)
        zones = tasks.mapped('service_zone_id')
        teams = zones.mapped('team_ids')
        users = tasks.mapped('user_id')
        if (len(teams) <= 1 or len(zones) <= 1) and len(users) <= 1:
            res.update({
                'task_one': True,
                'user_id': users.id,
                'task_ids': [(6, 0, tasks.ids)],
            })
        else:
            res.update({
                'task_one': False,
                'line_ids': [(0, 0, {
                    'task_id': task.id,
                    'user_id': task.user_id.id,
                }) for task in tasks],
                'task_ids': [(6, 0, tasks.ids)],
            })
        return res

    def _confirm(self):
        if self.button_action_id:
            button = self.button_action_id.flow_stage_button_id
            defaults = {
                **self.env.context.get('defaults', {}),
                str(self.button_action_id.id): {
                    'user_id': self.user_id.id,
                }
            }
            action = button.with_context(defaults=defaults)._run_action(self.task_ids)
            if isinstance(action, dict) and 'action' in action:
                return action['action']
            return {'type': 'fsm.reload'}

    def confirm(self):
        action = self._confirm()
        if action:
            return action
 
        updated = False
        these = self if self.task_one else self.line_ids
        for this in these:
            user = this.user_id
            task = this.task_ids if self.task_one else this.task_id
            if not user and task.user_id:
                task.write({'user_id': False})
                for t in task:
                    t.message_post(body=_('<strong class="text-info">%s</strong> has been unassigned from this task.') % (user.name,))
                updated = True
            elif user.id != task.user_id.id:
                task.write({'user_id': user.id})
                for t in task:
                    t.message_post(body=_('<strong class="text-info">%s</strong> has been assigned to this task.') % (user.name,))
                updated = True

        if updated:
            return {'type': 'fsm.reload'}
            #return {'type': 'ir.actions.client', 'tag': 'reload'}
        return {'type': 'ir.actions.act_window_close'}

class FsmTaskUserAssignLine(models.TransientModel):
    _name = 'fsm.task.user.assign.line'
    _description = 'Field Service Management: Assign Technician to Task Lines'

    @api.depends('task_id')
    def _compute_user_ids(self):
        for wizard in self:
            wizard.user_ids = [(6, 0, wizard.task_id.service_zone_id.team_ids.mapped('crm_team_member_ids.user_id').ids)]

    wizard_id = fields.Many2one('fsm.task.user.assign', ondelete='cascade')
    task_id = fields.Many2one('fsm.task', required=True, readonly=True)
    service_zone_id = fields.Many2one(related='task_id.service_zone_id')
    user_id = fields.Many2one('res.users', domain='[("id", "in", user_ids)]')
    user_ids = fields.Many2many('res.users', compute='_compute_user_ids')