# -*- coding: utf-8 -*-

from odoo import models, fields


class FsmPackage(models.Model):
    _name = 'fsm.package'
    _description = 'Field Service Management: Packages'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char()
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
