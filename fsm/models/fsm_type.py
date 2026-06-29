# -*- coding: utf-8 -*-

from odoo import models, fields


class FsmType(models.Model):
    _name = 'fsm.type'
    _description = 'Field Service Management: Types'
    _order = 'sequence'

    name = fields.Char(required=True)
    code = fields.Char()
    description = fields.Char()
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
