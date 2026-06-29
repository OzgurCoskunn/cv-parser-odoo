# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, Command, _


class FsmFlow(models.Model):
    _name = 'fsm.flow'
    _description = 'Field Service Management: Flows'
    _order = 'type_code, service_type_code, sequence'

    def _compute_name(self):
        for flow in self:
            flow.name = _('Flow #%s') % flow.id if flow.id else _('New')

    name = fields.Char(compute='_compute_name')
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    type_id = fields.Many2one('fsm.type', string='Type', ondelete='restrict', required=True, index=True)
    type_code = fields.Char(related='type_id.code', store=True)
    service_type_id = fields.Many2one('fsm.service.type', string='Service Type', ondelete='restrict', required=True, index=True)
    service_type_code = fields.Char(related='service_type_id.code', store=True)
    project_id = fields.Many2one('fsm.project', string='Project', ondelete='cascade', index=True)
    stage_ids = fields.One2many('fsm.flow.stage', 'flow_id', string='Stages', copy=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    misc_use_material_product = fields.Boolean('Use Material Product')


class FsmFlowStage(models.Model):
    _name = 'fsm.flow.stage'
    _description = 'Field Service Management: Flow Stages'
    _rec_names_search = ['complete_name']
    _order = 'sequence'

    @api.depends('field_ids.field_id')
    def _compute_field_all(self):
        for stage in self:
            stage.field_all = stage.field_ids.mapped('field_id').ids

    @api.depends('button_ids.button_id')
    def _compute_button_all(self):
        for stage in self:
            stage.button_all = stage.button_ids.mapped('button_id').ids

    @api.depends('auto_ids.auto_id')
    def _compute_auto_all(self):
        for stage in self:
            stage.auto_all = stage.auto_ids.mapped('auto_id').ids

    @api.depends('todo_ids.todo_id')
    def _compute_todo_all(self):
        for stage in self:
            stage.todo_all = stage.todo_ids.mapped('todo_id').ids

    #@api.depends('reason_ids.reason_id')
    #def _compute_reason_all(self):
    #    for stage in self:
    #        stage.reason_all = stage.reason_ids.mapped('reason_id').ids

    @api.depends('name')
    def _compute_complete_name(self):
        for stage in self:
            stage.complete_name = stage.display_name

    def _domain_field_all(self):
        names = []
        field_ids = self.env['fsm.task']._fields
        for name, field in field_ids.items():
            if name.startswith('field_'):
                names.append(re.sub(r'^field_', '', name))
        return [('model', '=', 'fsm.task'), ('name', 'in', names)]

    sequence = fields.Integer(default=10)
    name = fields.Char(related='stage_id.name', store=True)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)
    template_id = fields.Many2one('fsm.flow.stage', copy=True)
    flow_id = fields.Many2one('fsm.flow', string='Flow', ondelete='cascade', required=True)
    type_id = fields.Many2one('fsm.type', related='flow_id.type_id', store=True, readonly=True, index=True)
    project_id = fields.Many2one('fsm.project', related='flow_id.project_id', store=True, readonly=True, index=True)
    stage_id = fields.Many2one('fsm.stage', string='Stage', ondelete='restrict')
    stage_type = fields.Selection(related='stage_id.type')
    stage_prev_ids = fields.Many2many('fsm.flow.stage', 'fsm_flow_stage_rel', 'next_id', 'prev_id', string='Previous Stages', domain='[("id", "!=", id), ("flow_id", "=", flow_id)]', copy=True)
    stage_next_ids = fields.Many2many('fsm.flow.stage', 'fsm_flow_stage_rel', 'prev_id', 'next_id', string='Next Stages', domain='[("id", "!=", id), ("flow_id", "=", flow_id)]', copy=True)
    field_ids = fields.One2many('fsm.flow.stage.field', 'stage_id', string='Fields', context={'without_model': True}, copy=True)
    field_all = fields.Many2many('ir.model.fields', string='All Fields', domain=_domain_field_all, context={'without_model': True}, compute='_compute_field_all', readonly=False)
    todo_ids = fields.One2many('fsm.flow.stage.todo', 'stage_id', string='Todos', copy=True)
    todo_all = fields.Many2many('fsm.todo', compute='_compute_todo_all', readonly=False)
    reason_ids = fields.Many2many('fsm.reason', 'fsm_flow_stage_reason_rel', 'stage_id', 'reason_id', string='Reasons', copy=True)
    reason_ok = fields.Boolean('Reason Required')
    #reason_ids = fields.One2many('fsm.flow.stage.reason', 'stage_id', string='Reasons', copy=True)
    #reason_all = fields.Many2many('fsm.reason', compute='_compute_reason_all', readonly=False)
    button_ids = fields.One2many('fsm.flow.stage.button', 'stage_id', string='Buttons', copy=True)
    button_all = fields.Many2many('fsm.button', compute='_compute_button_all', readonly=False)
    auto_ids = fields.One2many('fsm.flow.stage.auto', 'stage_id', string='Automations', copy=True)
    auto_all = fields.Many2many('fsm.auto', compute='_compute_auto_all', readonly=False)
    user_ids = fields.One2many('fsm.flow.stage.user', 'stage_id', string='Users', copy=True)
    team_ids = fields.One2many('fsm.flow.stage.team', 'stage_id', string='Teams', copy=True)
    activity_ids = fields.Many2many('mail.activity.type', 'fsm_flow_stage_activity_rel', 'stage_id', 'activity_id', string='Activities', copy=True)
    domain_stage = fields.Many2many(related='flow_id.project_id.stage_ids')
    misc_show_appointment_form = fields.Boolean('Show Appointment Form')
    misc_prev_todo_required = fields.Boolean('Previous Todos Required')

    @api.model
    def _prepare_fields_to_copy(self, record):
        default = dict([])
        blacklist = set(models.MAGIC_COLUMNS)
        whitelist = set(name for name, field in record._fields.items() if not field.inherited)

        def blacklist_fields(record):
            for parent_model, parent_field in record._inherits.items():
                blacklist.add(parent_field)
                if parent_field in default:
                    blacklist.update(set(self.env[parent_model]._fields) - whitelist)
                else:
                    blacklist_fields(self.env[parent_model])

        blacklist_fields(record)
        fields_to_copy = {
            name: field
            for name, field in record._fields.items()
            if field.copy and name not in default and name not in blacklist
        }

        for name, field in fields_to_copy.items():
            if field.type == 'one2many':
                lines = [self._prepare_fields_to_copy(rec) for rec in record[name]]
                default[name] = [Command.create(line) for line in lines if line]
            elif field.type == 'many2many':
                default[name] = [Command.set(record[name].ids)]
            else:
                default[name] = field.convert_to_write(record[name], record)
        return [default][0] if default else {}

    def onchange(self, values, field_name, field_onchange):
        return super(FsmFlowStage, self.with_context(recursive_onchanges=False)).onchange(values, field_name, field_onchange)

    @api.onchange('field_all')
    def onchange_field_all(self):
        field_ids = set(self.field_ids.mapped('field_id').ids)
        for field in self.field_all:
            if field._origin.id not in field_ids:
                self.field_ids += self.field_ids.new({
                    'field_id': field._origin.id,
                    'group_ids': [(0, 0, {
                        'group_id': self.env.ref('fsm.group_user').id,
                        'perm_read': True,
                        'perm_open': False,
                        'perm_update': False,
                    }), (0, 0, {
                        'group_id': self.env.ref('fsm.group_officer').id,
                        'perm_read': True,
                        'perm_open': False,
                        'perm_update': False,
                    }), (0, 0, {
                        'group_id': self.env.ref('fsm.group_administrator').id,
                        'perm_read': True,
                        'perm_open': True,
                        'perm_update': True,
                    })]
                })
            else:
                field_ids.remove(field._origin.id)
        for field in self.field_ids:
            if field.field_id.id in field_ids:
                self.field_ids -= field

    @api.onchange('auto_all')
    def onchange_auto_all(self):
        autos = set(self.auto_ids.mapped('auto_id').ids)
        for auto in self.auto_all:
            if auto._origin.id not in autos:
                values = self._prepare_fields_to_copy(auto)
                self.auto_ids += self.auto_ids.new(values)

    @api.onchange('button_all')
    def onchange_button_all(self):
        buttons = set(self.button_ids.mapped('button_id').ids)
        for button in self.button_all:
            if button._origin.id not in buttons:
                values = self._prepare_fields_to_copy(button)
                self.button_ids += self.button_ids.new(values)

    @api.onchange('todo_all')
    def onchange_todo_all(self):
        todos = set(self.todo_ids.mapped('todo_id').ids)
        for todo in self.todo_all:
            if todo._origin.id not in todos:
                values = self._prepare_fields_to_copy(todo)
                self.todo_ids += self.todo_ids.new(values)

    #@api.onchange('reason_all')
    #def onchange_reason_all(self):
    #    reasons = set(self.reason_ids.mapped('reason_id').ids)
    #    for reason in self.reason_all:
    #        if reason._origin.id not in reasons:
    #            values = self._prepare_fields_to_copy(reason)
    #            self.reason_ids += self.reason_ids.new(values)

    def _compute_display_name(self):
        for stage in self:
            stage.display_name = '%s #%s' % (stage.name, stage.id or '-')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        field_names = ['partner_id', 'merchant_id', 'product_id', 'product_lot_id', 'product_lot_ref', 'service_type_id']
        field_ids = self.env['ir.model.fields'].sudo().search([('model', '=', 'fsm.task'), ('name', 'in', field_names)])
        res.update({'field_ids': [(0, 0, {'field_id': field.id}) for field in field_ids]})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        stages = super().create(vals_list)
        for stage in stages:
            if not stage.template_id:
                stage.template_id = stage.id
        return stages


