# -*- coding: utf-8 -*-

import uuid
from pytz import timezone
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _

DEFAULT_TZ = 'Europe/Istanbul'


class SlaTicket(models.Model):
    _name = 'sla.ticket'
    _description = 'Service Level Agreement: Tickets'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id desc'

    def _compute_name(self):
        for ticket in self:
            ticket.name = _('Ticket #%s') % ticket.id

    @api.depends('stage_id', 'agreement_id')
    def _compute_kanban_state(self):
        self.kanban_state = 'normal'

    def _get_default_stage_id(self):
        if self.env.context.get('default_agreement_id'):
            agreement = self.env['sla.agreement'].sudo().browse(self.env.context['default_agreement_id'])
            return agreement.stage_ids and agreement.stage_ids[0]['id']
        return False

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        if self.env.context.get('default_agreement_id'):
            agreement = self.env['sla.agreement'].sudo().browse(self.env.context['default_agreement_id'])
            return agreement.stage_ids
        return self.env['sla.agreement.stage'].search(domain, order=order)

    @api.depends('agreement_id')
    def _compute_stage_ids(self):
        for ticket in self:
            stage_ids = None
            if ticket.res_id and ticket.res_model:
                res = self.env[ticket.res_model].sudo().browse(ticket.res_id)
                if res and hasattr(res, 'stage_ids'):
                    stage_ids = ticket.agreement_id.stage_ids.filtered(lambda s: s.stage_id in res.stage_ids.ids)
            ticket.stage_ids = stage_ids or ticket.agreement_id.stage_ids.ids

    def _compute_stage_log_id(self):
        for ticket in self:
            log_ids = ticket.stage_log_ids
            ticket.stage_log_id = log_ids and log_ids[-1]

    @api.depends('stage_id')
    def _compute_hours(self):
        for ticket in self:
            ticket.stage_hour_all = ticket.stage_time_hour_all
            ticket.stage_hour_work = ticket.stage_time_hour_work

    def _compute_times(self):
        for ticket in self:
            time_all = 0
            time_work = 0
            time_work_spent = 0
            time_work_paused = 0

            for log in ticket.stage_log_ids:
                if log.stage_id.type in ('0', '1'):
                    time_all += log.time_all
                    if log.stage_id.type == '0':
                        time_work += log.time_work
                        time_work_spent += log.time_work
                    else:
                        time_work_paused += log.time_work

            time_from = ticket.stage_log_ids[0].date_from if ticket.stage_log_ids else ticket.create_date
            if not time_from:
                ticket.stage_time_work_spent = 0
                ticket.stage_time_work_left = 0
                ticket.stage_time_work_paused = 0
                ticket.stage_time_hour_all = 0
                ticket.stage_time_hour_work = 0
                ticket.due_date = False
                continue

            time_work_total = ticket.agreement_id.worksheet_id.hour_average
            if not time_work_total:
                ticket.stage_time_work_spent = 0
                ticket.stage_time_work_left = 0
                ticket.stage_time_work_paused = 0
                ticket.stage_time_hour_all = 0
                ticket.stage_time_hour_work = 0
                ticket.due_date = False
                continue

            time_work_day, time_work_hour = divmod(time_work, time_work_total)
            time_work = time_work_day * 24 + time_work_hour

            ticket.stage_time_hour_all = time_all
            ticket.stage_time_hour_work = time_work
            ticket.stage_time_work_spent = time_work_spent
            ticket.stage_time_work_left = ticket.agreement_hour_total - time_work_spent
            ticket.stage_time_work_paused = time_work_paused
            ticket.due_date = ticket._get_due_date(date_from=time_from)

    def _compute_stage_times(self):
        for ticket in self:
            time_from = ticket.stage_log_ids[0].date_from if ticket.stage_log_ids else ticket.create_date
            if not time_from:
                ticket.stage_time_all = ''
                ticket.stage_time_work = ''
                continue

            if not ticket.stage_time_hour_all:
                ticket.stage_time_all = ''
                ticket.stage_time_work = ''
                continue

            delta_all = relativedelta(time_from + relativedelta(hours=ticket.stage_time_hour_all), time_from)
            delta_work = relativedelta(time_from + relativedelta(hours=ticket.stage_time_hour_work), time_from)

            time_all = []
            time_work = []

            if delta_all.years:
                time_all.append(_('%s year(s)') % delta_all.years)
            if delta_all.years or delta_all.months:
                time_all.append(_('%s month(s)') % delta_all.months)
            time_all.append(_('%s day(s)') % delta_all.days)
            time_all.append(_('%s hour(s)') % delta_all.hours)
            time_all.append(_('%s minute(s)') % delta_all.minutes)

            if delta_work.years:
                time_work.append(_('%s year(s)') % delta_work.years)
            if delta_work.years or delta_work.months:
                time_work.append(_('%s month(s)') % delta_work.months)
            time_work.append(_('%s day(s)') % delta_work.days)
            time_work.append(_('%s hour(s)') % delta_work.hours)
            time_work.append(_('%s minute(s)') % delta_work.minutes)

            ticket.stage_time_all = ' '.join(time_all)
            ticket.stage_time_work = ' '.join(time_work)

    @api.model
    def _selection_ref(self):
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([])]

    name = fields.Char(compute='_compute_name')
    active = fields.Boolean(default=True, tracking=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer()
    uid = fields.Char(default=lambda self: str(uuid.uuid4()), copy=False)
    description = fields.Text()
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'High'),
    ], default='0', required=True, tracking=True, index=True)
    res_id = fields.Many2oneReference(model_field='res_model')
    res_ref = fields.Reference(selection='_selection_ref')
    res_model = fields.Char()
    res_type = fields.Char()
    user_id = fields.Many2one('res.users', string='User')
    team_id = fields.Many2one('crm.team', string='Team')
    user_ids = fields.Many2many('res.users', related='team_id.member_ids', string='Users')
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Ready'),
        ('blocked', 'Blocked')
    ], string='Status', copy=False, default='normal', required=True, compute='_compute_kanban_state', readonly=False, store=True)
    agreement_id = fields.Many2one('sla.agreement', required=True, index=True, tracking=True, check_company=True)
    agreement_hour_total = fields.Float(readonly=True)
    partner_id = fields.Many2one('res.partner', related='agreement_id.partner_id', store=True, index=True, tracking=True)
    stage_id = fields.Many2one('sla.agreement.stage', ondelete='restrict', tracking=True, index=True, copy=False, default=_get_default_stage_id, group_expand='_read_group_stage_ids', domain='[("id", "in", stage_ids)]')
    stage_ids = fields.Many2many('sla.agreement.stage', compute='_compute_stage_ids', compute_sudo=True)
    stage_log_ids = fields.One2many('sla.ticket.log', 'ticket_id', string='Logs')
    stage_log_id = fields.Many2one('sla.ticket.log', compute='_compute_stage_log_id', compute_sudo=True)
    stage_type = fields.Selection(related='stage_id.type', store=True, index=True)
    stage_time_all = fields.Char(string='Elapsed Time (All Hours)', compute='_compute_stage_times', compute_sudo=True)
    stage_time_work = fields.Char(string='Elapsed Time (Work Hours)', compute='_compute_stage_times', compute_sudo=True)
    stage_time_work_spent = fields.Float(string='Spent Time (Work Hours)', compute='_compute_times', compute_sudo=True)
    stage_time_work_left = fields.Float(string='Residual Time (Work Hours)', compute='_compute_times', compute_sudo=True)
    stage_time_work_paused = fields.Float(string='Paused Time (Work Hours)', compute='_compute_times', compute_sudo=True)
    stage_time_hour_all = fields.Float(string='Elapsed Time (With All Hours)', compute='_compute_times', compute_sudo=True)
    stage_time_hour_work = fields.Float(string='Elapsed Time (With Work Hours)', compute='_compute_times', compute_sudo=True)
    stage_hour_all = fields.Float(string='Elapsed Time (Based All Hours)', compute='_compute_hours', compute_sudo=True, store=True)
    stage_hour_work = fields.Float(string='Elapsed Time (Based Work Hours)', compute='_compute_hours', compute_sudo=True, store=True)
    due_date = fields.Datetime(string='Due Date', compute='_compute_times', compute_sudo=True)
    company_id = fields.Many2one('res.company', related='agreement_id.company_id', store=True)

    def _get_due_date(self, date_from=None):
        def hours(hour):
            hour, minute = divmod(hour, 1)
            return {'hours': int(hour), 'minutes': int(60*minute)}

        if not date_from:
            date_from = self.create_date
        if not date_from:
            return False

        date_sign = -1 if self.stage_time_work_left < 0 else 1
        date_residual = self.stage_time_work_left * date_sign
        date_due = self.stage_log_id and self.stage_log_id.date_to or datetime.now()
        date_to = date_due + relativedelta(months=1)

        worksheet = self.agreement_id.worksheet_id
        holidays = self.env['sla.holiday'].sudo()._get_range(date_from=date_from)
        workdays = {}
        for w in worksheet.line_ids:
            if w.day not in workdays:
                workdays[w.day] = []
            workdays[w.day].append((w.hour_from, w.hour_to))

        try: tz = timezone(worksheet.tz or DEFAULT_TZ)
        except: tz = timezone('UTC')
        date_offset = tz.utcoffset(date_from)

        #residual = self.agreement_hour_total
        #for log in self.stage_log_ids:
        #    elapsed = log.time_work
        #    if log.stage_id.type == '0':
        #        if elapsed >= residual:
        #            residual = 0
        #            due += relativedelta(**hours(residual))
        #            break
        #        else:
        #            residual -= elapsed
        #            due += relativedelta(**hours(elapsed))
        #    elif log.stage_id.type == '1':
        #        if log.due_date:
        #            due = log.due_date
        #        residual += elapsed

        timeons = []
        date_today = datetime.combine(date_due + date_offset, datetime.min.time()) - date_offset
        date_start = date_today
        while True:
            if date_sign > 0:
                if date_today >= date_to:
                    break
            else:
                if date_today <= date_from:
                    break

            workday = workdays.get(str((date_today + date_offset).date().weekday()))
            if workday:
                for day in workday:
                    date_start = date_today + relativedelta(**hours(day[0]))
                    date_end = date_today + relativedelta(**hours(day[1]))
                    timeons.append([date_start, date_end])

            date_today = date_today + relativedelta(days=date_sign)
            continue

        for h in holidays:
            for i, t in enumerate(timeons):
                if h[0] <= t[0] <= h[1]:
                    if t[1] <= h[1]:
                        del timeons[i]
                    else:
                        timeons[i][0] = h[1]
                elif h[0] <= t[1] <= h[1]:
                    if h[0] <= t[0]:
                        del timeons[i]
                    else:
                        timeons[i][1] = h[0]
                elif t[0] < h[0] and h[1] < t[1]:
                    timeons[i][1] = h[0]
                    timeons.append([h[1], t[1]])

        timeons.sort()
        if date_sign < 0:
            timeons.reverse()

        if date_sign > 0:
            for t in timeons:
                if date_due <= t[1]:
                    if date_due <= t[0]:
                        diff = (t[1] - t[0]).total_seconds() / 3600
                    else:
                        diff = (t[1] - date_due).total_seconds() / 3600
                    
                    if date_residual >= diff:
                        date_due = t[1]
                        date_residual -= diff
                        if date_residual == 0:
                            date_due = t[1]
                            break
                    else:
                        date_due = t[0] + relativedelta(**hours(date_residual))
                        break
        else:
            for t in timeons:
                if date_due >= t[0]:
                    if date_due >= t[1]:
                        diff = (t[1] - t[0]).total_seconds() / 3600
                    else:
                        diff = (date_due - t[0]).total_seconds() / 3600
                    
                    if date_residual >= diff:
                        date_due = t[0]
                        date_residual -= diff
                    else:
                        date_due = t[1] - relativedelta(**hours(date_residual))
                        break

        return date_due
        #return due.replace(second=0, microsecond=0)

    def _update_stage_log_ids(self):
        for ticket in self.sudo():
            date = fields.Datetime.now()
            log = ticket.stage_log_id
            if log:
                if log.stage_id.id == ticket.stage_id.id:
                    continue
                log.set_date_to(date)
            ticket.stage_log_ids.create({
                'ticket_id': ticket.id,
                'stage_id': ticket.stage_id.id,
                'date_from': date,
                'date_to': ticket.stage_id.type in ('2', '3') and date,
            })

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for i, vals in enumerate(vals_list):
            if 'agreement_hour_total' not in vals and not res[i].agreement_id.hour_model:
                res[i].agreement_hour_total = res[i].agreement_id.hour_total
        res._update_stage_log_ids()
        return res

    def write(self, values):
        res = super().write(values)
        if 'stage_id' in values:
            self._update_stage_log_ids()
        return res


