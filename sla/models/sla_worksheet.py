# -*- coding: utf-8 -*-

from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone, utc

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.addons.base.models.res_partner import _tz_get


class SlaWorksheet(models.Model):
    _name = 'sla.worksheet'
    _description = 'Service Level Agreement: Worksheets'
    _order = 'sequence'

    @api.depends('line_ids.hour_from', 'line_ids.hour_to')
    def _compute_hour_average(self):
        for worksheet in self:
            days = {}
            for line in worksheet.line_ids:
                if line.day not in days:
                    days[line.day] = 0
                days[line.day] += line.hour_to - line.hour_from
            worksheet.hour_average = round(sum(days.values()) / len(days)) if days else 0

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    line_ids = fields.One2many('sla.worksheet.line', 'worksheet_id', 'Working Times', copy=True)
    hour_average = fields.Float(string='Average Work Hour', compute='_compute_hour_average', store=True, readonly=False)
    hour_threshold = fields.Float(string='Threshold Work Hour')
    tz = fields.Selection(_tz_get, string='Timezone', required=True, default=lambda self: self._context.get('tz') or self.env.user.tz or self.env.ref('base.user_admin').tz or 'UTC')
    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset', invisible=True)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res['line_ids'] = [
            (0, 0, {'name': _('Monday Morning'), 'day': '0', 'period': 'morning', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Monday Afternoon'), 'day': '0', 'period': 'afternoon', 'hour_from': 13, 'hour_to': 17}),
            (0, 0, {'name': _('Tuesday Morning'), 'day': '1', 'period': 'morning', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Tuesday Afternoon'), 'day': '1', 'period': 'afternoon', 'hour_from': 13, 'hour_to': 17}),
            (0, 0, {'name': _('Wednesday Morning'), 'day': '2', 'period': 'morning', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Wednesday Afternoon'), 'day': '2', 'period': 'afternoon', 'hour_from': 13, 'hour_to': 17}),
            (0, 0, {'name': _('Thursday Morning'), 'day': '3', 'period': 'morning', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Thursday Afternoon'), 'day': '3', 'period': 'afternoon', 'hour_from': 13, 'hour_to': 17}),
            (0, 0, {'name': _('Friday Morning'), 'day': '4', 'period': 'morning', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Friday Afternoon'), 'day': '4', 'period': 'afternoon', 'hour_from': 13, 'hour_to': 17}),
        ]
        return res

    @api.depends('tz')
    def _compute_tz_offset(self):
        for worksheet in self:
            worksheet.tz_offset = datetime.now(timezone(worksheet.tz or 'GMT')).strftime('%z')


class SlaWorksheetLine(models.Model):
    _name = 'sla.worksheet.line'
    _description = 'Service Level Agreement: Worksheet Lines'
    _order = 'day, hour_from'

    worksheet_id = fields.Many2one('sla.worksheet', ondelete='cascade')
    name = fields.Char(required=True)
    day = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], 'Day of Week', required=True, index=True, default='0')
    hour_from = fields.Float(string='Start Hour', required=True, index=True)
    hour_to = fields.Float(string='End Hour', required=True, index=True)
    period = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
        ('all', 'All Day'),
    ], required=True, default='all')
    sequence = fields.Integer(default=10)

    @api.constrains('hour_from', 'hour_to')
    def _check_dates(self):
        for day in self:
            if day.hour_from and day.hour_to and day.hour_from > day.hour_to:
                raise ValidationError(_('Start hour must be earlier than end hour.'))

    @api.onchange('hour_from', 'hour_to')
    def _onchange_hours(self):
        self.hour_from = min(self.hour_from, 23.99)
        self.hour_from = max(self.hour_from, 0.0)
        self.hour_to = min(self.hour_to, 24)
        self.hour_to = max(self.hour_to, 0.0)
        self.hour_to = max(self.hour_to, self.hour_from)