class FsmFlowStageField(models.Model):
    _name = 'fsm.flow.stage.field'
    _description = 'Field Service Management: Flow Stage Fields'
    _order = 'name'

    name = fields.Char(related='field_id.field_description', store=True)
    stage_id = fields.Many2one('fsm.flow.stage', ondelete='cascade')
    field_id = fields.Many2one('ir.model.fields', string='Field', domain=[('model', '=', 'fsm.task')], required=True, ondelete='cascade')
    group_ids = fields.One2many('fsm.flow.stage.field.group', 'field_id', string='Groups')


class FsmFlowStageFieldGroup(models.Model):
    _name = 'fsm.flow.stage.field.group'
    _description = 'Field Service Management: Flow Stage Field Groups'

    @api.depends('group_id', 'perm_read', 'perm_open', 'perm_update')
    def _compute_name(self):
        for group in self:
            if group.perm_read:
                perm_read = '✓ %s' % _('Can Read')
            else:
                perm_read = '× %s' % _('Cannot Read')
            if group.perm_open:
                perm_open = '✓ %s' % _('Can Open')
            else:
                perm_open = '× %s' % _('Cannot Open')
            if group.perm_update:
                perm_update = '✓ %s' % _('Can Update')
            else:
                perm_update = '× %s' % _('Cannot Update')
            group.name = '%s \n %s %s %s' % (group.group_id.display_name, perm_read, perm_open, perm_update)

    name = fields.Char(compute='_compute_name')
    field_id = fields.Many2one('fsm.flow.stage.field', ondelete='cascade')
    group_id = fields.Many2one('res.groups', string='Group', required=True, default=lambda self: self.env.ref('fsm.group_user').id)
    perm_read = fields.Boolean(string='Read Permission', default=True)
    perm_open = fields.Boolean(string='Open Permission', default=True)
    perm_update = fields.Boolean(string='Update Permission', default=True)


