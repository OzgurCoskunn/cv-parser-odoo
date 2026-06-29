# -*- coding: utf-8 -*-

from odoo import models, fields


class FsmStage(models.Model):
    _name = 'fsm.stage'
    _description = 'Field Service Management: Stages'
    _order = 'type, sequence'

    name = fields.Char(required=True)
    code = fields.Char()
    sequence = fields.Integer(default=10)
    description = fields.Char()
    type = fields.Selection([
        ('0', 'Regular'),
        ('1', 'Paused'),
        ('2', 'Closed'),
        ('3', 'Cancelled'),
    ], default='0', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
