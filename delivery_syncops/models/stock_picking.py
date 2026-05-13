# -*- coding: utf-8 -*-
from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    syncops_log_ref = fields.Char(string='syncOPS Log Reference', readonly=True, copy=False)
    syncops_connector_id = fields.Many2one('syncops.connector', string='syncOPS Connector', readonly=True, copy=False)

    def write(self, values):
        if 'carrier_id' in values:
            carrier = self.env['delivery.carrier'].browse(values['carrier_id'])
            connector = getattr(carrier, 'delivery_%s_connector_id' % carrier.delivery_type, False)
            values['syncops_connector_id'] = connector and connector.id
        return super().write(values)
