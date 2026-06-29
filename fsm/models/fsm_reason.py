# -*- coding: utf-8 -*-

from odoo import models, fields


class FsmReason(models.Model):
    _name = 'fsm.reason'
    _description = 'Field Service Management: Reasons'
    _order = 'sequence'

    sequence = fields.Integer(default=10)
    name = fields.Char('Description')
    code = fields.Char('Code')
    status = fields.Integer('HTTP Code')
    description = fields.Boolean('Allow Extra Description')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    project_ids = fields.Many2many('fsm.project', 'fsm_reason_project_rel', 'reason_id', 'project_id', string='Projects')