class FsmFlowStageButton(models.Model):
    _name = 'fsm.flow.stage.button'
    _inherit = 'fsm.button'
    _description = 'Field Service Management: Flow Stage Buttons'
    _order = 'sequence'

    button_id = fields.Many2one('fsm.button', string='Button')
    stage_id = fields.Many2one('fsm.flow.stage', ondelete='cascade')
    action_ids = fields.One2many(inverse_name='flow_stage_button_id')
    group_ids = fields.Many2many(relation='fsm_flow_stage_button_group_rel')


class FsmFlowStageAuto(models.Model):
    _name = 'fsm.flow.stage.auto'
    _inherit = 'fsm.auto'
    _description = 'Field Service Management: Flow Stage Automations'

    auto_id = fields.Many2one('fsm.auto', string='Automation')
    stage_id = fields.Many2one('fsm.flow.stage', ondelete='cascade')
    field_ids = fields.One2many(inverse_name='flow_stage_auto_id')
    picking_ids = fields.One2many(inverse_name='flow_stage_auto_id')
    activity_ids = fields.One2many(inverse_name='flow_stage_auto_id')
    action_ids = fields.One2many(inverse_name='flow_stage_auto_id')
    cron_ids = fields.One2many(inverse_name='flow_stage_auto_id')
    todo_ids = fields.Many2many(relation='fsm_flow_stage_auto_todo_rel')
    type_id = fields.Many2one(related='stage_id.type_id', store=True, required=False)


