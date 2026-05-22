# -*- coding: utf-8 -*-

import uuid
import base64
from pytz import timezone
from markupsafe import Markup
from datetime import datetime
from urllib.parse import quote_plus
from .. import ReasonError, AppointmentError, TaskError

from odoo import models, fields, api, tools, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError, AccessDenied
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF


class FsmTask(models.Model):
    _name = 'fsm.task'
    _description = 'Field Service Management: Tasks'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id desc'

    def _compute_name(self):
        for task in self:
            if task.uid:
                task.name = 'ID #%s' % task.uid
            elif task.order_uid:
                task.name = 'ORDER %s' % task.order_uid
            else:
                task.name = 'TASK #%s' % task.id

    @api.depends('stage_id', 'project_id')
    def _compute_kanban_state(self):
        self.kanban_state = 'normal'

    @api.depends('stage_id', 'type_id')
    def _compute_todo_ids(self):
        for task in self:
            value_ids = []
            if task.flow_stage_id:
                todo_ids = self.env['fsm.task.todo'].sudo().search([
                    ('task_id', '=', task.id),
                    ('flow_stage_id', '=', task.flow_stage_id.id),
                    ('todo_id', 'in', task.flow_stage_id.todo_ids.ids),
                ])
                value_ids.append((6, 0, todo_ids.ids))
            task.todo_ids = value_ids

    @api.depends('stage_id', 'type_id')
    def _compute_fields(self):
        uid = self.env.uid
        keys = [name for name in self._fields.keys() if name.startswith('field_')]

        for task in self:
            options = {}
            if task.flow_stage_id:
                for field in task.flow_stage_id.field_ids:
                    field_name = field.field_id.name
                    if field.group_ids:
                        for group in field.group_ids:
                            if uid in group.group_id.mapped('user_ids').ids:
                                value = options.get(field_name, [False, False, False])
                                options[field_name] = [value[0] or group.perm_read, value[1] or group.perm_open, value[2] or group.perm_update]
                    else:
                        value = options.get(field_name, [False, False, False])
                        options[field_name] = [value[0], value[1], value[2]]

            for key in keys:
                if self.env.user.has_group('fsm.group_administrator'):
                    value = [True, True, True]
                else:
                    value = options.get(key[6:], [False, False, False])
                if value[0] and value[1] and value[2]:
                    task.update({key: 4})
                elif value[0] and value[2]:
                    task.update({key: 3})
                elif value[0] and value[1]:
                    task.update({key: 2})
                elif value[0]:
                    task.update({key: 1})
                else:
                    task.update({key: 0})

    @api.depends('flow_id')
    def _compute_stage_ids(self):
        for task in self:
            task.stage_ids = task.flow_id.stage_ids.mapped('stage_id').ids

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        domain = []
        if self.env.context.get('default_project_id'):
            project = self.env['fsm.project'].sudo().browse(self.env.context['default_project_id'])
            domain.append(('id', 'in', project.stage_ids.ids))
        return self.env['fsm.stage'].search(domain, order=order)

    @api.depends('merchant_service_id')
    def _compute_service_zone_id(self):
        service_zones = self.env['fsm.service.zone'].sudo()
        for task in self:
            task.service_zone_id = service_zones.search([
                ('sla_id', '=', task.sla_id.id),
                ('state_id', '=', task.merchant_service_id.state_id.id),
                ('town_id', '=', task.merchant_service_id.town_id.id),
            ], limit=1).id
            task.team_ids = task.service_zone_id.team_ids.ids
            task.service_type_id = task.service_zone_id.type_id.id

    @api.depends('project_id', 'type_id', 'service_type_id')
    def _compute_flow_id(self):
        for task in self:
            if task.stage_id.type in ('2', '3'):
                raise UserError(_('You cannot change flow for this task in which stage type is "Closed" or "Cancelled".'))

            flows = task.project_id.flow_ids.filtered(lambda f: f.type_id.id == task.type_id.id and f.service_type_id.id == task.service_type_id.id)
            task.flow_id = flows and flows[0]['id'] or False

    def _compute_ticket_ids(self):
        tickets = self.env['sla.ticket'].sudo()
        for task in self:
            task.partner_ticket_show = len(task.partner_ticket_ids) > 0
            task.user_ticket_show = len(task.user_ticket_ids) > 0
            task.team_ticket_show = len(task.team_ticket_ids) > 0

    def _compute_timesheet_ids(self):
        for task in self:
            task.user_timesheet_ids = self.env['account.analytic.line'].sudo().search([('fsm_task_id', '=', task.id)]).ids

    def _compute_ticket_hours(self):
        for task in self:
            partner_ticket = task.partner_ticket_ids and task.partner_ticket_ids[0]
            user_ticket = task.user_ticket_ids and task.user_ticket_ids[0]
            team_ticket = task.team_ticket_ids and task.team_ticket_ids[0]

            task.partner_ticket_hour_left = partner_ticket and partner_ticket.stage_time_work_left or 0
            task.partner_ticket_hour_paused = partner_ticket and partner_ticket.stage_time_work_paused or 0
            task.partner_ticket_hour_spent = partner_ticket and partner_ticket.stage_time_work_spent or 0
            task.partner_ticket_hour_total = partner_ticket and partner_ticket.agreement_hour_total or 0
            task.user_ticket_hour_left = user_ticket and user_ticket.stage_time_work_left or 0
            task.user_ticket_hour_paused = user_ticket and user_ticket.stage_time_work_paused or 0
            task.user_ticket_hour_total = user_ticket and user_ticket.agreement_hour_total or 0
            task.team_ticket_hour_left = team_ticket and team_ticket.stage_time_work_left or 0
            task.team_ticket_hour_paused = team_ticket and team_ticket.stage_time_work_paused or 0
            task.team_ticket_hour_total = team_ticket and team_ticket.agreement_hour_total or 0
            task.due_date = partner_ticket and partner_ticket.due_date or False

    @api.depends('picking_ids.state')
    def _compute_is_all_internal_pickings_done(self):
        for task in self:
            pickings = task.picking_ids.filtered(lambda p: p.picking_type_code == 'internal' and p.state not in ('cancel'))
            task.is_all_internal_pickings_done = all(picking.state == 'done' for picking in pickings)

    @api.depends('picking_ids.state')
    def _compute_is_all_outgoing_pickings_done(self):
        for task in self:
            pickings = task.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing' and p.state not in ('cancel'))
            task.is_all_outgoing_pickings_done = all(picking.state == 'done' for picking in pickings)

    def _compute_is_all_todo_done(self):
        self.is_all_todo_done = all(todo.done for todo in self.todo_ids)
        if self.is_all_todo_done:
            autos = self.flow_stage_id.mapped('auto_ids').filtered(lambda a: a.trigger == 'todo' and a.todo_all)
            autos.run_todos_all(self.id, autos.ids)

    def _compute_picking_ids(self):
        for task in self:
            pickings_done = task.picking_ids.filtered(lambda p: p.state == 'done')
            pickings_ready = task.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
            task.picking_done_count = len(pickings_done)
            task.picking_ready_count = len(pickings_ready)
            task.picking_show = bool(task.picking_ids)

    def _compute_delivery_ids(self):
        for task in self:
            deliveries = self.env['stock.picking'].sudo().search([
                ('fsm_task_id', '=', task.id),
                ('carrier_id', '!=', False),
            ])
            deliveries_done = deliveries.filtered(lambda p: p.state == 'done')
            deliveries_ready = deliveries.filtered(lambda p: p.state not in ('done', 'cancel'))
            task.delivery_done_count = len(deliveries_done)
            task.delivery_ready_count = len(deliveries_ready)
            task.delivery_show = bool(deliveries)

    def _compute_domain_type(self):
        for task in self:
            task.domain_type = task.project_id.type_ids.mapped('type_id').ids

    def _compute_child_count(self):
        for task in self:
            task.child_count = len(task.child_ids)
            task.child_closed_count = len(task.child_ids.filtered(lambda t: t.stage_type == '2'))

    def _compute_appointments(self):
        for task in self:
            task.appointment_count = len(task.appointment_ids)
            task.appointment_date = task.appointment_ids[0].date and task.appointment_ids[0].date.date() if task.appointment_ids else False

    def _compute_todos(self):
        for task in self:
            todos = self.env['fsm.task.todo'].search([('task_id', '=', task.id)])
            task.todo_count = len(todos)
            task.todo_done = len(todos.filtered(lambda t: t.done))

    def _compute_merchant_category_id(self):
        for task in self:
            task.merchant_category_id = self.env.ref('fsm.partner_category_fsm').id

    def _compute_service_documents(self):
        for task in self:
            attachments = self.env['ir.attachment'].sudo().search([
                ('res_id', '=', task.id),
                ('res_model', '=', task._name),
                ('fsm_document_type', '!=', False),
            ])
            itf = next(filter(lambda a: a.fsm_document_type == 'itf', attachments), False) if attachments else False

            task.document_itf = itf and itf.id
            task.document_ids = [(6, 0, attachments.ids)]

    def _compute_log_id(self):
        for task in self:
            task.log_id = task.log_ids and task.log_ids[-1] or False

    def _compute_material_barcode_tag(self):
        tag = self.env['ir.config_parameter'].sudo().get_param('fsm.material_barcode_tag') or _('Material Barcode')
        for task in self:
            if task.material_barcode:
                task.material_barcode_tag = tag
            elif task.child_ids and any(t.material_barcode for t in task.child_ids):
                task.material_barcode_tag = tag
            elif task.parent_id and (task.parent_id.material_barcode or any(t.material_barcode for t in task.parent_id.child_ids)):
                task.material_barcode_tag = tag
            else:
                task.material_barcode_tag = False

    def _compute_sla_status(self):
        for task in self:
            task.sla_status = all((t.stage_time_work_left or 0) < 0 for t in task.partner_ticket_ids) and 'off' or 'on'

    def _search_sla_status(self, operator, value):
        if operator != '=':
            raise UserError(_('Operation not supported'))
        if value not in ('on', 'off'):
            raise UserError(_('Value not supported'))

        ids = []
        if value == 'off':
            for task in self.sudo().search([]):
                if all((t.stage_time_work_left or 0) < 0 for t in task.partner_ticket_ids):
                    ids.append(task.id)
        else:
            for task in self.sudo().search([]):
                if not all((t.stage_time_work_left or 0) < 0 for t in task.partner_ticket_ids):
                    ids.append(task.id)

        return [('id', 'in', ids)]

    def _search_partner_ticket_hour_left(self, operator, value):
        if operator not in ('=', '!=', '<', '>', '<=', '>='):
            raise UserError(_('Operation not supported'))

        ids = []
        tasks = self.sudo().search([])
        if operator == '=':
            for task in tasks:
                if task.partner_ticket_hour_left == value:
                    ids.append(task.id)
        elif operator == '!=':
            for task in tasks:
                if task.partner_ticket_hour_left != value:
                    ids.append(task.id)
        elif operator == '<':
            for task in tasks:
                if task.partner_ticket_hour_left < value:
                    ids.append(task.id)
        elif operator == '>':
            for task in tasks:
                if task.partner_ticket_hour_left > value:
                    ids.append(task.id)
        elif operator == '<=':
            for task in tasks:
                if task.partner_ticket_hour_left <= value:
                    ids.append(task.id)
        elif operator == '>=':
            for task in tasks:
                if task.partner_ticket_hour_left >= value:
                    ids.append(task.id)

        return [('id', 'in', ids)]

    def _search_partner_ticket_hour_paused(self, operator, value):
        if operator not in ('=', '!=', '<', '>', '<=', '>='):
            raise UserError(_('Operation not supported'))

        ids = []
        tasks = self.sudo().search([])
        if operator == '=':
            for task in tasks:
                if task.partner_ticket_hour_paused == value:
                    ids.append(task.id)
        elif operator == '!=':
            for task in tasks:
                if task.partner_ticket_hour_paused != value:
                    ids.append(task.id)
        elif operator == '<':
            for task in tasks:
                if task.partner_ticket_hour_paused < value:
                    ids.append(task.id)
        elif operator == '>':
            for task in tasks:
                if task.partner_ticket_hour_paused > value:
                    ids.append(task.id)
        elif operator == '<=':
            for task in tasks:
                if task.partner_ticket_hour_paused <= value:
                    ids.append(task.id)
        elif operator == '>=':
            for task in tasks:
                if task.partner_ticket_hour_paused >= value:
                    ids.append(task.id)

        return [('id', 'in', ids)]

    def _search_partner_ticket_hour_spent(self, operator, value):
        if operator not in ('=', '!=', '<', '>', '<=', '>='):
            raise UserError(_('Operation not supported'))

        ids = []
        tasks = self.sudo().search([])
        if operator == '=':
            for task in tasks:
                if task.partner_ticket_hour_spent == value:
                    ids.append(task.id)
        elif operator == '!=':
            for task in tasks:
                if task.partner_ticket_hour_spent != value:
                    ids.append(task.id)
        elif operator == '<':
            for task in tasks:
                if task.partner_ticket_hour_spent < value:
                    ids.append(task.id)
        elif operator == '>':
            for task in tasks:
                if task.partner_ticket_hour_spent > value:
                    ids.append(task.id)
        elif operator == '<=':
            for task in tasks:
                if task.partner_ticket_hour_spent <= value:
                    ids.append(task.id)
        elif operator == '>=':
            for task in tasks:
                if task.partner_ticket_hour_spent >= value:
                    ids.append(task.id)

        return [('id', 'in', ids)]

    def _search_due_date(self, operator, value):
        if operator not in ('=', '!=', '<', '>', '<=', '>='):
            raise UserError(_('Operation not supported'))

        if isinstance(value, str):
            value = datetime.strptime(value, DTF)
 
        ids = []
        tasks = self.sudo().search([])
        if operator == '=':
            for task in tasks:
                if task.due_date and task.due_date == value:
                    ids.append(task.id)
        elif operator == '!=':
            for task in tasks:
                if task.due_date and task.due_date != value:
                    ids.append(task.id)
        elif operator == '<':
            for task in tasks:
                if task.due_date and task.due_date < value:
                    ids.append(task.id)
        elif operator == '>':
            for task in tasks:
                if task.due_date and task.due_date > value:
                    ids.append(task.id)
        elif operator == '<=':
            for task in tasks:
                if task.due_date and task.due_date <= value:
                    ids.append(task.id)
        elif operator == '>=':
            for task in tasks:
                if task.due_date and task.due_date >= value:
                    ids.append(task.id)

        return [('id', 'in', ids)]

    @api.depends('merchant_service_id')
    def _compute_merchant_service(self):
        for task in self:
            task.merchant_service_contact_name = task.merchant_service_id.contact_id.name

    def _search_merchant_service_contact_name(self, operator, value):
        return [
            ('merchant_service_id.child_ids.type', '=', 'contact'),
            ('merchant_service_id.child_ids.is_company', '=', False),
            ('merchant_service_id.child_ids.name', operator, value),
        ]

    def _compute_document_url(self):
        for task in self:
            base_url = task.get_base_url()
            task.document_url = '%s/fsm/%s/document/%s' % (base_url, task.uid, task.document_token)

    def _compute_current_date(self):
        tz = timezone(self.env.context.get('tz') or self.env.user.tz or 'Europe/Istanbul')
        now = fields.Datetime.now()
        offset = tz.utcoffset(now)
        for task in self:
            task.current_date = now + offset

    @api.depends('product_ids', 'product_ids.product_id', 'product_ids.product_lot_id')
    def _compute_product(self):
        for task in self:
            line = len(task.product_ids) > 0 and task.product_ids[0]
            if line:
                task.product_id = line.product_id.id
                task.product_lot_id = line.product_lot_id.id
                task.product_lot_ref = line.product_lot_ref
                task.product_owner = line.product_owner
                task.product_state = line.product_state
                task.product_os = line.product_os
                task.product_type = line.product_type
                task.product_order_type = line.product_order_type
                task.product_operation_type = line.product_operation_type
                task.product_subpartner = line.product_subpartner
                task.product_operator = line.product_operator
            else:
                task.product_id = False
                task.product_lot_id = False
                task.product_lot_ref = False
                task.product_owner = False
                task.product_state = False
                task.product_os = False
                task.product_type = False
                task.product_order_type = False
                task.product_operation_type = False
                task.product_subpartner = False
                task.product_operator = False

    def _compute_product_move_line_ids(self):
        for task in self:
            task.product_move_line_ids = task.picking_ids.move_line_ids.filtered(lambda l: l.state == 'done').ids

    # Base Fields
    #name = fields.Char(required=True, tracking=True)
    name = fields.Char(compute='_compute_name')
    active = fields.Boolean(default=True, tracking=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer()
    uid = fields.Char(copy=False, readonly=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'High'),
    ], default='0', required=True, tracking=True, index=True)
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Ready'),
        ('blocked', 'Blocked')
    ], string='Status', copy=False, default='normal', required=True, compute='_compute_kanban_state', readonly=False, store=True)
    parent_id = fields.Many2one('fsm.task', string='Parent Task', index=True, ondelete='cascade')
    parent_type = fields.Many2one(related='parent_id.type_id')
    child_ids = fields.One2many('fsm.task', 'parent_id', string='Sub Tasks')
    child_count = fields.Integer(compute='_compute_child_count')
    child_closed_count = fields.Integer(compute='_compute_child_count')
    current_date = fields.Datetime(compute='_compute_current_date')
    project_id = fields.Many2one('fsm.project', required=True, index=True, check_company=True)
    project_item_id = fields.Many2one('fsm.project.item', string='Project Follow-Up', index=True, check_company=True)
    stage_id = fields.Many2one('fsm.stage', ondelete='restrict', related='flow_stage_id.stage_id', index=True, store=True, group_expand='_read_group_stage_ids')
    stage_type = fields.Selection(related='stage_id.type')
    partner_ticket_ids = fields.One2many('sla.ticket', 'fsm_task_id', string='Partner Tickets', domain='[("res_type", "=", "partner")]')
    partner_ticket_show = fields.Boolean(compute='_compute_ticket_ids', compute_sudo=True)
    partner_ticket_hour_left = fields.Float(compute='_compute_ticket_hours', search='_search_partner_ticket_hour_left', compute_sudo=True)
    partner_ticket_hour_paused = fields.Float(compute='_compute_ticket_hours', search='_search_partner_ticket_hour_paused', compute_sudo=True)
    partner_ticket_hour_spent = fields.Float(compute='_compute_ticket_hours', search='_search_partner_ticket_hour_spent', compute_sudo=True)
    partner_ticket_hour_total = fields.Float(compute='_compute_ticket_hours', compute_sudo=True)
    user_timesheet_ids = fields.Many2many('account.analytic.line', compute='_compute_timesheet_ids', compute_sudo=True)
    user_ticket_ids = fields.One2many('sla.ticket', 'fsm_task_id', string='User Tickets', domain='[("res_type", "=", "user")]')
    user_ticket_show = fields.Boolean(compute='_compute_ticket_ids', compute_sudo=True)
    user_ticket_hour_left = fields.Float(compute='_compute_ticket_hours', compute_sudo=True)
    user_ticket_hour_paused = fields.Float(compute='_compute_ticket_hours', compute_sudo=True)
    user_ticket_hour_total = fields.Float(compute='_compute_ticket_hours', compute_sudo=True)
    team_ticket_ids = fields.One2many('sla.ticket', 'fsm_task_id', string='Team Tickets', domain='[("res_type", "=", "team")]')
    team_ticket_show = fields.Boolean(compute='_compute_ticket_ids', compute_sudo=True)
    team_ticket_hour_left = fields.Float(compute='_compute_ticket_hours', compute_sudo=True)
    team_ticket_hour_paused = fields.Float(compute='_compute_ticket_hours', compute_sudo=True)
    team_ticket_hour_total = fields.Float(compute='_compute_ticket_hours', compute_sudo=True)
    stage_ids = fields.Many2many('fsm.stage', compute='_compute_stage_ids', compute_sudo=True)
    stage_type = fields.Selection(related='stage_id.type', string='Stage Type', store=True, index=True)
    flow_id = fields.Many2one('fsm.flow', compute='_compute_flow_id', store=True, readonly=False, index=True)
    flow_stage_id = fields.Many2one('fsm.flow.stage', tracking=True, index=True, domain="[('flow_id', '=', flow_id)]")
    user_ids = fields.Many2many('res.users', 'fsm_task_user_rel', 'task_id', 'user_id', default=lambda self: [(4, self.env.user.id)])
    user_id = fields.Many2one('res.users', string='Technician')
    picking_ids = fields.One2many('stock.picking', 'fsm_task_id', string='Pickings')
    picking_show = fields.Boolean(compute='_compute_picking_ids')
    picking_ready_count = fields.Integer(compute='_compute_picking_ids')
    picking_done_count = fields.Integer(compute='_compute_picking_ids')
    delivery_ids = fields.One2many('stock.picking', 'fsm_task_id', string='Deliveries', domain="[('carrier_id', '!=', False)]")
    delivery_show = fields.Boolean(compute='_compute_delivery_ids')
    delivery_ready_count = fields.Integer(compute='_compute_delivery_ids')
    delivery_done_count = fields.Integer(compute='_compute_delivery_ids')
    appointment_ids = fields.One2many('fsm.appointment', 'task_id', string='Appointments')
    appointment_count = fields.Integer(compute='_compute_appointments')
    appointment_date = fields.Date(compute='_compute_appointments')
    todo_count = fields.Integer(compute='_compute_todos', string='Todo Count')
    todo_done = fields.Integer(compute='_compute_todos', string='Todo Done Count')
    todo_ids = fields.Many2many('fsm.task.todo', string='Todos', compute='_compute_todo_ids', readonly=False)
    company_id = fields.Many2one('res.company', related='project_id.company_id', store=True)
    close_success = fields.Boolean(string='Close Successful', readonly=True)
    close_done = fields.Boolean(string='Close Done', readonly=True)
    close_date = fields.Datetime(string='Close Date', readonly=True)
    close_contact_id = fields.Many2one('res.partner', string='Close Responsible Contact', readonly=True)
    reason_code = fields.Char(string='Reason Code', related='reason_id.code', store=True, readonly=True)
    reason_name = fields.Char(string='Reason Name', related='reason_id.name', store=True, readonly=True)
    reason_id = fields.Many2one('fsm.reason', string='Reason', readonly=True)
    reason_desc = fields.Text(string='Reason Description', readonly=True)
    approval_desc = fields.Char(string='Approval Description', readonly=True)
    approval_state = fields.Selection(selection=[('0', 'Approved'), ('1', 'Rejected')], string='Approval State', readonly=True)
    log_ids = fields.One2many('fsm.task.log', 'task_id', string='Logs', readonly=True)
    log_id = fields.Many2one('fsm.task.log', compute='_compute_log_id')

    # Dynamic Fields
    barcode = fields.Char(string='Barcode')
    description = fields.Text(string='Description')
    package_id = fields.Many2one('fsm.package', string='Package', ondelete='set null')
    sla_id = fields.Many2one('sla.agreement', string='SLA', ondelete='restrict', required=True, index=True)
    sla_status = fields.Selection([
        ('on', 'SLA On'),
        ('off', 'SLA Off'),
    ], string='SLA Status', compute='_compute_sla_status', search='_search_sla_status')
    order_uid = fields.Char(string='Order ID', readonly=True, copy=False)
    project_uid = fields.Char(string='Project ID', related='project_item_id.uid')
    project_name = fields.Char(string='Project Name', related='project_item_id.name')
    due_date = fields.Datetime(string='Due Date', compute='_compute_ticket_hours', search='_search_due_date', compute_sudo=True)
    type_id = fields.Many2one('fsm.type', string='Type', ondelete='restrict', required=True, index=True)
    service_zone_id = fields.Many2one('fsm.service.zone', string='Service Zone', ondelete='restrict', copy=True, readonly=True, store=True, compute='_compute_service_zone_id')
    service_type_id = fields.Many2one('fsm.service.type', string='Service Type', ondelete='restrict', copy=True, store=True, compute='_compute_service_zone_id', tracking=True)
    partner_id = fields.Many2one('res.partner', related='project_id.partner_id', store=True, index=True, tracking=True)
    team_ids = fields.Many2many('crm.team', 'fsm_task_team_rel', 'task_id', 'team_id', string='Teams', domain="[('id', 'in', domain_team)]", compute='_compute_service_zone_id', store=True, readonly=False)
    user_ids = fields.Many2many('res.users', 'fsm_task_user_rel', 'task_id', 'user_id', string='Users', domain="[('id', 'in', domain_user)]")
    product_ids = fields.One2many('fsm.task.product', 'task_id', tracking=True, string='Products')
    product_id = fields.Many2one('product.product', string='Product', compute='_compute_product', store=True)
    product_lot_id = fields.Many2one('stock.lot', string='Product Lot/Serial', compute='_compute_product', store=True)
    product_lot_ref = fields.Char(string='Product Lot/Serial Reference', compute='_compute_product', store=True)
    product_owner = fields.Char(string='Product Owner', compute='_compute_product', store=True)
    product_state = fields.Selection([
        ('examining', 'Examining'),
        ('solid', 'Solid'),
        ('faulty', 'Faulty'),
        ('scrap', 'Scrap'),
    ], string='Product State', compute='_compute_product', store=True)
    product_os = fields.Char(string='Product Operating System', compute='_compute_product', store=True)
    product_type = fields.Char(string='Product Type', compute='_compute_product', store=True)
    product_order_type = fields.Char(string='Product Order Type', compute='_compute_product', store=True)
    product_operation_type = fields.Char(string='Product Operation Type', compute='_compute_product', store=True)
    product_subpartner = fields.Char(string='Product Subpartner', compute='_compute_product', store=True)
    product_operator = fields.Char(string='Product Operator', compute='_compute_product', store=True)
    product_move_line_ids = fields.Many2many('stock.move.line', compute='_compute_product_move_line_ids')
    setup_uid = fields.Char(string='Setup ID')
    setup_key = fields.Char(string='Setup Key')
    setup_merchant_uid = fields.Char(string='Merchant ID')
    setup_application_ids = fields.One2many('fsm.task.setup.application', 'task_id', string='Applications')
    merchant_id = fields.Many2one('res.partner', required=True, index=True, tracking=True, domain='[("is_company", "=", True), ("parent_id", "=", False)]')
    merchant_vat = fields.Char(related='merchant_id.vat', string='Merchant VAT')
    merchant_service_id = fields.Many2one('res.partner', required=False, index=True, tracking=True, domain='["|", ("id", "=", merchant_id), ("parent_id", "=", merchant_id)]')
    merchant_service_country_id = fields.Char(related='merchant_service_id.country_id.name', string='Merchant Service Country')
    merchant_service_state_id = fields.Char(related='merchant_service_id.state_id.name', string='Merchant Service City')
    merchant_service_city = fields.Char(related='merchant_service_id.city', string='Merchant Service Town')
    merchant_service_zip = fields.Char(related='merchant_service_id.zip', string='Merchant Service ZIP')
    merchant_service_street = fields.Char(related='merchant_service_id.street', string='Merchant Service District')
    merchant_service_street2 = fields.Char(related='merchant_service_id.street2', string='Merchant Service Address')
    merchant_service_table_name = fields.Char(related='merchant_service_id.table_name', string='Merchant Service Table Name')
    merchant_service_phone = fields.Char(related='merchant_service_id.phone', string='Merchant Service Phone')
    merchant_service_mobile = fields.Char(related='merchant_service_id.mobile', string='Merchant Service Mobile')
    merchant_service_contact_name = fields.Char(compute='_compute_merchant_service', search='_search_merchant_service_contact_name', string='Merchant Service Contact', compute_sudo=True)
    merchant_category_id = fields.Many2one('res.partner.category', compute='_compute_merchant_category_id')
    merchant_service_ok = fields.Boolean(string='Use Service Address')
    material_id = fields.Many2one('product.product', string='Material')
    material_name = fields.Char(string='Material Name')
    material_serial = fields.Char(string='Material Serial Number')
    material_count = fields.Integer(string='Material Count')
    material_barcode = fields.Char(string='Material Barcode')
    material_barcode_tag = fields.Char(string='Material Barcode Tag', compute='_compute_material_barcode_tag')
    document_uid = fields.Char(string='Document Code')
    document_type = fields.Char(string='Document Type')
    document_name = fields.Char(string='Document Name')
    document_serial = fields.Char(string='Document Serial')
    document_token = fields.Char(string='Document Token')
    document_url = fields.Char(string='Document URL', compute='_compute_document_url')
    document_ids = fields.Many2many('ir.attachment', compute='_compute_service_documents', string='Service Documents')
    document_itf = fields.Many2one('ir.attachment', compute='_compute_service_documents', string='ITF Document')
    document_info_vat = fields.Char(string='Document Information VAT')
    document_info_name = fields.Char(string='Document Information Name')
    document_info_birthday = fields.Date(string='Document Information Birthday')
    document_info_birthplace = fields.Char(string='Document Information Bırthplace')
    document_info_iban = fields.Char(string='Document Information IBAN')
    document_info_detail_ids = fields.One2many('fsm.task.document.detail', 'task_id', string='Document Information Others')

    # Domain Fields
    domain_product = fields.Many2many(related='project_id.product_ids')
    domain_team = fields.Many2many(related='project_id.team_ids')
    domain_user = fields.Many2many(related='project_id.user_ids')
    domain_todo = fields.One2many(related='flow_stage_id.todo_ids')

    # Technical Fields
    is_all_internal_pickings_done = fields.Boolean(compute='_compute_is_all_internal_pickings_done', store=True)
    is_all_outgoing_pickings_done = fields.Boolean(compute='_compute_is_all_outgoing_pickings_done', store=True)
    is_all_todo_done = fields.Boolean()
    is_barcode_scanned = fields.Boolean()

    # Field Toggles
    field_create_date = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_type_id = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_package_id = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_partner_id = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_merchant_id = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_merchant_vat = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_merchant_service_id = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_merchant_service_country_id = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_merchant_service_state_id = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_merchant_service_city = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_merchant_service_zip = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_merchant_service_street = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_merchant_service_street2 = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_merchant_service_table_name = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_merchant_service_contact_name = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_merchant_service_phone = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_merchant_service_mobile = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_service_zone_id = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_service_type_id = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_due_date = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_description = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_barcode = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_sla_id = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_sla_status = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_order_uid = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_project_uid = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_project_name = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_todo_ids = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_team_ids = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_user_ids = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_user_id = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_product_ids = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_product_id = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_product_lot_id = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_product_lot_ref = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_product_owner = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_product_state = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_product_type = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_product_os = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_product_subpartner = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_product_operator = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_product_order_type = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_product_operation_type = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_setup_uid = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_setup_key = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_setup_application_ids = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_setup_merchant_uid = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_material_id = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_material_name = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_material_serial = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_material_count = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_material_barcode = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_document_uid = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_document_type = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_document_name = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_document_info_vat = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_document_info_name = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_document_info_birthday = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_document_info_birthplace = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_document_info_iban = fields.Integer(compute='_compute_fields', compute_sudo=True)
    field_document_info_detail_ids = fields.Integer(compute='_compute_fields', compute_sudo=True)

    def _get_mail_thread_data_attachments(self):
        self.ensure_one()
        res = super()._get_mail_thread_data_attachments()
        res |= self.env['ir.attachment'].search([('res_id', 'in', self.todo_ids.ids), ('res_model', '=', 'fsm.task.todo')], order='id desc')
        res |= self.env['ir.attachment'].search([('res_id', 'in', self.appointment_ids.ids), ('res_model', '=', 'fsm.appointment')], order='id desc')
        res |= self.env['ir.attachment'].search([('res_id', 'in', self.delivery_ids.ids), ('res_model', '=', 'stock.picking'), '|', ('delivery_contract_rendered', '=', True), ('delivery_contract_signed', '=', True)], order='id desc')
        return res

    def _create_document_itf(self):
        itf = self.env['fsm.form'].sudo().search([('code', '=', 'ITF')], limit=1)
        if itf:
            token = str(uuid.uuid4())
            serial = 'P-ITF-%s' % fields.Datetime.now().strftime('%Y%m%d%H%M')
            self.write({'document_token': token, 'document_serial': serial})

            body = itf.render(self)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            rcontext = {'mode': 'print', 'base_url': base_url}
            #header = self.env['ir.actions.report']._render_template("web.internal_layout", values=rcontext)
            #header = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=Markup(header.decode())))

            body = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=Markup(body)))
            pdf = self.env['ir.actions.report']._run_wkhtmltopdf(
                [body.decode()],
                landscape=False,
                #header=header.decode(),
                specific_paperformat_args={
                    'data-report-margin-top': 10,
                    'data-report-margin-bottom': 10,
                    'data-report-header-spacing': 10,
                }
            )

            attachment = self.env['ir.attachment'].sudo().create({
                'type': 'binary',
                'name': '%s.pdf' % (serial),
                'mimetype': 'application/pdf',
                'fsm_document_type': 'itf',
                'fsm_document_serial': serial,
                'access_token': token,
                'res_model': self._name,
                'res_id': self.id,
                'datas': base64.b64encode(pdf),
            })
            return attachment
        return None

    def _close(self):
        return # function closed due to request of customer
        if self.close_success and not self.document_itf:
            self._create_document_itf()

    def _prepare_picking_values(self, action=None, values={}, moves={}):
        if self.flow_id.misc_use_material_product:
            product = self.material_id
            quantity = self.material_count
        else:
            if not self.product_id:
                self._compute_product()
            product = self.product_id
            quantity = 1

        if not product:
            raise UserError(_("This task doesn't have any product."))

        if action:
            if getattr(action, '_name', False) == 'fsm.button.action':
                values.update({'fsm_button_action_id': action.id})

            if getattr(action, 'picking_return_ok', False):
                values.update({
                    'picking_type_id': action.picking_type_id.return_picking_type_id.id,
                    'location_id': action.picking_location_dest_id.id or action.picking_type_id.default_location_dest_id.id,
                    'location_dest_id': action.picking_location_id.id or action.picking_type_id.default_location_src_id.id,
                    **values,
                    **self.env.context.get('values_stock_picking', {})
                })
                moves.update({
                    'location_id': action.picking_location_dest_id.id or action.picking_type_id.default_location_dest_id.id,
                    'location_dest_id': action.picking_location_id.id or action.picking_type_id.default_location_src_id.id,
                    **moves,
                    **self.env.context.get('values_stock_move', {})
                })
            else:
                values.update({
                    'picking_type_id': action.picking_type_id.id,
                    'location_id': action.picking_location_id.id or action.picking_type_id.default_location_src_id.id,
                    'location_dest_id': action.picking_location_dest_id.id or action.picking_type_id.default_location_dest_id.id,
                    **values,
                    **self.env.context.get('values_stock_picking', {})
                })
                moves.update({
                    'location_id': action.picking_location_id.id or action.picking_type_id.default_location_src_id.id,
                    'location_dest_id': action.picking_location_dest_id.id or action.picking_type_id.default_location_dest_id.id,
                    **moves,
                    **self.env.context.get('values_stock_move', {})
                })

        return {
            'fsm_task_id': self.id,
            'fsm_flow_stage_id': self.flow_stage_id.id,
            'partner_id': self.merchant_service_id.id,
            'move_ids': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': quantity,
                **moves
            })],
            **values
        }

    def _update_log_ids(self):
        if not self.env.context.get('no_log'):
            for task in self.sudo():
                date = fields.Datetime.now()
                log = task.log_ids and task.log_ids[-1] or False
                if log:
                    if log.stage_id.id == task.flow_stage_id.id:
                        if log.reason_id.id == task.reason_id.id:
                            continue
                        self.env.cr.execute('''
                            UPDATE fsm_task_log SET reason_id=%s, reason_code=$$%s$$, reason_name=$$%s$$, reason_desc=$$%s$$
                            WHERE id=%s
                            ''' % (
                                task.reason_id.id or 'NULL',
                                task.reason_id.code or 'NULL',
                                task.reason_id.name or 'NULL',
                                task.reason_id.description or 'NULL',
                                log.id
                            )
                        )
                        continue
                    self.env.cr.execute('''
                        UPDATE fsm_task_log SET date_to='%s'
                        WHERE id=%s AND date_to IS NULL
                        ''' % (date.strftime(DTF), log.id)
                    )
                self.env.cr.execute('''
                    INSERT INTO fsm_task_log (task_id, stage_id, reason_id, reason_code, reason_name, reason_desc, date_from, create_uid, write_uid, create_date, write_date)
                    VALUES (%s, %s, %s, $$%s$$, $$%s$$, $$%s$$, '%s', 1, 1, NOW() at time zone 'UTC', NOW() at time zone 'UTC')
                    ''' % (
                        task.id or 'NULL',
                        task.flow_stage_id.id or 'NULL',
                        task.reason_id.id or 'NULL',
                        task.reason_id.code or 'NULL',
                        task.reason_id.name or 'NULL',
                        task.reason_id.description or 'NULL',
                        date.strftime(DTF)
                    )
                )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self.env.context.get('default_project_id') and self.env.context.get('default_type_id'):
            flow = self.env['fsm.flow'].search([
                ('project_id', '=', self.env.context['default_project_id']),
                ('type_id', '=', self.env.context['default_type_id']),
            ], limit=1)
            if flow and flow.stage_ids:
                stage = flow.stage_ids[0]
                res.update({'flow_stage_id': stage.id})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            #if 'parent_id' not in vals:
                #if vals.get('product_lot_id'):
                    #task = self.env['fsm.task'].sudo().search([
                    #    ('stage_id.type', '!=', '2'),
                    #    ('product_lot_id', '=', vals['product_lot_id']),
                    #], limit=1)
                    #if task:
                    #    raise ValidationError(_('Product lot/serial number %s is being used in an ongoing task %s.') % (task.product_lot_id.name, task.name))

                    #task = self.env['fsm.task'].sudo().search([
                    #    ('stage_id.type', '!=', '2'),
                    #    ('product_lot_id', '=', vals['product_lot_id']),
                    #], limit=1)

            if 'flow_stage_id' not in vals and 'project_id' in vals and 'type_id' in vals and 'service_type_id' in vals:
                flow = self.env['fsm.flow'].search([
                    ('project_id', '=', vals['project_id']),
                    ('type_id', '=', vals['type_id']),
                    ('service_type_id', '=', vals['service_type_id']),
                ], limit=1)
                if flow and flow.stage_ids:
                    stage = flow.stage_ids[0]
                    vals.update({'flow_id': flow.id, 'flow_stage_id': stage.id})

        tasks = super().create(vals_list)
        tasks.set_uid()
        tasks.set_flow()
        tasks.set_products()

        self.env['fsm.auto'].run_creates(tasks)
        tasks._update_log_ids()

        today = fields.Date.today()
        for task in tasks:
            if task.project_item_id.task_maximum and task.project_item_id.task_maximum < task.project_item_id.task_count:
                raise TaskError(_('Task count of this project cannot be higher than %s.') % task.project_item_id.task_maximum)
            if (task.project_item_id.date_start and task.project_item_id.date_start > today) or (task.project_item_id.date_end and task.project_item_id.date_end < today):
                raise TaskError(_('Task must be created between %s and %s.') % (
                    task.project_item_id.date_start.strftime('%d/%m/%Y'),
                    task.project_item_id.date_end.strftime('%d/%m/%Y'),
                ))

            if not task.parent_id:
                type = next(filter(lambda t: t.type_id.id == task.type_id.id, task.project_id.type_ids), None)
                if type and type.subtype_ids:
                    for subtype in type.subtype_ids:
                        task.copy({'parent_id': task.id, 'type_id': subtype.id})

            if task.sla_id:
                stage = task.sla_id.stage_ids.filtered(lambda s: s.stage_id == task.stage_id.id)
                if stage:
                    self.env['sla.ticket'].sudo().create({
                        'agreement_id': task.sla_id.id,
                        'agreement_hour_total': task.service_zone_id.value if task.sla_id.hour_model and task.service_zone_id else task.sla_id.hour_total,
                        'partner_id': task.sla_id.partner_id.id,
                        'fsm_task_id': task.id,
                        'stage_id': stage.id,
                        'res_type': 'partner',
                        'res_id': task.id,
                        'res_model': task._name,
                        'res_ref': '%s,%s' % (task._name, task.id),
                    })

            for user in task.flow_stage_id.user_ids:
                stage = user.sla_id.stage_ids.filtered(lambda s: s.stage_id == task.stage_id.id)
                if stage:
                    self.env['sla.ticket'].sudo().create({
                        'partner_id': user.sla_id.partner_id.id,
                        'agreement_id': user.sla_id.id,
                        'fsm_task_id': task.id,
                        'stage_id': stage.id,
                        'res_type': 'user',
                        'res_id': task.id,
                        'res_model': task._name,
                        'user_id': user.user_id.id,
                        'res_ref': '%s,%s' % (task._name, task.id),
                    })

            for team in task.flow_stage_id.team_ids:
                stage = team.sla_id.stage_ids.filtered(lambda s: s.stage_id == task.stage_id.id)
                if stage:
                    self.env['sla.ticket'].sudo().create({
                        'partner_id': team.sla_id.partner_id.id,
                        'agreement_id': team.sla_id.id,
                        'fsm_task_id': task.id,
                        'stage_id': stage.id,
                        'res_type': 'team',
                        'res_id': task.id,
                        'res_model': task._name,
                        'team_id': team.team_id.id,
                        'res_ref': '%s,%s' % (task._name, task.id)
                    })

        return tasks

    def _write(self, values):
        vals = {}
        ids = self.ids
        query = f"SELECT * FROM fsm_task WHERE id IN ({','.join(map(str, ids))})"
        self.env.cr.execute(query)
        for v in self.env.cr.dictfetchall():
            vals.update({
                v['id']: {
                    'value': values,
                    'prev': dict(v),
                    'next': dict(v),
                    'flow': v['flow_id'],
                    'stage': v['flow_stage_id'],
                }
            })
        for tid in ids:
            vals[tid]['next'].update(values)
        self.env['fsm.flow.stage.auto'].run_fields(vals)

        res = super()._write(values)

        if 'stage_id' in values or 'type_id' in values:
            todos = self.env['fsm.task.todo'].sudo()
            for task in self.sudo():
                creates = []
                deletes = []

                todo_ids = todos.search([('task_id', '=', task.id)]).mapped('todo_id').ids
                if task.flow_stage_id:
                    for todo in task.flow_stage_id.todo_ids:
                        if todo.id in todo_ids:
                            todo_ids.remove(todo.id)
                        else:
                            creates.append({
                                'name': todo.name,
                                'todo_id': todo.id,
                                'task_id': task.id,
                            })
                for todo in todo_ids:
                    deletes.append(todo)

                todos.create(creates)
                todos.browse(deletes).unlink()

        return res

    def write(self, values):
        if 'service_type_id' in values:
            for task in self:
                flow = self.env['fsm.flow'].sudo().search([
                    ('service_type_id', '=', values['service_type_id']),
                    ('project_id', '=', task.project_id.id),
                    ('type_id', '=', task.type_id.id),
                ], limit=1)
                if flow and flow.id != task.flow_id.id and flow.stage_ids:
                    stage = flow['stage_ids'][0]
                    values.update({
                        'flow_id': flow.id,
                        'flow_stage_id': stage.id,
                        'stage_id': stage.stage_id.id,
                    })

                    service_zone_id = self.env['fsm.service.zone'].sudo().search([
                        ('sla_id', '=', task.sla_id.id),
                        ('state_id', '=', task.merchant_service_id.state_id.id),
                        ('town_id', '=', task.merchant_service_id.town_id.id),
                    ], limit=1)
                    if service_zone_id:
                        values.update({
                            'service_zone_id': service_zone_id.id,
                        })

        if 'flow_stage_id' in values:
            for task in self:
                stage = self.env['fsm.flow.stage'].sudo().browse(values['flow_stage_id'])
                stage_closed = stage.stage_id.type == '2'

                if self.env.user.has_group('fsm.group_user') and task.todo_ids:
                    # We were considiring checking todos when successfully completing a task, but we do not anymore...
                    #if stage_closed and values.get('close_success') and any(not t.done for t in task.todo_ids):
                    #    raise UserError(_('You cannot close this task without completing todos.'))
                    if stage.misc_prev_todo_required and any(not t.done and t.required for t in task.todo_ids):
                        raise UserError(_('You cannot change stage for this task without completing todos.'))
            
            if not self.env.context.get('no_reason'):
                reason_ids = (stage.reason_ok or stage_closed) and stage.reason_ids
                if reason_ids or stage_closed:
                    action = self.env.ref('fsm.action_stage_reason').sudo().read()[0]
                    action['context'] = {
                        **self.env.context,
                        'values': values,
                        'default_task_ids': self.ids,
                        'default_stage_id': stage.id,
                    }
                    if reason_ids:
                        action['context']['reason_ids'] = reason_ids.ids
                    if stage_closed:
                        action['name'] = _('Close Task')
                    raise ReasonError(_('Reason not specified'), action)

            if not self.env.context.get('no_appointment') and 'flow_stage_id' in values:
                stage = self.env['fsm.flow.stage'].sudo().browse(values['flow_stage_id'])
                if stage.misc_show_appointment_form:
                    action = self.env.ref('fsm.action_appointment').sudo().read()[0]
                    context = {
                        **self.env.context,
                        'values': values,
                        **self.env.context.get('defaults', {}).get('fsm.appointment', {})
                    }
                    if len(self) > 1:
                        context.update({'default_task_ids': self.ids})
                    else:
                        context.update({'default_task_id': self.id})
                    action.update({
                        'target': 'new',
                        'views': [(False, 'form')],
                        'context': context,
                    })
                    if self.env.context.get('defaults'): # If defaults exist, commit values then continue
                        self.env.cr.commit()
                    raise AppointmentError(_('Appointment dialog must be filled'), action)

        res = super().write(values)

        if 'flow_stage_id' in values:
            for task in self:
                task = task.sudo()
                if task.stage_type == '2':
                    task._close()
                else:
                    task.write({
                        'close_success': False,
                        'close_done': False,
                        'close_date': False,
                    })

                if task.sla_id:
                    stage = task.sla_id.stage_ids.filtered(lambda s: s.stage_id == task.stage_id.id)
                    if stage:
                        for ticket in task.partner_ticket_ids:
                            ticket.write({'stage_id': stage.id})
                    else:
                        for ticket in task.partner_ticket_ids:
                            ticket.stage_log_id.set_date_to()

                for timesheet in task.user_timesheet_ids.filtered(lambda t: not t.fsm_date_to):
                    date_to = fields.Datetime.now()
                    date_from = timesheet.fsm_date_from or date_to
                    unit_amount = (date_to - date_from).total_seconds() / 3600
                    try:
                        timesheet.write({
                            'fsm_date_to': date_to,
                            'unit_amount': unit_amount,
                        })
                    except:
                        pass
                for user in task.flow_stage_id.user_ids:
                    if user.analytic_account_id:
                        employee = self.env['hr.employee'].sudo().search([('user_id', '=', user.user_id.id)], limit=1)
                        self.env['account.analytic.line'].sudo().create({
                            'account_id': user.analytic_account_id.id,
                            'name': task.stage_id.name,
                            'fsm_task_id': task.id,
                            'user_id': user.user_id.id,
                            'employee_id': employee.id,
                            'fsm_date_from': fields.Datetime.now(),
                        })

                users = []
                for user in task.flow_stage_id.user_ids:
                    users.append(user.user_id.id)
                    ticket = task.user_ticket_ids.filtered(lambda u: u.user_id == user.user_id.id)
                    if ticket:
                        stage = user.sla_id.stage_ids.filtered(lambda s: s.stage_id == task.stage_id.id)
                        if stage:
                            ticket.write({'stage_id': stage.id})
                        else:
                            ticket.stage_log_id.set_date_to()
                    else:
                        stage = user.sla_id.stage_ids.filtered(lambda s: s.stage_id == task.stage_id.id)
                        if stage:
                            self.env['sla.ticket'].sudo().create({
                                'partner_id': user.sla_id.partner_id.id,
                                'agreement_id': user.sla_id.id,
                                'fsm_task_id': task.id,
                                'stage_id': stage.id,
                                'res_type': 'user',
                                'res_id': task.id,
                                'res_model': task._name,
                                'user_id': user.user_id.id,
                                'res_ref': '%s,%s' % (task._name, task.id),
                            })
                for ticket in task.user_ticket_ids.filtered(lambda u: u.user_id not in users):
                    ticket.stage_log_id.set_date_to()

                teams = []
                for team in task.flow_stage_id.team_ids:
                    teams.append(team.team_id.id)
                    ticket = task.team_ticket_ids.filtered(lambda u: u.team_id == team.team_id.id)
                    if ticket:
                        stage = team.sla_id.stage_ids.filtered(lambda s: s.stage_id == task.stage_id.id)
                        if stage:
                            ticket.write({'stage_id': stage.id})
                        else:
                            ticket.stage_log_id.set_date_to()
                    else:
                        stage = team.sla_id.stage_ids.filtered(lambda s: s.stage_id == task.stage_id.id)
                        if stage:
                            self.env['sla.ticket'].sudo().create({
                                'partner_id': team.sla_id.partner_id.id,
                                'agreement_id': team.sla_id.id,
                                'fsm_task_id': task.id,
                                'stage_id': stage.id,
                                'res_type': 'team',
                                'res_id': task.id,
                                'res_model': task._name,
                                'team_id': team.team_id.id,
                                'res_ref': '%s,%s' % (task._name, task.id),
                            })
                for ticket in task.team_ticket_ids.filtered(lambda u: u.team_id not in teams):
                    ticket.stage_log_id.set_date_to()

        if 'flow_stage_id' in values or 'reason_id' in values:
            self._update_log_ids()

        return res

    @api.model
    def scan_barcode(self, barcode):
        task = self.search(['|', ('uid', '=', barcode), ('material_barcode', '=', barcode)], limit=1)
        if task:
            action = self.env.ref('fsm.action_task').sudo().read()[0]
            action.update({
                'views': [(False, 'form')],
                'view_mode': 'form',
                'res_id': task.id
            })
            return action

        task = self.search([('product_lot_id.name', '=', barcode)], limit=1)
        if task:
            autos = task.flow_stage_id.mapped('auto_ids').filtered(lambda a: a.trigger == 'barcode')
            autos.run_barcodes(task.id, autos.ids)

            action = self.env.ref('fsm.action_task').sudo().read()[0]
            action.update({
                'views': [(False, 'form')],
                'view_mode': 'form',
                'res_id': task.id
            })
            return action

        return False

    @api.model
    def _check_button(self, button, tasks):
        if not button.visible_ok:
            if not button.visible_code:
                return False
            context = {
                'env': self.env,
                'uid': self._uid,
                'user': self.env.user,
                'time': tools.safe_eval.time,
                'datetime': tools.safe_eval.datetime,
                'dateutil': tools.safe_eval.dateutil,
                'timezone': timezone,
                'tasks': tasks,
            }
            safe_eval(button.visible_code.strip(), context, mode='exec')
            if context.get('visible') is not True:
                return False
        if button.group_ids:
            gids = button.group_ids.ids
            groups = self.env.user.groups_id.ids
            if all(g not in gids for g in groups):
                return False
        return True

    @api.model
    def get_buttons(self, project_id=None, task_id=None):
        buttons = []
        tasks = self.env['fsm.task']
        if task_id:
            tasks = tasks.browse(task_id)
            project_id = tasks.project_id.id
        if project_id:
            flows = self.env['fsm.flow'].search([('project_id', '=', project_id)])
            if not tasks:
                tasks = tasks.search([('project_id', '=', project_id)])
            for flow in flows:
                for button in flow.mapped('stage_ids.button_ids'):
                    if not self._check_button(button, tasks):
                        continue

                    buttons.append({
                        'id': button.id,
                        'name': button.name,
                        'type': flow.type_id.id,
                        'desc': button.description,
                        'stage': button.stage_id.id,
                        'theme': button.custom_theme,
                        'class': button.custom_class,
                        'style': button.custom_style,
                    })
        return buttons

    @api.model
    def run_button(self, button_id, record_ids=[]):
        button = self.env['fsm.flow.stage.button'].browse(button_id)
        tasks = self.env['fsm.task'].browse(record_ids)
        if not self._check_button(button, tasks):
            raise Exception(_('Button execute conditions are not met.'))
        return button._run_action(tasks)

    def set_uid(self):
        for task in self:
            tz = timezone(self.env.context.get('tz') or self.env.user.tz or 'Europe/Istanbul')
            now = fields.Datetime.now()
            offset = tz.utcoffset(now)
            date = task.create_date + offset
            task.write({
                'uid': 'WO%s%s%s-%s-%s' % (
                    task.project_id.code or 'XX',
                    date.strftime('%y%m%d'),
                    str(task.type_id.id).zfill(3),
                    task.project_id.sequence_id.next_by_id(),
                    date.strftime('%H%M'),
                )
            })

    def set_flow(self):
        for task in self:
            if task.parent_id:
                flow = self.env['fsm.flow'].sudo().search([
                    ('service_type_id', '=', task.service_type_id.id),
                    ('project_id', '=', task.project_id.id),
                    ('type_id', '=', task.type_id.id),
                ], limit=1)
                stage = flow['stage_ids'] and flow['stage_ids'][0] or False
                task.with_context(no_reason=True).write({
                    'flow_id': flow and flow.id or False,
                    'flow_stage_id': stage and stage.id or False,
                    'stage_id': stage and stage.stage_id.id or False,
                })

            elif (not task.flow_stage_id or task.flow_stage_id.flow_id.id != task.flow_id.id) and task.flow_id and task.flow_id.stage_ids:
                stage = task.flow_id.stage_ids[0]
                task.with_context(no_log=True, no_reason=True).write({'flow_stage_id': stage.id})

    def set_products(self):
        for task in self:
            if task.parent_id:
                for product in task.parent_id.product_ids:
                    if product.product_order_type == task.type_id.code:
                        product.copy({'task_id': task.id})

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.product_lot_id = False

    @api.onchange('merchant_id')
    def onchange_merchant_id(self):
        self.merchant_service_id = self.merchant_id.id

    def action_view_partner_tickets(self):
        is_admin = self.env.user.has_group('fsm.group_administrator')
        action = self.env.ref('sla.action_ticket').sudo().read()[0]
        action['context'] = {'create': False, 'edit': is_admin, 'delete': False}
        action['domain'] = [('id', 'in', self.partner_ticket_ids.ids)]
        return action

    def action_view_user_tickets(self):
        is_admin = self.env.user.has_group('fsm.group_administrator')
        action = self.env.ref('sla.action_ticket').sudo().read()[0]
        action['context'] = {'create': False, 'edit': is_admin, 'delete': False}
        action['domain'] = [('id', 'in', self.user_ticket_ids.ids)]
        return action

    def action_view_team_tickets(self):
        is_admin = self.env.user.has_group('fsm.group_administrator')
        action = self.env.ref('sla.action_ticket').sudo().read()[0]
        action['context'] = {'create': False, 'edit': is_admin, 'delete': False}
        action['domain'] = [('id', 'in', self.team_ticket_ids.ids)]
        return action

    def action_view_pickings(self):
        is_admin = self.env.user.has_group('fsm.group_administrator')
        action = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
        action['context'] = {'create': False, 'edit': is_admin, 'delete': False}
        action['domain'] = [('fsm_task_id', '=', self.id)]
        return action

    def action_view_deliveries(self):
        is_admin = self.env.user.has_group('fsm.group_administrator')
        action = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
        action['context'] = {'create': False, 'edit': is_admin, 'delete': False}
        action['domain'] = [('fsm_task_id', '=', self.id), ('carrier_id', '!=', False)]
        return action

    def action_view_project(self):
        is_admin = self.env.user.has_group('fsm.group_administrator')
        action = self.env.ref('fsm.action_project').sudo().read()[0]
        action['context'] = {'create': False, 'edit': is_admin, 'delete': False}
        action['res_id'] = self.project_id.id
        action['views'] = [(False, 'form')]
        return action

    def action_view_flow(self):
        is_admin = self.env.user.has_group('fsm.group_administrator')
        action = self.env.ref('fsm.action_flow').sudo().read()[0]
        action['context'] = {'create': False, 'edit': is_admin, 'delete': False}
        action['res_id'] = self.flow_id.id
        action['views'] = [(False, 'form')]
        return action

    def action_view_task(self):
        action = self.env.ref('fsm.action_task').sudo().read()[0]
        action['context'] = {'create': False, 'delete': False}
        action['res_id'] = self.parent_id.id
        action['views'] = [(False, 'form')]
        return action

    def action_view_subtask(self):
        action = self.env.ref('fsm.action_task').sudo().read()[0]
        action['context'] = {'create': False, 'delete': False}
        action['domain'] = [('id', 'in', self.child_ids.ids)]
        #action['views'] = [(False, 'form')]
        return action

    def action_view_appointments(self):
        action = self.env.ref('fsm.action_appointment').sudo().read()[0]
        action['context'] = {'default_task_id': self.id, 'create': True, 'delete': True}
        action['domain'] = [('task_id', '=', self.id)]
        return action

    def action_view_todos(self):
        action = self.env.ref('fsm.action_task_todo').sudo().read()[0]
        action['domain'] = [('task_id', '=', self.id)]
        return action

    def action_update_todos(self):
        todos = self.env['fsm.task.todo'].sudo()
        for task in self.sudo():
            creates = []
            deletes = []

            todo_ids = todos.search([('task_id', '=', task.id), ('flow_stage_id', '=', task.flow_stage_id.id)]).mapped('todo_id').ids
            if task.flow_stage_id:
                for todo in task.flow_stage_id.todo_ids:
                    if todo.id in todo_ids:
                        todo_ids.remove(todo.id)
                    else:
                        creates.append({
                            'name': todo.name,
                            'todo_id': todo.id,
                            'task_id': task.id,
                        })
            for todo in todo_ids:
                deletes.append(todo)

            todos.create(creates)
            todos.browse(deletes).unlink()

    def action_change_stage(self):
        if not self.env.user.has_group('fsm.group_manager'):
            raise AccessDenied(_('Only managers can change stage manually!'))

        if len(self.mapped('flow_id')) > 1:
            raise UserError(_('You can only change stage of tasks which has same flow.'))

        action = self.env.ref('fsm.action_stage_change').sudo().read()[0]
        action['context'] = {'default_task_ids': [(6, 0, self.ids)]}
        return action

    def action_change_reason(self):
        if not self.mapped('flow_stage_id.reason_ids'):
            raise AccessDenied(_('There is not any reason to set for this stage!'))

        if len(self.mapped('flow_stage_id')) > 1:
            raise UserError(_('You can only change stage of tasks which has same stage.'))

        action = self.env.ref('fsm.action_reason_change').sudo().read()[0]
        action['context'] = {'default_task_ids': [(6, 0, self.ids)]}
        return action

    def action_change_service_type(self):
        action = self.env.ref('fsm.action_task_service_change').sudo().read()[0]
        action['context'] = {'default_task_ids': [(6, 0, self.ids)]}
        return action

    def action_assign_user(self):
        if not self.env.user.has_group('fsm.group_manager'):
            for task in self:
                exception = True
                teams = task.service_zone_id.team_ids
                for team in teams:
                    if self.env.user.id == team.user_id.id or self.env.user.id in team.fsm_user_ids.ids:
                        exception = False
                        break

                if exception:
                    if len(self) > 1:
                        raise AccessDenied(_('You are not allowed to assign user to task #%s.') % task.uid)
                    else:
                        raise AccessDenied(_('You are not allowed to assign user to this task.'))

        action = self.env.ref('fsm.action_task_user_assign').sudo().read()[0]
        action['context'] = {'active_ids': self.ids}
        return action


