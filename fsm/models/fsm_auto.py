# -*- coding: utf-8 -*-
import ast
from pytz import timezone
from datetime import datetime
from dateutil.relativedelta import relativedelta

from .. import ReasonError, AppointmentError
from odoo import models, fields, api, tools, Command, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval, test_python_expr


class FsmAuto(models.Model):
    _name = 'fsm.auto'
    _description = 'Field Service Management: Automation'
    _order = 'sequence'

    @api.depends('trigger')
    def _compute_name(self):
        triggers = dict(self._fields['trigger'].selection)
        for auto in self:
            auto.name = _(triggers.get(auto.trigger))

    @api.depends('active')
    def _compute_model(self):
        for auto in self:
            auto.model = 'fsm.task'

    name = fields.Char(compute='_compute_name')
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    trigger = fields.Selection([
        ('field', 'On update of fields'),
        ('todo', 'On completion of todos'),
        ('picking', 'On progress of stock moves'),
        ('activity', 'On change of activities'),
        ('create', 'On creation'),
        ('cron', 'On timed condition'),
        ('barcode', 'On opened by barcode scanner'),
    ], required=True, default='field')
    filter = fields.Text()
    description = fields.Text()
    model = fields.Char(compute='_compute_model')
    project_id = fields.Many2one('fsm.project', string='Project', ondelete='cascade')
    type_id = fields.Many2one('fsm.type', string='Type', ondelete='cascade', required=True, copy=True)
    field_ids = fields.One2many('fsm.auto.field', 'auto_id', string='Fields', copy=True)
    activity_ids = fields.One2many('fsm.auto.activity', 'auto_id', string='Activities', copy=True)
    picking_ids = fields.One2many('fsm.auto.picking', 'auto_id', string='Pickings', copy=True)
    cron_ids = fields.One2many('fsm.auto.cron', 'auto_id', string='Schedules', copy=True)
    action_ids = fields.One2many('fsm.auto.action', 'auto_id', string='Actions', copy=True)
    todo_ids = fields.Many2many('fsm.todo', 'fsm_auto_todo_rel', 'auto_id', 'todo_id', string='Todos', copy=True)
    todo_all = fields.Boolean(string='All Todos')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model
    def _get_task(self, task_id, domain):
        domain = ast.literal_eval(domain) if domain else []
        domain.insert(0, ['id', '=', task_id])
        return self.env['fsm.task'].sudo().search(domain, limit=1)

    @api.model
    def _run_action(self, auto, task):
        self = self.sudo()
        auto = auto.sudo()
        task = task.sudo()
        for action in auto.action_ids:

            if action.type == 'code':
                if action.code:
                    context = {
                        'env': self.env,
                        'uid': self._uid,
                        'user': self.env.user,
                        'time': tools.safe_eval.time,
                        'datetime': tools.safe_eval.datetime,
                        'dateutil': tools.safe_eval.dateutil,
                        'timezone': timezone,
                        'task': task,
                        'Command': Command,
                        'UserError': UserError,
                    }
                    safe_eval(action.code.strip(), context, mode='exec')
                    if 'action' in context:
                        return context

            elif action.type == 'email':
                template = action.mail_template_id
                if not template:
                    continue
                #email_values = {}
                task.message_post_with_template(template.id)#, email_values=email_values)

            elif action.type == 'sms':
                template = action.sms_template_id
                if not template:
                    continue
                task._message_sms_with_template(template)

            elif action.type == 'activity':
                activity_type = action.activity_type_id
                if not activity_type:
                    continue
                model_id = self.env['ir.model']._get_id('fsm.task')
                activity = self.env['mail.activity'].create({
                    'res_id': task.id,
                    'res_model_id': model_id,
                    'activity_type_id': activity_type.id,
                })
                activity._onchange_activity_type_id()
                activity.write({
                    'summary': action.activity_summary,
                })

            elif action.type == 'stage':
                if action.stage_type == '2':
                    task.with_context(no_reason=True).write({
                        'flow_stage_id': action.flow_stage_id.id,
                        'reason_id': action.reason_id.id,
                        'close_success': action.stage_success,
                        'close_date': fields.Datetime.now(),
                        'close_done': True,
                    })
                else:
                    def create_appointment():
                        date_now = fields.Datetime.now()
                        date_period = action.stage_appointment_date_period or 'days'
                        date_value = action.stage_appointment_date_value or 0
                        date = date_now + relativedelta(**{date_period: date_value})
                        if date_period != 'hours':
                            date_tz = timezone('Europe/Istanbul')
                            date_offset = date_tz.utcoffset(date_now)
                            date_max = datetime.combine(date, datetime.max.time())
                            date = date_max - date_offset
                        self.env['fsm.appointment'].create({'task_id': task.id, 'date': date})

                    try:
                        task.with_context(**{
                            'default_stage_success': action.stage_success,
                            'default_reason_id': action.reason_id,
                            'default_reason_desc': action.reason_desc,
                        }).write({
                            'flow_stage_id': action.flow_stage_id.id,
                        })
                    except ReasonError:
                        try:
                            task.with_context(no_reason=True).write({
                                'flow_stage_id': action.flow_stage_id.id,
                                'reason_id': action.reason_id.id, 
                            })
                        except AppointmentError:
                            create_appointment()
                            task.with_context(no_reason=True, no_appointment=True).write({
                                'flow_stage_id': action.flow_stage_id.id,
                                'reason_id': action.reason_id.id, 
                            })
                    except AppointmentError:
                        create_appointment()
                        task.with_context(no_reason=True, no_appointment=True).write({
                            'flow_stage_id': action.flow_stage_id.id,
                            'reason_id': action.reason_id.id, 
                        })

            elif action.type == 'picking':
                picking_values = task._prepare_picking_values(action=action)
                picking = self.env['stock.picking'].sudo().create(picking_values)
                picking.action_assign()
                if not task.flow_id.misc_use_material_product:
                    for line in picking.move_line_ids:
                        line.write({'lot_id': task.product_lot_id.id})
                if action.picking_done:
                    for move in picking.move_ids:
                        move.write({'quantity': move.product_uom_qty})
                    picking.button_validate()

            elif action.type == 'action':
                active_ids = task.ids
                active_id = active_ids[0]
                context = {
                    'active_id': active_id,
                    'active_ids': active_ids,
                    'active_model': task._name,
                }
                result = action.action_id.with_context(**context).run()
                if result:
                    return {'action': result}

        return {}

    @api.model
    def run_creates(self, tasks):
        if not tasks:
            return True

        for t in tasks:
            autos = t.mapped('flow_stage_id.auto_ids').filtered(lambda a: a.trigger == 'create')
            if not autos:
                continue
            for auto in autos:
                task = self._get_task(t.id, auto.filter)
                if not task:
                    continue
                self._run_action(auto, task)
        return True

    @api.model
    def run_fields(self, values):
        for key, value in values.items():
            if not value['flow'] or not value['stage']:
                continue

            self.env.cr.execute(f'''
                SELECT
                    a.id,
                    a.filter,
                    imf.name AS field,
                    f.field_type AS type,
                    f.value_prev_any AS prevany,
                    f.value_next_any AS nextany,
                    (CASE WHEN f.field_type = 'many2one' THEN f.value_prev_raw ELSE value_prev END) AS prev,
                    (CASE WHEN f.field_type = 'many2one' THEN f.value_next_raw ELSE value_next END) AS next
                FROM fsm_flow_stage_auto a
                JOIN fsm_flow_stage s ON s.id = a.stage_id
                JOIN fsm_auto_field f ON f.flow_stage_auto_id = a.id
                JOIN ir_model_fields imf ON f.field_id = imf.id
                WHERE a.active IS TRUE
                AND a.trigger = 'field'
                AND a.stage_id = {value['stage']}
                AND s.flow_id = {value['flow']}
                ORDER BY a.sequence, a.id
            ''')
            result = self.env.cr.dictfetchall()
            autos = {}
            filters = {}
            for res in result:
                if res['field'] not in value['value']:
                    continue

                value_prev = res['prev']
                value_next = res['next']

                if res['type'] in ('integer', 'many2one'):
                    value_prev = value_prev and int(value_prev) or False
                    value_next = value_next and int(value_next) or False
                elif res['type'] == 'boolean':
                    value_prev = value_prev == '1'
                    value_next = value_next == '1'

                if res['prevany']:
                    value_prev = None
                if res['nextany']:
                    value_next = None

                if res['id'] not in autos:
                    autos[res['id']] = {}
                autos[res['id']][res['field']] = {'prev': value_prev, 'next': value_next}
                filters[res['id']] = res['filter']

            for aid, val in autos.items():
                valid = True
                for k, v in val.items():
                    if v['prev'] is not None and v['prev'] != value['prev'][k]:
                        valid = False
                        break
                    if v['next'] is not None and v['next'] != value['next'][k]:
                        valid = False
                        break
                if valid:
                    task = self._get_task(key, filters[aid])
                    if not task:
                        continue
                    auto = self.browse(aid)
                    self._run_action(auto, task)
        return True

    @api.model
    def run_todos(self, task_id, todo_id):
        state = False
        self.env.cr.execute(f'SELECT project_id, type_id FROM fsm_task WHERE id = {task_id or 0}')
        result = self.env.cr.fetchone()
        if not result:
            return

        project_id, type_id = result
        self.env.cr.execute(f'''
            SELECT
                a.id,
                a.filter
            FROM fsm_flow_stage_auto a
            JOIN fsm_auto_todo_rel at ON at.auto_id = a.id
            JOIN fsm_flow_stage_todo t ON at.todo_id = t.id
            WHERE a.active IS TRUE
            AND a.trigger = 'todo'
            AND a.todo_all IS NOT TRUE
            AND a.project_id = {project_id or 0}
            AND a.type_id = {type_id or 0}
            AND t.id = {todo_id or 0}
            ORDER BY a.sequence, a.id
        ''')
        result = self.env.cr.dictfetchall()
        if result:
            for res in result:
                task = self._get_task(task_id, res['filter'])
                if not task:
                    continue
                auto = self.browse(res['id'])
                self._run_action(auto, task)
                state = True
        return state

    @api.model
    def run_todos_all(self, task_id, auto_ids):
        if not auto_ids:
            return True

        self.env.cr.execute(f'''
            SELECT
                a.id,
                a.filter
            FROM fsm_flow_stage_auto a
            WHERE a.active IS TRUE
            AND a.id IN ({','.join(map(str, auto_ids))})
            ORDER BY a.sequence, a.id
        ''')
        result = self.env.cr.dictfetchall()
        autos = []
        filters = {}
        for res in result:
            autos.append(res['id'])
            filters[res['id']] = res['filter']

        for aid in autos:
            task = self._get_task(task_id, filters[aid])
            if not task:
                continue
            auto = self.browse(aid)
            self._run_action(auto, task)
        return True

    @api.model
    def run_pickings(self, task_id, auto_ids, values):
        if not auto_ids:
            return True

        self.env.cr.execute(f'''
            SELECT
                a.id,
                a.filter,
                imf.name AS field,
                f.field_type AS type,
                (CASE WHEN f.field_type = 'selection' THEN f.value_raw ELSE f.value END) AS value
            FROM fsm_flow_stage_auto a
            JOIN fsm_auto_picking f ON f.flow_stage_auto_id = a.id
            JOIN ir_model_fields imf ON f.field_id = imf.id
            WHERE a.active IS TRUE
            AND a.id IN ({','.join(map(str, auto_ids))})
            ORDER BY a.sequence, a.id
        ''')
        result = self.env.cr.dictfetchall()
        autos = {}
        filters = {}
        for res in result:
            value = res['value']
            if res['type'] in ('integer', 'many2one'):
                value = int(value)
            elif res['type'] == 'boolean':
                value = value == '1'

            if res['id'] not in autos:
                autos[res['id']] = {}
            autos[res['id']][res['field']] = {'value': value}
            filters[res['id']] = res['filter']

        for aid, val in autos.items():
            valid = True
            for k, v in val.items():
                if k not in values or values[k] != v['value']:
                    valid = False
                    break
            if valid:
                task = self._get_task(task_id, filters[aid])
                if not task:
                    continue
                auto = self.browse(aid)
                self._run_action(auto, task)
        return True

    @api.model
    def run_barcodes(self, task_id, auto_ids):
        if not auto_ids:
            return True

        self.env.cr.execute(f'''
            SELECT
                a.id,
                a.filter
            FROM fsm_flow_stage_auto a
            WHERE a.active IS TRUE
            AND a.id IN ({','.join(map(str, auto_ids))})
            ORDER BY a.sequence, a.id
        ''')
        result = self.env.cr.dictfetchall()
        autos = []
        filters = {}
        for res in result:
            autos.append(res['id'])
            filters[res['id']] = res['filter']

        for aid in autos:
            task = self._get_task(task_id, filters[aid])
            if not task:
                continue
            auto = self.browse(aid)
            self._run_action(auto, task)
        return True

    @api.model
    def run_activities(self, task_id, activity_id, trigger):
        state = False
        self.env.cr.execute(f'SELECT project_id, type_id FROM fsm_task WHERE id = {task_id}')
        result = self.env.cr.fetchone()
        if not result:
            return

        project_id, type_id = result
        self.env.cr.execute(f'''
            SELECT
                a.id,
                a.filter
            FROM fsm_flow_stage_auto a
            JOIN fsm_auto_activity ac ON ac.flow_stage_auto_id = a.id
            WHERE a.active IS TRUE
            AND a.trigger = 'activity'
            AND a.project_id = {project_id}
            AND a.type_id = {type_id}
            AND ac.activity_id = {activity_id}
            AND ac.trigger = '{trigger}'
            ORDER BY a.sequence, a.id
        ''')
        result = self.env.cr.dictfetchall()
        if result:
            for res in result:
                task = self._get_task(task_id, res['filter'])
                if not task:
                    continue
                auto = self.browse(res['id'])
                self._run_action(auto, task)
                state = True
        return state

    def run_cron(self):
        pass
        return
        self.env.cr.execute(f'''
            SELECT
                a.id,
                a.filter
            FROM fsm_flow_stage_auto a
            JOIN fsm_auto_cron cr ON cr.flow_stage_auto_id = a.id
            WHERE a.active IS TRUE
            AND a.trigger = 'cron'
            AND a.project_id IS NOT NULL
            AND a.project_id IS NOT FALSE 
            AND ac.activity_id = {trigger}
            AND ac.trigger = '{trigger}'
            ORDER BY a.sequence, a.id
        ''')


