from odoo import models, fields


class DeliveryBarcodePrefix(models.Model):
    _name = 'delivery.barcode.prefix'
    _description = 'Delivery Barcode Prefix'

    carrier_id = fields.Many2one('delivery.carrier')
    service_type = fields.Selection([
        ('standard', 'Standart Teslimat'),
        ('return', 'İade Alım'),
        ('contract', 'Sözleşmeli Teslimat'),
        ('eygy_delivery', 'EYGY Teslimat'),
        ('eygy_return', 'EYGY İade'),
        ('contract_only', 'Sözleşme')
    ], required=True)
    name = fields.Char(string="Barcode Prefix", required=True)