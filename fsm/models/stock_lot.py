# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockLot(models.Model):
    _inherit = 'stock.lot'

    @api.depends('fsm_partner_id')
    def _compute_fsm_subpartner_ids(self):
        for lot in self:
            if lot.fsm_partner_id:
                lot.fsm_subpartner_ids = self.env['fsm.project.subpartner'].sudo().search([
                    ('project_id.partner_id', '=', lot.fsm_partner_id.id),
                ]).mapped('partner_id').ids
            else:
                lot.fsm_subpartner_ids = False

    def _domain_fsm_partner_id(self):
        return [('id', 'in', self.env['fsm.project'].sudo().search([]).mapped('partner_id').ids)]

    def _compute_fsm_sale_order_ids(self):
        for lot in self:
            lines = self.env['stock.move.line'].search([('lot_id', '=', lot.id)])
            lot.fsm_sale_order_ids = lines.mapped('move_id.sale_line_id.order_id').ids

    fsm_task_ids = fields.One2many('fsm.task', 'product_lot_id', string='Field Service Tasks', readonly=True)
    fsm_partner_id = fields.Many2one('res.partner', string='Field Service Owner', domain=_domain_fsm_partner_id)
    fsm_sale_order_ids = fields.Many2many('sale.order', compute='_compute_fsm_sale_order_ids', compute_sudo=True)
    fsm_subpartner_id = fields.Many2one('res.partner', string='Field Service Subpartner', domain='[("id", "in", fsm_subpartner_ids)]')
    fsm_subpartner_ids = fields.Many2many('res.partner', compute='_compute_fsm_subpartner_ids')

    @api.onchange('fsm_partner_id')
    def onchange_fsm_partner_id(self):
        self.fsm_subpartner_id = False