class SlaTicketLog(models.Model):
    _name = 'sla.ticket.log'
    _description = 'Service Level Agreement: Ticket Logs'
    _order = 'id'

    def _compute_times(self):
        def hours(hour):
            hour, minute = divmod(hour, 1)
            return {'hours': int(hour), 'minutes': int(60*minute)}

        date_now = fields.Datetime.now()
        date_min = min(self.filtered('date_from').mapped('date_from')) or date_now
        holidays_list = self.env['sla.holiday'].sudo()._get_range(date_from=date_min, date_to=date_now)

        log = None
        for i, log in enumerate(self):
            worksheet = log.ticket_id.agreement_id.worksheet_id
            try: tz = timezone(worksheet.tz or DEFAULT_TZ)
            except: tz = timezone('UTC')

            date_offset = tz.utcoffset(date_now)
            date_from = log.date_from or date_now
            date_to = log.date_to or date_now
            diff = (date_to - date_from).total_seconds()
            log.time_all = diff / 3600

            if not worksheet or log.stage_id.type not in ('0', '1'):
                log.time_work = 0
                continue

            holidays = list(filter(lambda d: d[0] >= date_from and d[0] <= date_to or d[0] <= date_from <= d[1], holidays_list))
            for holiday in holidays:
                if holiday[0] <= date_from <= holiday[1]:
                    date_from = holiday[1]
                    if date_from >= date_to:
                        break
                if holiday[0] <= date_to <= holiday[1]:
                    date_to = holiday[0]
                    if date_from >= date_to:
                        break

            if date_from >= date_to:
                log.time_work = 0
                continue

            workdays = {}
            for line in worksheet.line_ids:
                if line.day not in workdays:
                    workdays[line.day] = []
                workdays[line.day].append((line.hour_from, line.hour_to))

            hour_offset = date_offset.seconds / 3600
            hour_from = (date_from.hour + hour_offset) % 24
            #hour_now = (date_now.hour + hour_offset) % 24
            if i == 0 and worksheet.hour_threshold and hour_from >= worksheet.hour_threshold:
                date_from = datetime.combine(date_from + date_offset + relativedelta(days=1), datetime.min.time()) - date_offset

            timeoffs = []
            date_today = datetime.combine(date_from + date_offset, datetime.min.time()) - date_offset
            date_start = date_today
            while True:
                if date_today >= date_to:
                    break

                workday = workdays.get(str((date_today + date_offset).date().weekday()))
                if workday:
                    for day in workday:
                        date_end = date_today + relativedelta(**hours(day[0]))
                        timeoffs.append((date_start, date_end))
                        date_start = date_today + relativedelta(**hours(day[1]))

                date_end = date_today + relativedelta(days=1)
                timeoffs.append((date_start, date_end))
                date_today = date_end
                date_start = date_today
                continue

            timeoffs += holidays
            timeoffs.sort()
            diff = 0

            for t in timeoffs:
                if date_from < t[0]:
                    if date_to < t[0]:
                        diff += (date_to - date_from).total_seconds()
                        break
                    else:
                        diff += (t[0] - date_from).total_seconds()
                if t[0] <= date_to < t[1]:
                    break
                date_from = max(date_from, t[1])

            log.time_work = diff / 3600

        if log and log.stage_id.type not in ('0', '1'):
            log.time_all = 0

    ticket_id = fields.Many2one('sla.ticket', ondelete='cascade')
    stage_id = fields.Many2one('sla.agreement.stage')
    stage_type = fields.Selection(related='stage_id.type')
    date_from = fields.Datetime(string='Start Date')
    date_to = fields.Datetime(string='End Date')
    due_date = fields.Datetime(string='Due Date')
    time_all = fields.Float(string='Elapsed Time (All Hours)', compute='_compute_times')
    time_work = fields.Float(string='Elapsed Time (Work Hours)', compute='_compute_times')
    approval_state = fields.Selection([('0', 'Approved'), ('1', 'Rejected')], string='Approval State')
    approval_date = fields.Datetime(string='Approval Date')
    approval_code = fields.Char(string='Approval Code')
    approval_desc = fields.Char(string='Approval Description')

    def set_date_from(self, date=None):
        if not self.date_from:
            self.sudo().write({'date_from': date or fields.Datetime.now()})

    def set_date_to(self, date=None):
        if not self.date_to:
            self.sudo().write({'date_to': date or fields.Datetime.now()})