class FsmAutoField(models.Model):
    _name = 'fsm.auto.field'
    _description = 'Field Service Management: Automation Fields'

    @api.depends('field_id', 'value_prev_many2one', 'value_prev_char', 'value_prev_text', 'value_prev_integer', 'value_prev_boolean')
    def _compute_value_prev(self):
        for auto in self:
            value_prev = False
            value_prev_raw = False
            if auto.field_id.ttype == 'many2one':
                value_prev = auto.value_prev_many2one and auto.value_prev_many2one.display_name or False
                value_prev_raw = auto.value_prev_many2one and auto.value_prev_many2one.id or False
            elif auto.field_id.ttype == 'char':
                value_prev = auto.value_prev_char
            elif auto.field_id.ttype == 'text':
                value_prev = auto.value_prev_text
            elif auto.field_id.ttype == 'integer':
                value_prev = auto.value_prev_integer
            elif auto.field_id.ttype == 'boolean':
                value_prev = auto.value_prev_boolean and 1
            auto.value_prev = value_prev
            auto.value_prev_raw = value_prev_raw

    @api.depends('field_id', 'value_next_many2one', 'value_next_char', 'value_next_text', 'value_next_integer', 'value_next_boolean')
    def _compute_value_next(self):
        for auto in self:
            value_next = False
            value_next_raw = False
            if auto.field_id.ttype == 'many2one':
                value_next = auto.value_next_many2one and auto.value_next_many2one.display_name or False
                value_next_raw = auto.value_next_many2one and auto.value_next_many2one.id or False
            elif auto.field_id.ttype == 'char':
                value_next = auto.value_next_char
            elif auto.field_id.ttype == 'text':
                value_next = auto.value_next_text
            elif auto.field_id.ttype == 'integer':
                value_next = auto.value_next_integer
            elif auto.field_id.ttype == 'boolean':
                value_next = auto.value_next_boolean and 1 or 0
            auto.value_next = value_next
            auto.value_next_raw = value_next_raw

    @api.depends('field_id')
    def _compute_field_model_id(self):
        for auto in self:
            if auto.field_id.relation:
                auto.field_model_id = self.env['ir.model'].sudo().search([('model', '=', auto.field_id.relation)], limit=1).id
            else:
                auto.field_model_id = False

    @api.depends('field_name')    
    def _compute_name(self):
        for auto in self:
            auto.name = auto.field_name

    @api.model
    def _selection_many2one(self):
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([])]

    name = fields.Char(compute='_compute_name')
    auto_id = fields.Many2one('fsm.auto', ondelete='cascade')
    flow_stage_auto_id = fields.Many2one('fsm.flow.stage.auto', ondelete='cascade')
    field_id = fields.Many2one('ir.model.fields', string='Field', domain='[("model", "=", "fsm.task"), ("name", "not like", "field_%"), ("name", "not like", "domain_%"), ("name", "not in", ["_last_update"])]', required=True, ondelete='cascade')
    field_name = fields.Char(related='field_id.field_description', store=True)
    field_type = fields.Selection(related='field_id.ttype', store=True)
    field_model = fields.Char(related='field_id.relation', store=True)
    field_model_id = fields.Many2one('ir.model', compute='_compute_field_model_id', store=True)
    value_prev_many2one = fields.Reference(selection='_selection_many2one')
    value_next_many2one = fields.Reference(selection='_selection_many2one')
    value_prev_char = fields.Char(string='Previous Char Value')
    value_next_char = fields.Char(string='Next Char Value')
    value_prev_text = fields.Char(string='Previous Text Value')
    value_next_text = fields.Char(string='Next Text Value')
    value_prev_integer = fields.Integer(string='Previous Integer Value')
    value_next_integer = fields.Integer(string='Next Integer Value')
    value_prev_boolean = fields.Boolean(string='Previous Boolean Value')
    value_next_boolean = fields.Boolean(string='Next Boolean Value')
    value_prev_raw = fields.Char(string='Raw Previous Value', compute='_compute_value_prev', store=True)
    value_next_raw = fields.Char(string='Raw Next Value', compute='_compute_value_next', store=True)
    value_prev = fields.Char(string='Previous Value', compute='_compute_value_prev', store=True)
    value_next = fields.Char(string='Next Value', compute='_compute_value_next', store=True)
    value_prev_any = fields.Boolean(string='Previous Any Value')
    value_next_any = fields.Boolean(string='Next Any Value')

    @api.onchange('value_prev_any')
    def onchange_value_prev_any(self):
        self.update({
            'value_prev_many2one': False,
            'value_prev_boolean': False,
            'value_prev_char': False,
            'value_prev_text': False,
            'value_prev_raw': False,
            'value_prev': False,
        })

    @api.onchange('value_next_any')
    def onchange_value_next_any(self):
        self.update({
            'value_next_many2one': False,
            'value_next_boolean': False,
            'value_next_char': False,
            'value_next_text': False,
            'value_next_raw': False,
            'value_next': False,
        })


