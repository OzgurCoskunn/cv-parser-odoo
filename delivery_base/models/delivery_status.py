from odoo import models, fields, api


class DeliveryStatus(models.Model):
    _name = 'delivery.status'
    _description = 'Delivery Status'

    code = fields.Char(string='Code', required=True, help='Unique code for the delivery status')
    name = fields.Char(string='Name', required=True, translate=True, help='Name of the delivery status')

    @api.model
    def get_status(self, code):
        return self.search([('code', '=', code)], limit=1)
