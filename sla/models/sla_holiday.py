# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SlaHoliday(models.Model):
    _name = 'sla.holiday'
    _description = 'Service Level Agreement: Holidays'
    _order = 'date_from'

    name = fields.Char(required=True)
    date_from = fields.Datetime(string='Start Date', required=True)
    date_to = fields.Datetime(string='End Date', required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for day in self:
            if day.date_from and day.date_to and day.date_from > day.date_to:
                raise ValidationError(_('Start date must be earlier than end date.'))

    @api.model
    def _get_range(self, date_from=None, date_to=None):
        if date_from and date_to:
            domain = [
                '|',
                '&', ('date_from', '>=', date_from), ('date_from', '<=', date_to),
                '&', ('date_from', '<=', date_from), ('date_to', '>=', date_from),
            ]
        elif date_from:
            domain = [
                '|', ('date_from', '>=', date_from),
                '&', ('date_from', '<=', date_from), ('date_to', '>=', date_from),
            ]
        elif date_to:
            domain = [('date_from', '<=', date_to)]
        else:
            domain = []
        dates = self.env['sla.holiday'].sudo().search_read(domain, ['date_from', 'date_to'])
        return [(date['date_from'], date['date_to']) for date in dates]

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        now = datetime.now()
        res.update({
            'date_from': datetime.combine(now, datetime.min.time()),
            'date_to': datetime.combine(now, datetime.max.time()),
        })
        return res