class FsmAutoActivity(models.Model):
    _name = 'fsm.auto.activity'
    _description = 'Field Service Management: Automation Activities'

    auto_id = fields.Many2one('fsm.auto', ondelete='cascade')
    flow_stage_auto_id = fields.Many2one('fsm.flow.stage.auto', ondelete='cascade')
    activity_id = fields.Many2one('mail.activity.type', required=True)
    trigger = fields.Selection([
        ('done', 'On Done'),
        ('cancel', 'On Cancel'),
        ('expire', 'On Expire'),
    ], required=True)


class FsmAutoPickings(models.Model):
    _name = 'fsm.auto.picking'
    _description = 'Field Service Management: Automation Stock Picking Fields'

    @api.depends('field_id', 'value_selection_id')
    def _compute_value(self):
        for auto in self:
            value = False
            value_raw = False
            if auto.field_id.ttype == 'selection':
                value = auto.value_selection_id.name
                value_raw = auto.value_selection_id.value
            auto.value = value
            auto.value_raw = value_raw

    @api.depends('field_name')    
    def _compute_name(self):
        for auto in self:
            auto.name = auto.field_name

    name = fields.Char(compute='_compute_name')
    auto_id = fields.Many2one('fsm.auto', ondelete='cascade')
    flow_stage_auto_id = fields.Many2one('fsm.flow.stage.auto', ondelete='cascade')
    field_id = fields.Many2one('ir.model.fields', string='Field', domain='[("model", "=", "stock.picking"), ("name", "in", ("state", "carrier_state"))]', required=True, ondelete='cascade')
    field_name = fields.Char(related='field_id.field_description', store=True)
    field_model = fields.Char(related='field_id.relation', store=True)
    field_type = fields.Selection(related='field_id.ttype', store=True)
    value_selection_id = fields.Many2one('ir.model.fields.selection', string='Selection', ondelete='cascade', domain='[("field_id", "=", field_id)]')
    value_raw = fields.Char(string='Raw Value', compute='_compute_value', store=True)
    value = fields.Char(string='Value', compute='_compute_value', store=True)


