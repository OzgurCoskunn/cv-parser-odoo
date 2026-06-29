# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    fsm_task_id = fields.Many2one('fsm.task', string='FSM Task', readonly=True)
    fsm_project_id = fields.Many2one('fsm.project', string='FSM Project', related='fsm_task_id.project_id', store=True, readonly=True)
    fsm_project_item_id = fields.Many2one('fsm.project.item', string='FSM Project Follow-Ups', related='fsm_task_id.project_item_id', store=True, readonly=True)
    fsm_date_from = fields.Datetime('FSM Start Date')
    fsm_date_to = fields.Datetime('FSM End Date')
