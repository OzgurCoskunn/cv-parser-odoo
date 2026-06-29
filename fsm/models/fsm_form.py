# -*- coding: utf-8 -*-

from odoo import models, fields


class FsmForm(models.Model):
    _name = 'fsm.form'
    _description = 'Field Service Management: Forms'
    _order = 'sequence, id desc'

    name = fields.Char(required=True)
    code = fields.Char()
    version = fields.Char()
    body = fields.Html(sanitize=False)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def render(self, task):
        return self.env['mail.render.mixin']._render_template(self.body, task._name, task.ids, engine='qweb')[task.id]
