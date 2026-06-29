# -*- coding: utf-8 -*-
from odoo import models


class SyncopsConnector(models.Model):
    _inherit = 'syncops.connector'

    def action_toggle_environment(self):
        super().action_toggle_environment()
        self.env['delivery.carrier'].sudo().search([
            ('delivery_ptt_connector_id', '=', self.id),
        ]).write({'prod_environment': self.environment})