class FsmFlowStageTodo(models.Model):
    _name = 'fsm.flow.stage.todo'
    _inherit = 'fsm.todo'
    _description = 'Field Service Management: Flow Stage Todos'

    todo_id = fields.Many2one('fsm.todo', string='Todo')
    stage_id = fields.Many2one('fsm.flow.stage', ondelete='cascade')
    action_ids = fields.One2many(inverse_name='flow_stage_todo_id')


class FsmFlowStageReason(models.Model):
    _name = 'fsm.flow.stage.reason'
    _inherit = 'fsm.reason'
    _description = 'Field Service Management: Flow Stage Reasons'

    reason_id = fields.Many2one('fsm.reason', string='Reason')
    stage_id = fields.Many2one('fsm.flow.stage', ondelete='cascade')
    project_ids = fields.Many2many(relation='fsm_flow_stage_project_rel')


class FsmFlowStageUser(models.Model):
    _name = 'fsm.flow.stage.user'
    _description = 'Field Service Management: Flow Stage Users'

    name = fields.Char(related='user_id.name', store=True)
    stage_id = fields.Many2one('fsm.flow.stage', ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', domain='[("id", "in", user_ids), ("share", "=", False)]', required=True, ondelete='cascade')
    sla_id = fields.Many2one('sla.agreement', string='SLA', domain='[("state", "=", "confirm"), ("stage_model_name", "=", "fsm.stage"), ("type", "=", "user"), ("user_id", "=", user_id)]', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    user_ids = fields.Many2many(related='stage_id.project_id.user_ids')

    @api.onchange('user_id')
    def onchange_user_id(self):
        self.sla_id = self.env['sla.agreement'].sudo().search([('state', '=', 'confirm'), ('type', '=', 'user'), ('user_id', '=', self.user_id.id)], limit=1).id if self.user_id else False


class FsmFlowStageTeam(models.Model):
    _name = 'fsm.flow.stage.team'
    _description = 'Field Service Management: Flow Stage Teams'

    name = fields.Char(related='team_id.name', store=True)
    stage_id = fields.Many2one('fsm.flow.stage', ondelete='cascade')
    team_id = fields.Many2one('crm.team', string='Team', domain='[("id", "in", team_ids)]', required=True, ondelete='cascade')
    sla_id = fields.Many2one('sla.agreement', string='SLA', domain='[("state", "=", "confirm"), ("stage_model_name", "=", "fsm.stage"), ("type", "=", "team"), ("team_id", "=", team_id)]', required=True)
    user_ids = fields.Many2many(related='team_id.member_ids')
    team_ids = fields.Many2many(related='stage_id.project_id.team_ids')

    @api.onchange('team_id')
    def onchange_team_id(self):
        self.sla_id = self.env['sla.agreement'].sudo().search([('state', '=', 'confirm'), ('type', '=', 'team'), ('team_id', 'in', self.team_id.ids)], limit=1).id if self.team_id else False
