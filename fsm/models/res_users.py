# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _compute_fsm_warehouse_ids(self):
        for user in self:
            user.fsm_warehouse_ids = user.fsm_location_ids.mapped('warehouse_id').ids

        #warehouses = self.env['stock.warehouse']
        #for user in self:
        #    views = set()
        #    locations = user.fsm_location_ids
        #    for location in locations:
        #        while location.usage != 'view':
        #            location = location.location_id
        #        views.add(location.id)
        #    user.fsm_warehouse_ids = warehouses.search([('view_location_id', 'in', list(views))]).ids

    fsm_task_ids = fields.One2many('fsm.task', 'user_id', string='Field Service Tasks')
    fsm_location_ids = fields.One2many('stock.location', 'fsm_user_id', string='Field Service Locations')
    fsm_warehouse_ids = fields.Many2many('stock.warehouse', compute='_compute_fsm_warehouse_ids', string='Field Service Warehouses')

    def action_assign_stock_location(self):
        return self.env.ref('fsm.action_stock_location_user_assign').sudo().read()[0]
