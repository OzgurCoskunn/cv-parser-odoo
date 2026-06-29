# -*- coding: utf-8 -*-

import uuid
from pytz import timezone
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import AccessDenied, UserError

APPOINTMENT_STAGE_CODE = 'RANDEVU'


class FsmAppointment(models.Model):
    _name = 'fsm.appointment'
    _description = 'Field Service Management: Appointments'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    def _compute_name(self):
        for appointment in self:
            if appointment.uid:
                appointment.name = 'ID #%s' % appointment.uid
            else:
                appointment.name = 'TASK #%s' % appointment.id

    def _compute_valid(self):
        task_ids = {}
        for appointment in self:
            task_id = appointment.task_id.id
            if task_id not in task_ids:
                task_ids[task_id] = self.sudo().search([('task_id', '=', task_id)], limit=1).id
            appointment.valid = task_ids[task_id] == appointment.id

    def _compute_today(self):
        for appointment in self:
            appointment.today = appointment.date and appointment.date.date() == fields.Date.today()

    def _compute_photo_ids(self):
        for appointment in self:
            photos = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', appointment._name),
                ('res_id', '=', appointment.id),
            ])
            appointment.photo_ids = photos.ids

    @api.depends('task_id')
    def _compute_reason_ids(self):
        for appointment in self:
            stage = self.env.context.get('values', {}).get('flow_stage_id', 0)
            if stage:
                stage = self.env['fsm.flow.stage'].sudo().browse(stage)
            if not stage:
                stage = appointment.task_id.flow_stage_id
            appointment.reason_ids = stage.reason_ids.ids

    @api.depends_context('default_task_ids')
    def _compute_task_ids(self):
        for appointment in self:
            appointment.task_ids = self.env.context.get('default_task_ids', False)

    name = fields.Char(compute='_compute_name')
    valid = fields.Boolean(compute='_compute_valid')
    today = fields.Boolean(compute='_compute_today')
    uid = fields.Char(default=lambda self: str(uuid.uuid4()), readonly=True, copy=False)
    date = fields.Datetime('Appointment Date', required=True)
    create_date = fields.Datetime(string='Create Date')
    task_id = fields.Many2one('fsm.task', ondelete='cascade')
    task_ids = fields.Many2many('fsm.task', compute='_compute_task_ids', readonly=False)
    merchant_id = fields.Many2one(related='task_id.merchant_id')
    partner_id = fields.Many2one('res.partner', string='Contact', ondelete='restrict', domain='[("is_company", "=", False), ("parent_id", "=", merchant_id)]')
    photo_ids = fields.Many2many('ir.attachment', compute='_compute_photo_ids', string='Photos')
    document_ids = fields.Many2many('ir.attachment', 'fsm_appointment_document_rel', 'appointment_id', 'document_id', string='Documents')
    reason_id = fields.Many2one('fsm.reason', string='Reason', ondelete='restrict', domain='[("id", "in", reason_ids)]')
    reason_ids = fields.Many2many('fsm.reason', compute='_compute_reason_ids')
    reason_code = fields.Char(related='reason_id.code', string='Reason Code')
    reason_desc = fields.Text('Reason Description')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.constrains('date')
    def _check_date(self):
        for appointment in self:
            tz = timezone(self.env.context.get('tz') or self.env.user.tz or 'Europe/Istanbul')
            now = fields.Datetime.now()
            offset = tz.utcoffset(now)

            date = now + relativedelta(hours=1)
            if date > appointment.date:
                raise UserError(_('You cannot set appointment date before %s.' % (date + offset).strftime('%d/%m/%Y %H:%M:%S')))

            project = appointment.task_id.project_id
            if project.appointment_date_ok:
                value = project.appointment_date_value
                period = project.appointment_date_period
                date = now + relativedelta(**{period: value})
                if date < appointment.date:
                    raise UserError(_('You cannot set appointment date after %s.' % (date + offset).strftime('%d/%m/%Y %H:%M:%S')))

    def _get_mail_thread_data_attachments(self):
        self.ensure_one()
        res = super()._get_mail_thread_data_attachments()
        attachments = self.env['ir.attachment'].search([('id', 'in', self.document_ids.ids)])
        return res | attachments

    def _update_task(self):
        for appointment in self:
            appointment.task_id.write({
                'reason_id': appointment.reason_id.id,
                'reason_name': appointment.reason_id.name,
                'reason_code': appointment.reason_id.code,
                'reason_desc': appointment.reason_desc,
            })

    def _update_sla(self):
        for appointment in self:
            if appointment.task_id.stage_id.code == APPOINTMENT_STAGE_CODE:
                tickets = appointment.task_id.partner_ticket_ids
                if tickets:
                    log = tickets[0]['stage_log_id']
                    if log and log.stage_id.stage_ref.code == APPOINTMENT_STAGE_CODE:
                        log.sudo().write({'due_date': appointment.date})

    def action_view_task(self):
        action = self.env.ref('fsm.action_task').sudo().read()[0]
        action['context'] = {'create': False, 'delete': False}
        action['views'] = [(False, 'form')]
        action['res_id'] = self.task_id.id
        return action

    def action_change_date(self):
        if not self.env.user.has_group('fsm.group_manager'):
            raise AccessDenied(_('Only managers can change appointment date manually!'))

        action = self.env.ref('fsm.action_appointment_date_change').sudo().read()[0]
        action['context'] = {'default_appointment_id': self.id}
        return action

    def confirm(self):
        return {'type': 'fsm.reload'}

    def action_photo(self):
        return {'type': 'fsm.file'}
    
    def get_metadata(self):
        return {'type': None, 'size': None}

    @api.model_create_multi
    def create(self, vals_list):
        task_one = 'default_task_id' in self.env.context
        if not task_one:
            for vals in vals_list[:]:
                if vals.get('task_ids'):
                    val_list = []
                    for task_id in vals['task_ids'][0][2]:
                        task = self.task_id.browse(task_id)
                        contact = task.merchant_id.child_ids.filtered(lambda c: not c.is_company)
                        val_list.append({
                            **vals,
                            'task_id': task_id,
                            'partner_id': contact and contact[0]['id'] or False,
                        })
                    vals_list = val_list
                    break

        res = super().create(vals_list)
        task_vals = self.env.context.get('values', {})
        for appointment in res:
            if task_vals:
                appointment.task_id.with_context(no_reason=True, no_appointment=True).write(task_vals)
            if appointment.reason_id:
                appointment._update_task()
                appointment._update_sla()
        if not task_one:
            return res[0]
        return res

    def write(self, values):
        res = super().write(values)
        if 'reason_id' in values:
            self._update_task()
            self._update_sla()
        return res
