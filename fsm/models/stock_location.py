# -*- coding: utf-8 -*-
from odoo import models, fields


class StockLocation(models.Model):
    _inherit = 'stock.location'

    fsm_country_id = fields.Many2one('res.country', string='Field Service Country')
    fsm_state_id = fields.Many2one('res.country.state', string='Field Service State/City', domain='[("country_id", "=", fsm_country_id)]')
    fsm_town_id = fields.Many2one('res.country.town', string='Field Service Town', domain='[("state_id", "=", fsm_state_id)]')
    fsm_user_id = fields.Many2one('res.users', string='Field Service User', domain='[("share", "=", False)]')
    fsm_users_id = fields.Many2many('res.users', 'fsm_stock_location_user_rel', 'location_id', 'user_id', string='Field Service Users', domain='[("share", "=", False)]')
    fsm_user_type = fields.Selection([
        ('solid', 'Solid'),
        ('faulty', 'Faulty'),
        ('repair', 'Repair'),
    ])