class FsmAutoCron(models.Model):
    _name = 'fsm.auto.cron'
    _description = 'Field Service Management: Automation Scheduled Jobs'

    @api.onchange('range')
    def _compute_expr(self):
        for auto in self:
            auto.expr = auto.range and _('later')

    auto_id = fields.Many2one('fsm.auto', ondelete='cascade')
    flow_stage_auto_id = fields.Many2one('fsm.flow.stage.auto', ondelete='cascade')
    field_id = fields.Many2one('ir.model.fields', string='Field', domain='[("model", "=", "fsm.task"), ("ttype", "in", ("date", "datetime")), ("store", "=", True), ("name", "not in", ["_last_update"])]', required=True, ondelete='cascade')
    time = fields.Integer(required=True)
    range = fields.Selection([
        ('minute', 'minute(s)'),
        ('hour', 'hour(s)'),
        ('day', 'day(s)'),
        ('month', 'month(s)'),
    ], required=True)
    expr = fields.Char(compute='_compute_expr')
    task_ids = fields.Many2many('fsm.task', 'fsm_auto_cron_task_rel', 'cron_id', 'task_id', string='Tasks', copy=False)


class FsmAutoAction(models.Model):
    _name = 'fsm.auto.action'
    _description = 'Field Service Management: Automation Actions'
    _order = 'sequence'

    @api.depends('type')
    def _compute_name(self):
        types = dict(self._fields['type'].selection)
        for auto in self:
            auto.name = _(types.get(auto.type))

    @api.depends('flow_stage_auto_id.stage_id.stage_next_ids')
    def _compute_flow_stage_ids(self):
        for action in self:
            stages = action.flow_stage_auto_id.stage_id.stage_next_ids
            if not stages and action.env.context.get('stages'):
                stages = action.env['fsm.flow.stage'].browse(action.env.context['stages'])
            action.flow_stage_ids = stages

    name = fields.Char(compute='_compute_name')
    auto_id = fields.Many2one('fsm.auto', ondelete='cascade')
    flow_stage_auto_id = fields.Many2one('fsm.flow.stage.auto', ondelete='cascade')
    sequence = fields.Integer(default=10)
    type = fields.Selection([
        ('email', 'Send Email'),
        ('sms', 'Send SMS'),
        ('activity', 'Plan Activity'),
        ('stage', 'Change Stage'),
        ('picking', 'Create Picking'),
        ('action', 'Execute Action'),
        ('code', 'Run Code'),
    ], required=True, default='code')
    code = fields.Text()
    mail_template_id = fields.Many2one('mail.template')
    sms_template_id = fields.Many2one('sms.template')
    activity_type_id = fields.Many2one('mail.activity.type', string='Activity Type')
    activity_summary = fields.Text(string='Activity Summary')
    stage_id = fields.Many2one('fsm.stage', string='Stage', related='flow_stage_id.stage_id', store=True, readonly=False)
    stage_type = fields.Selection(related='stage_id.type')
    stage_code = fields.Char(related='stage_id.code')
    stage_success = fields.Boolean(string='Stage Successful', default=True)
    stage_appointment_date_period = fields.Selection([
        ('hours', 'hours'),
        ('days', 'days'),
        ('weeks', 'weeks'),
        ('months', 'months'),
        ('years', 'years'),
    ], string='Stage Appointment Date Period')
    stage_appointment_date_value = fields.Integer(string='Stage Appointment Date Value')
    reason_id = fields.Many2one('fsm.reason', string='Reason')
    reason_desc = fields.Text(string='Reason Description')
    flow_stage_id = fields.Many2one('fsm.flow.stage', string='Stage', domain='[("id", "in", flow_stage_ids)]')
    flow_stage_ids = fields.Many2many('fsm.flow.stage', compute='_compute_flow_stage_ids')
    picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type')
    picking_location_id = fields.Many2one('stock.location', string='Picking Location', domain='[("company_id", "=", picking_type_company_id)]')
    picking_location_dest_id = fields.Many2one('stock.location', string='Picking Location Destination', domain='[("company_id", "=", picking_type_company_id)]')
    picking_done = fields.Boolean(string='Picking Mark as Done')
    picking_type_company_id = fields.Many2one('res.company', related='picking_type_id.company_id')
    action_id = fields.Reference(selection=[
        ('ir.actions.report', 'Report'),
        ('ir.actions.server', 'Server'),
        ('ir.actions.client', 'Client'),
        ('ir.actions.act_url', 'Address'),
        ('ir.actions.act_window', 'Window'),
    ])

    @api.constrains('code')
    def _check_code(self):
        for action in self:
            if action.type == 'stage' and not action.stage_id:
                raise ValidationError(_('Stage field cannot be empty.'))
            elif action.type == 'picking' and not action.picking_type_id:
                raise ValidationError(_('Picking type field cannot be empty.'))
            elif action.type == 'code' and action.code:
                msg = test_python_expr(expr=action.code.strip(), mode='exec')
                if msg:
                    raise ValidationError(msg)

    @api.onchange('type')
    def onchange_type(self):
        if self.type == 'picking' and not self.picking_type_id:
            types = self.env['stock.picking.type'].sudo().search([('company_id', '=', self.env.company.id)])
            type = types.filtered(lambda t: t.code == 'internal')
            type = type[0] if type else types[0]
            self.picking_type_id = type.id

    @api.onchange('picking_type_id')
    def onchange_picking_type(self):
        if self.type == 'picking' and self.picking_type_id:
            location_customer, location_supplier = self.env['stock.warehouse']._get_partner_locations()
            self.picking_location_id = self.picking_type_id.default_location_src_id.id
            if not self.picking_location_id and self.picking_type_id.code == 'incoming':
                self.picking_location_id = location_supplier.id

            self.picking_location_dest_id = self.picking_type_id.default_location_dest_id.id
            if not self.picking_location_dest_id and self.picking_type_id.code == 'outgoing':
                self.picking_location_dest_id = location_customer.id
        else:
            self.picking_location_id = False
            self.picking_location_dest_id = False

    @api.onchange('flow_stage_id')
    def onchange_flow_stage_id(self):
        if self.flow_stage_id.stage_id.code == 'RANDEVU':
            self.stage_appointment_date_period = 'days'
            self.stage_appointment_date_value = 1
        else:
            self.stage_appointment_date_period = False
            self.stage_appointment_date_value = False
