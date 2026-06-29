# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SlaPolicy(models.Model):
    _name = 'sla.policy'
    _description = 'Service Level Agreement: Policies'
    _order = 'sequence'

    @api.depends('stage_model_id', 'stage_model_name')
    def _compute_stage_model_show(self):
        for policy in self:
            policy.stage_model_show = policy.stage_model_id.model != policy.stage_model_name

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    worksheet_id = fields.Many2one('sla.worksheet')
    hour_total = fields.Float(string='Total Hour(s)')
    stage_model_id = fields.Many2one('ir.model', domain=[('model', 'like', '%.stage')])
    stage_model_name = fields.Char()
    stage_model_show = fields.Boolean(compute='_compute_stage_model_show')
    stage_model_apply = fields.Boolean(default=False, store=False)
    stage_reset = fields.Boolean(default=False, store=False)
    stage_ids = fields.One2many('sla.policy.stage', 'policy_id', string='Stages', copy=True)

    @api.onchange('stage_model_apply')
    def onchange_stage_model_apply(self):
        if self.stage_model_id:
            self.stage_model_name = self.stage_model_id.model
            stages = self.env[self.stage_model_id.model].sudo().search([])
            self.stage_ids = [(5, 0, 0)] + [(0, 0, {
                'name': stage.name,
                'stage_id': stage.id,
                'stage_model': stage._name,
                'stage_ref': '%s,%s' % (stage._name, stage.id),
            }) for stage in stages]
            if self.stage_ids:
                self.stage_ids[-1]['type'] = '2'
        else:
            self.stage_model_name = False
            if self.env.context.get('reset'):
                self.stage_ids = [(5, 0, 0)]
            else:
                for stage in self.stage_ids:
                    stage.update({
                        'stage_id': False,
                        'stage_ref': False,
                        'stage_model': False
                    })

    @api.onchange('stage_reset')
    def onchange_stage_reset(self):
        self.with_context(reset=True).onchange_stage_model_apply()


class SlaPolicyStage(models.Model):
    _name = 'sla.policy.stage'
    _description = 'Service Level Agreement: Policy Stages'
    _order = 'type, sequence'

    @api.model
    def _selection_stage_ref(self):
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([('model', 'like', '%.stage')])]

    policy_id = fields.Many2one('sla.policy', ondelete='cascade')
    stage_id = fields.Many2oneReference(model_field='stage_model')
    stage_ref = fields.Reference(selection='_selection_stage_ref')
    stage_model = fields.Char()
    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    type = fields.Selection([
        ('0', 'Regular'),
        ('1', 'Paused'),
        ('2', 'Closed'),
        ('3', 'Cancelled'),
    ], default='0', required=True)
    description = fields.Char()

    @api.onchange('stage_id')
    def onchange_stage_id(self):
        if self.stage_id:
            self.name = self.stage_id.name
