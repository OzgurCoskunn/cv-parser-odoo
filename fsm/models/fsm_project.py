# -*- coding: utf-8 -*-

import uuid
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class FsmProject(models.Model):
    _name = 'fsm.project'
    _description = 'Field Service Management: Projects'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    def _compute_task_count(self):
        for project in self:
            project.task_count = self.env['fsm.task'].sudo().search_count([('project_id', '=', project.id)])

    def _compute_item_count(self):
        for project in self:
            project.item_count = self.env['fsm.project.item'].sudo().search_count([('project_id', '=', project.id)])

    def _compute_flow_count(self):
        for project in self:
            project.flow_count = self.env['fsm.flow'].sudo().search_count([('project_id', '=', project.id)])

    name = fields.Char(required=True)
    code = fields.Char()
    uid = fields.Char(default=lambda self: str(uuid.uuid4()), readonly=True, copy=False)
    active = fields.Boolean(default=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, domain='[("is_company", "=", True), ("parent_id", "=", False)]')
    item_ids = fields.One2many('fsm.project.item', 'project_id', string='Project Follow-Ups')
    subpartner_ids = fields.One2many('fsm.project.subpartner', 'project_id', string='Subpartners')
    product_ids = fields.Many2many('product.product', 'fsm_project_product_rel', 'project_id', 'product_id', string='Products', required=True, domain='[("fsm_ok", "=", True)]')
    sla_ids = fields.Many2many('sla.agreement', 'fsm_project_sla_rel', 'project_id', 'sla_id', string='SLAs', domain='[("state", "=", "confirm"), ("stage_model_name", "=", "fsm.stage")]')
    team_ids = fields.Many2many('crm.team', 'fsm_project_team_rel', 'project_id', 'team_id', string='Teams')
    user_ids = fields.Many2many('res.users', 'fsm_project_user_rel', 'project_id', 'user_id', string='Users', domain='[("share", "=", False)]')
    spare_ids = fields.Many2many('product.product', 'fsm_project_spare_rel', 'project_id', 'spare_id', string='Spare Parts', required=True)
    type_ids = fields.One2many('fsm.project.type', 'project_id', string='Types')
    stage_ids = fields.Many2many('fsm.stage', 'fsm_project_stage_rel', 'project_id', 'stage_id', string='Stages', required=True)
    warehouse_ids = fields.Many2many('stock.warehouse', 'fsm_project_warehouse_rel', 'project_id', 'warehouse_id', string='Warehouses', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),
    ], default='draft', required=True, tracking=True)
    task_count = fields.Integer(compute='_compute_task_count')
    item_count = fields.Integer(compute='_compute_item_count')
    flow_count = fields.Integer(compute='_compute_flow_count')
    flow_ids = fields.One2many('fsm.flow', 'project_id', string='Flows')
    appointment_date_ok = fields.Boolean('Restrict Appointment Date')
    appointment_date_value = fields.Integer('Appointment Date Value')
    appointment_date_period = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years'),
    ], string='Appointment Date Period')
    sequence_id = fields.Many2one('ir.sequence', string='Sequence', required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    def action_confirm(self):
        self.write({'state': 'confirm'})

        if not self.flow_ids:
            flows = self.env['fsm.flow'].sudo().search([
                ('project_id', '=', False),
                ('type_id', 'in', self.type_ids.mapped('type_id').ids),
            ])

            for flow in flows:
                flow.copy().write({'project_id': self.id})

            tmpls = {flow.template_id.id: flow for flow in self.flow_ids.mapped('stage_ids') if flow.template_id}
            for flow in tmpls.values():
                stage_prev_ids = [tmpls[stage.template_id.id]['id'] for stage in flow.stage_prev_ids]
                stage_next_ids = [tmpls[stage.template_id.id]['id'] for stage in flow.stage_next_ids]
                flow.write({
                    'stage_prev_ids': [(6, 0, stage_prev_ids)],
                    'stage_next_ids': [(6, 0, stage_next_ids)],
                })

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_task(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fsm.task.create',
            'name': _('Create Task'),
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
                'create': False,
            }
        }

    def action_view_items(self):
        action = self.env.ref('fsm.action_project_item').sudo().read()[0]
        action['context'] = {
            'default_project_id': self.id,
            'default_partner_id': self.partner_id.id,
        }
        action['domain'] = [('project_id', '=', self.id)]
        return action

    def action_view_flows(self):
        action = self.env.ref('fsm.action_flow').sudo().read()[0]
        action['context'] = {'default_project_id': self.id}
        action['domain'] = [('project_id', '=', self.id)]
        return action

    def action_view_tasks(self):
        action = self.env.ref('fsm.action_task').sudo().read()[0]
        action['context'] = {'default_project_id': self.id}
        action['domain'] = [('project_id', '=', self.id)]
        return action

    def unlink(self):
        for project in self:
            if project.state != 'draft':
                raise UserError(_('Only "Draft" projects can be deleted'))
        return super().unlink()