class FsmTaskTodo(models.Model):
    _name = 'fsm.task.todo'
    _description = 'Field Service Management: Task Todos'
    _order = 'sequence'

    def _compute_disabled(self):
        for todo in self:
            todo.disabled = todo.photo_ok and not todo.fulfilled

    @api.depends('photo_ids', 'picking_location_type', 'picking_product_lot_id', 'picking_product_lot_ok')
    def _compute_fulfilled(self):
        for todo in self:
            fulfilled = True
            if todo.photo_ok:
                fulfilled = fulfilled and bool(len(todo.photo_ids))
            if todo.picking_ok and not (todo.picking_location_id and todo.picking_location_dest_id):
                fulfilled = fulfilled and bool(todo.picking_location_type) and (bool(todo.picking_product_lot_id) if todo.picking_product_lot_ok else True)
            todo.fulfilled = fulfilled

    def _compute_types(self):
        for todo in self:
            types = todo.todo_id.action_ids.mapped('type')
            todo.photo_ok = 'photo' in types
            todo.picking_ok = 'picking' in types

    def _compute_photo_ids(self):
        for todo in self:
            photos = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', todo._name),
                ('res_id', '=', todo.id),
            ])
            todo.photo_ids = photos.ids

    @api.depends('task_id.product_ids.product_id')
    def _compute_picking_product(self):
        for todo in self:
            product_id, product_tracking, lot_id = False, False, False
            action = todo.todo_id.action_ids.filtered(lambda a: a.type == 'picking' and a.picking_product_type)
            if action:
                if action[0].picking_product_id:
                    product_id = action[0].picking_product_id.id
                    product_tracking = action[0].picking_product_id.tracking
                    lot_id = todo.picking_product_lot_id_raw
                else:
                    product = todo.task_id.product_ids.filtered(lambda p: p.product_type == action[0].picking_product_type)
                    if product:
                        product_id = product[0].product_id.id
                        product_tracking = product[0].product_id.tracking
                        lot_id = product[0].product_lot_id.id or todo.picking_product_lot_id_raw

            else:
                product_id = todo.task_id.product_id.id
                product_tracking = todo.task_id.product_id.tracking
                lot_id = todo.task_id.product_lot_id.id or todo.picking_product_lot_id_raw

            todo.picking_product_id = product_id
            todo.picking_product_lot_id = lot_id
            todo.picking_product_lot_read = lot_id
            todo.picking_product_lot_ok = product_tracking in ('serial', 'lot')

    @api.depends('picking_location_type')
    def _compute_picking_product_lot(self):
        for todo in self:
            lot_ids = False
            action = todo.todo_id.action_ids.filtered(lambda a: a.type == 'picking')
            picking_code = action and action[0].picking_type_id.code or False
            if picking_code == 'outgoing' or picking_code == 'internal':
                domain = [
                    ('product_id', '=', todo.picking_product_id.id),
                    ('reserved_quantity', '=', 0),
                    ('quantity', '>', 0),
                ]
                if todo.picking_location_id:
                    domain += [('location_id', '=', todo.picking_location_id.id)]
                else:
                    domain += [
                        ('location_id.fsm_user_id', '=', todo.task_id.user_id.id),
                        ('location_id.fsm_user_type', '=', todo.picking_location_type),
                        ('location_id.warehouse_id', 'in', todo.task_id.project_id.warehouse_ids.ids),
                    ]
                flag = False
                exist = False
                if todo.task_id.product_ids:
                    products = todo.task_id.product_ids.filtered(lambda p: p.product_id.id == todo.picking_product_id.id)
                    if products:
                        exist = True
                        product = products[0]
                        if product.product_lot_id and product.product_subpartner:
                            if product.product_subpartner == product.product_lot_id.fsm_subpartner_id.name:
                                flag = True
                                domain += [('lot_id', '=', product.product_lot_id.id)]
                        elif product.product_lot_id and not product.product_subpartner:
                            pass
                        elif not product.product_lot_id and product.product_subpartner:
                            flag = True
                            domain += [('lot_id', '!=', False), ('lot_id.fsm_subpartner_id.name', '=', product.product_subpartner)]
                        elif not product.product_lot_id and not product.product_subpartner:
                            flag = True
                            domain += [('lot_id', '!=', False), ('lot_id.fsm_subpartner_id', '=', False)]

                if exist and not flag:
                    domain = [('id', '=', 0)]

                lots = self.env['stock.quant'].sudo().search(domain).mapped('lot_id')
                lot_ids = lots.ids

            elif picking_code == 'incoming':
                domain = [
                    ('product_id', '=', todo.picking_product_id.id),
                ]
                if todo.picking_location_dest_id:
                    domain += [('location_id', '=', todo.picking_location_dest_id.id)]
                else:
                    domain += [
                        ('location_id.usage', '=', 'customer'),
                        ('location_id.warehouse_id', 'in', todo.task_id.project_id.warehouse_ids.ids)
                    ]
                flag = False
                exist = False
                if todo.task_id.product_ids:
                    products = todo.task_id.product_ids.filtered(lambda p: p.product_id.id == todo.picking_product_id.id)
                    if products:
                        exist = True
                        product = products[0]
                        if product.product_lot_id and product.product_subpartner:
                            if product.product_subpartner == product.product_lot_id.fsm_subpartner_id.name:
                                flag = True
                                domain += [('lot_id', '=', product.product_lot_id.id)]
                        elif product.product_lot_id and not product.product_subpartner:
                            pass
                        elif not product.product_lot_id and product.product_subpartner:
                            pass
                        elif not product.product_lot_id and not product.product_subpartner:
                            flag = True
                            domain += [('lot_id', '!=', False), ('lot_id.fsm_subpartner_id', '=', False)]

                if exist and not flag:
                    domain = [('id', '=', 0)]

                lots = self.env['stock.quant'].sudo().search(domain).mapped('lot_id')
                lots |= todo.picking_product_lot_read
                lot_ids = lots.ids

            todo.picking_product_lot_ids = lot_ids

    def _compute_picking_location(self):
        for todo in self:
            action = todo.todo_id.action_ids.filtered(lambda a: a.type == 'picking')
            if action:
                src_id = action[0].picking_location_id.id
                dest_id = action[0].picking_location_dest_id.id
            else:
                src_id = False
                dest_id = False

            todo.picking_location_id = src_id
            todo.picking_location_dest_id = dest_id

    def _compute_picking_ids(self):
        for todo in self:
            pickings = self.env['stock.picking'].sudo().search([
                ('state', '!=', 'cancel'),
                ('fsm_task_todo_id', '=', todo.id),
            ])
            todo.picking_ids = pickings.ids

            state = 0
            if pickings:
                if any(picking.state == 'done' for picking in pickings):
                    state += 1
                if any(picking.state not in ('done', 'cancel') for picking in pickings):
                    state += 2
            todo.picking_state = state

    def _set_picking_product(self):
        for todo in self:
            todo.picking_product_lot_id_raw = todo.picking_product_lot_id.id

    task_id = fields.Many2one('fsm.task', ondelete='cascade')
    flow_stage_id = fields.Many2one('fsm.flow.stage', related='todo_id.stage_id', store=True)
    sequence = fields.Integer(related='todo_id.sequence', store=True)
    name = fields.Char()
    done = fields.Boolean()
    automated = fields.Boolean()
    required = fields.Boolean(related='todo_id.required', store=True)
    fulfilled = fields.Boolean(compute='_compute_fulfilled')
    disabled = fields.Boolean(compute='_compute_disabled')
    todo_id = fields.Many2one('fsm.flow.stage.todo', string='Todo', ondelete='set null', readonly=True, index=True, domain='[("id", "in", parent.todo_ids)]')
    photo_ids = fields.Many2many('ir.attachment', compute='_compute_photo_ids', string='Photos')
    photo_ok = fields.Boolean(compute='_compute_types')
    picking_ok = fields.Boolean(compute='_compute_types')
    picking_location_type = fields.Selection([
        ('solid', 'Solid'),
        ('faulty', 'Faulty'),
        ('repair', 'Repair'),
    ], string='Stock Location Type')
    picking_location_id = fields.Many2one('stock.location', compute='_compute_picking_location')
    picking_location_dest_id = fields.Many2one('stock.location', compute='_compute_picking_location')
    picking_product_id = fields.Many2one('product.product', compute='_compute_picking_product')
    picking_product_lot_ok = fields.Boolean(compute='_compute_picking_product')
    picking_product_lot_read = fields.Many2one('stock.lot', compute='_compute_picking_product')
    picking_product_lot_ids = fields.Many2many('stock.lot', compute='_compute_picking_product_lot')
    picking_product_lot_id = fields.Many2one('stock.lot', domain='[("id", "in", picking_product_lot_ids)]', compute='_compute_picking_product', inverse='_set_picking_product')
    picking_product_lot_id_raw = fields.Many2one('stock.lot')
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids', string='Pickings')
    picking_state = fields.Integer(compute='_compute_picking_ids')

    @api.onchange('picking_location_type')
    def onchange_picking_location_type(self):
        self.picking_product_lot_id = False

    def action_toggle(self):
        if self.fulfilled:
            self.done = not self.done
            self.task_id._compute_is_all_todo_done()
            if not self.automated and self.done:
                self.todo_id._run_action(self.task_id)
                self.env['fsm.flow.stage.auto'].run_todos(self.task_id.id, self.todo_id.id)
                #self.automated = True

    def action_photo(self):
        return {'type': 'fsm.file'}

    def action_picking_return(self):
        for picking in self.picking_ids:
            p = self.env['stock.return.picking'].sudo().create({'picking_id': picking.id})
            p._onchange_picking_id()
            np, pti = p._create_returns()
            npicking = picking.browse(np)
            for move in npicking.sudo().move_ids:
                move.write({'quantity': move.product_uom_qty})
            if self.picking_product_lot_id:
                for line in npicking.move_line_ids:
                    line.write({'lot_id': self.picking_product_lot_id.id})
            npicking.button_validate()
            (picking | npicking).write({'state': 'cancel'})
        self.write({'done': False, 'picking_product_lot_id': False})
        self.task_id.product_ids.filtered(lambda p: p.todo_id.id == self.id and p.product_lot_id and p.product_id.id == self.picking_product_id.id).write({'product_lot_id': False})

    def action_picking_cancel(self):
        self.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')).action_cancel()
        self.write({'done': False, 'picking_product_lot_id': False})
        self.task_id.product_ids.filtered(lambda p: p.todo_id.id == self.id and p.product_lot_id and p.product_id.id == self.picking_product_id.id).write({'product_lot_id': False})
    
    def get_metadata(self):
        action = self.todo_id.action_ids.filtered(lambda a: a.type == 'photo')
        if action:
            return {'type': action[0]['file_type'] or None, 'size': action[0]['file_size'] or None}
        return {'type': None, 'size': None}

    def unlink_fsm_file(self):
        if not self.fulfilled and not self.task_id.stage_type == '2':
            self.done = False

    def write(self, values):
        res = super().write(values)
        if 'done' in values:
            for todo in self:
                if todo.done and todo.fulfilled:
                    if not todo.automated:
                        todo.env['fsm.flow.stage.auto'].run_todos(todo.task_id.id, todo.todo_id.id)
                        #todo.automated = True

                if todo.done:
                    for action in todo.todo_id.action_ids:
                        context = {}
                        if action.type == 'picking' and not todo.picking_ids and (todo.picking_location_id and todo.picking_location_dest_id or todo.picking_location_type):
                            user = todo.task_id.user_id
                            if not user and not (todo.picking_location_id and todo.picking_location_dest_id):
                                raise UserError(_('Please assign a user to this task before continuing.'))

                            context.update({
                                'force': True,
                                'values_stock_picking': {},
                                'values_stock_move': {},
                                'values_stock_move_line': {},
                            })

                            if action.picking_location_id:
                                location_id = action.picking_location_id
                            else:
                                location_id = self.env['stock.location'].sudo().search([
                                    ('fsm_user_id', '=', user.id),
                                    ('fsm_user_type', '=', todo.picking_location_type),
                                ], limit=1)

                            if action.picking_location_dest_id:
                                location_dest_id = action.picking_location_dest_id
                            else:
                                location_dest_id = self.env['stock.location'].sudo().search([
                                    ('fsm_user_id', '=', user.id),
                                    ('fsm_user_type', '=', todo.picking_location_type),
                                ], limit=1)

                            if todo.picking_product_lot_id:
                                context['values_stock_move_line'].update({'lot_id': todo.picking_product_lot_id.id})
                            if todo.picking_product_id:
                                context['values_stock_move'].update({
                                    'product_id': todo.picking_product_id.id,
                                    'name': todo.picking_product_id.name,
                                })
                            if location_id:
                                context['values_stock_picking'].update({'location_id': location_id.id})
                                context['values_stock_move'].update({'location_id': location_id.id})
                            if location_dest_id:
                                context['values_stock_picking'].update({'location_dest_id': location_dest_id.id})
                                context['values_stock_move'].update({'location_dest_id': location_dest_id.id})

                        todo.todo_id.with_context(**context)._run_action(todo.task_id, todo=todo, actions=action)
                    todo.task_id._compute_is_all_todo_done()
        return res


