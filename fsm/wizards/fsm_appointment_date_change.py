# -*- coding: utf-8 -*-

from odoo import models, fields


class FsmAppointmentDateChange(models.TransientModel):
    _name = 'fsm.appointment.date.change'
    _description = 'Field Service Management: Change Appointment Date'

    appointment_id = fields.Many2one('fsm.appointment', required=True, ondelete='cascade')
    date = fields.Datetime(required=True)

    def confirm(self):
        self.appointment_id.date = self.date
        return {'type': 'fsm.reload'}
