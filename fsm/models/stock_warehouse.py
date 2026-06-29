# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    fsm_owner_id = fields.Many2one('res.partner', string='Field Service Owner')
    fsm_user_id = fields.Many2one('res.users', string='Field Service User', domain='[("share", "=", False)]')