class FsmTaskProduct(models.Model):
    _name = 'fsm.task.product'
    _description = 'Field Service Management: Task Products'
    _inherit = ['mail.thread']

    task_id = fields.Many2one('fsm.task', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', index=True, tracking=True, domain="[('id', 'in', domain_product)]")
    product_lot_id = fields.Many2one('stock.lot', string='Product Lot/Serial', index=True, tracking=True, domain="[('product_id', '=', product_id)]")
    product_lot_ref = fields.Char(related='product_lot_id.ref', string='Product Lot/Serial Reference', tracking=True, store=True)
    product_owner = fields.Char(string='Product Owner', tracking=True)
    product_state = fields.Selection([
        ('examining', 'Examining'),
        ('solid', 'Solid'),
        ('faulty', 'Faulty'),
        ('scrap', 'Scrap'),
    ], string='Product State', tracking=True)
    product_os = fields.Char(string='Product Operating System', tracking=True)
    product_type = fields.Char(string='Product Type', tracking=True)
    product_order_type = fields.Char(string='Product Order Type', tracking=True)
    product_operation_type = fields.Char(string='Product Operation Type', tracking=True)
    product_subpartner = fields.Char(string='Product Subpartner', tracking=True)
    product_operator = fields.Char(string='Product Operator', tracking=True)
    todo_id = fields.Many2one('fsm.task.todo')
    domain_product = fields.Many2many(related='task_id.project_id.product_ids')

    def _compute_name(self):
        for task_product in self:
            if task_product.product_id:
                task_product.name = task_product.product_id.name
            else:
                task_product.name = 'TASK PRODUCT #%s' % task_product.id


class FsmTaskSetupApplication(models.Model):
    _name = 'fsm.task.setup.application'
    _description = 'Field Service Management: Task Setup Applications'

    task_id = fields.Many2one('fsm.task', ondelete='cascade')
    name = fields.Char('Name')
    description = fields.Char('Description')
    version = fields.Char('Version')


class FsmTaskDocumentDetail(models.Model):
    _name = 'fsm.task.document.detail'
    _description = 'Field Service Management: Task Document Detail Informations'

    task_id = fields.Many2one('fsm.task', ondelete='cascade')
    name = fields.Char('Key')
    value = fields.Char('Value')


class FsmTaskLog(models.Model):
    _name = 'fsm.task.log'
    _description = 'Field Service Management: Task Logs'
    _order = 'id'
 
    task_id = fields.Many2one('fsm.task', ondelete='cascade')
    stage_id = fields.Many2one('fsm.flow.stage')
    stage_type = fields.Selection(related='stage_id.stage_id.type')
    date_from = fields.Datetime(string='Start Date')
    date_to = fields.Datetime(string='End Date')
    approval_state = fields.Selection([('0', 'Approved'), ('1', 'Rejected')], string='Approval State')
    approval_date = fields.Datetime(string='Approval Date')
    approval_code = fields.Char(string='Approval Code')
    approval_desc = fields.Char(string='Approval Description')
    reason_id = fields.Many2one('fsm.reason')
    reason_code = fields.Char(string='Reason Code')
    reason_name = fields.Char(string='Reason Name')
    reason_desc = fields.Text(string='Reason Description')

    def set_date_from(self, date=None):
        if not self.date_from:
            self.sudo().write({'date_from': date or fields.Datetime.now()})

    def set_date_to(self, date=None):
        if not self.date_to:
            self.sudo().write({'date_to': date or fields.Datetime.now()})