class FsmProjectItem(models.Model):
    _name = 'fsm.project.item'
    _description = 'Field Service Management: Project Follow-Ups'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    def _compute_task_count(self):
        for item in self:
            item.task_count = self.env['fsm.task'].sudo().search_count([('project_item_id', '=', item.id)])

    name = fields.Char(required=True)
    uid = fields.Char(default=lambda self: str(uuid.uuid4()), readonly=True, copy=False)
    task_maximum = fields.Integer('Maximum Task Count')
    task_count = fields.Integer(compute='_compute_task_count')
    task_ids = fields.One2many('fsm.task', 'project_item_id', string='Tasks')
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    sla_id = fields.Many2one('sla.agreement', string='SLA', required=True, domain='[("state", "=", "confirm"), ("stage_model_name", "=", "fsm.stage"), ("partner_id", "=", partner_id)]')
    project_id = fields.Many2one('fsm.project', string='Project', ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', related='project_id.partner_id', store=True, index=True)
    company_id = fields.Many2one('res.company', related='project_id.company_id', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),
    ], default='draft', required=True, tracking=True)

    @api.constrains('task_maximum')
    def _check_task_maximum(self):
        for item in self:
            if item.task_maximum < 0:
                raise ValidationError(_('Maximum task count must be greater than zero.'))

    def action_confirm(self):
        self.write({'state': 'confirm'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_task(self):
        self.ensure_one()
        if self.task_maximum and self.task_maximum < self.task_count:
            raise UserError(_('Task count of this project follow-up cannot be higher than %s') % self.task_maximum)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fsm.task.create',
            'name': _('Create Task'),
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.project_id.id,
                'default_project_item_id': self.id,
                'create': False,
            }
        }

    def action_view_tasks(self):
        action = self.env.ref('fsm.action_task').sudo().read()[0]
        action['domain'] = [('project_item_id', '=', self.id)]
        action['context'] = {
            'default_project_id': self.project_id.id,
            'default_project_item_id': self.id,
        }
        return action

    def unlink(self):
        for item in self:
            if item.state != 'draft':
                raise UserError(_('Only "Draft" project follow-ups can be deleted'))
        return super().unlink()


class FsmProjectType(models.Model):
    _name = 'fsm.project.type'
    _description = 'Field Service Management: Project Types'
    _order = 'sequence'

    def _compute_name(self):
        for type in self:
            type.name = type.type_id.name

    name = fields.Char(compute='_compute_name')
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one('fsm.project', ondelete='cascade')
    type_id = fields.Many2one('fsm.type', string='Type', required=True)
    subtype_ids = fields.Many2many('fsm.type', 'fsm_project_type_subtype', 'type_id', 'subtype_id', string='Subtypes')


class FsmProjectSubpartner(models.Model):
    _name = 'fsm.project.subpartner'
    _description = 'Field Service Management: Project Subpartners'
    _order = 'sequence'

    def _compute_name(self):
        for subpartner in self:
            subpartner.name = subpartner.partner_id.name

    name = fields.Char(compute='_compute_name')
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one('fsm.project', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, domain='[("is_company", "=", True), ("parent_id", "=", False)]')
    location_ids = fields.Many2many('stock.location', 'fsm_project_subpartner_location', 'subpartner_id', 'location_id', string='Locations')
