# -*- coding: utf-8 -*-

from odoo import models, fields


class SlaTicket(models.Model):
    _inherit = 'sla.ticket'

    fsm_task_id = fields.Many2one('fsm.task', string='FSM Task', readonly=True)
    fsm_project_id = fields.Many2one('fsm.project', string='FSM Project', related='fsm_task_id.project_id', store=True, readonly=True)
    fsm_project_item_id = fields.Many2one('fsm.project.item', string='FSM Project Follow-Up', related='fsm_task_id.project_item_id', store=True, readonly=True)

    def action_view_task(self):
        action = self.env.ref('fsm.action_task').sudo().read()[0]
        action['res_id'] = self.fsm_task_id.id
        action['views'] = [(False, 'form')]
        return action
