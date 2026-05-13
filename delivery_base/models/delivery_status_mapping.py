from odoo import models, fields, _
from odoo.exceptions import ValidationError


class DeliveryStatusMapping(models.Model):
    _name = 'delivery.status.mapping'
    _description = 'Delivery Status Mapping'
    _order = 'sequence'

    code = fields.Char(string='Code', help='Unique code for the delivery status')
    name = fields.Char(string='Name', help='Unique name for the delivery status')
    ref = fields.Char(string='Reference', help='Unique reference for the delivery status')
    status_id = fields.Many2one('delivery.status', string='Status Name', required=True, help='Reference to the delivery status', ondelete='restrict')
    status_code = fields.Char(related='status_id.code', string='Status Code', help='Reference to the delivery status code')
    carrier_id = fields.Many2one('delivery.carrier', required=True, string='Carrier', help='Reference to the delivery carrier')
    sequence = fields.Integer(string='Sequence', default=10, help='Sequence for ordering the delivery status mappings')

    def get_status(self, name=None, code=None, ref=False):
        if not name and not code:
            raise ValidationError(_('One of name or code parameter must be set.'))

        for line in self:
            status = True

            if name and line.name:
                status = status and line.name == name
                if not status:
                    continue

            if code and line.code:
                status = status and line.code == code
                if not status:
                    continue
            status = status and line.ref == ref
            if status:
                return line.status_id

        return self.env['delivery.status'].get_status('transferring')
