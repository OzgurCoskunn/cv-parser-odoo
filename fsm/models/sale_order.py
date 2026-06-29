# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import float_compare
from odoo.exceptions import UserError


class FsmSaleOrderDetail(models.Model):
    _name = 'fsm.sale.order.detail'
    _description = 'Field Service Sale Order Details'

    order_id = fields.Many2one('sale.order')
    key = fields.Char()
    value = fields.Char()


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fsm_detail_ids = fields.One2many('fsm.sale.order.detail', 'order_id', string='Field Service Details')
    fsm_warehouse_id = fields.Many2one('stock.warehouse', string='Field Service Warehouse')
    fsm_ref = fields.Char(string='Field Service Customer Order ID')
    fsm_channel = fields.Char(string='Field Service Channel')
    fsm_cancelled = fields.Boolean(string='Field Service Cancelled')
    fsm_ok = fields.Boolean(string='Field Service')

    @api.depends('user_id', 'company_id', 'fsm_warehouse_id')
    def _compute_warehouse_id(self):
        for order in self:
            if order.fsm_ok and order.fsm_warehouse_id:
                order.warehouse_id = order.fsm_warehouse_id.id
            else:
                super(SaleOrder, order)._compute_warehouse_id()

    @api.model
    def _get_fsm_warehouse_id(self, partner, company):
        return self.env['stock.warehouse'].sudo().search([
            ('fsm_owner_id', '=', partner.id),
            ('company_id', '=', company.id),
        ], limit=1)

    @api.model
    def create(self, values):
        res = super(SaleOrder, self).create(values)
        for order in res:
            if order.fsm_ok:
                if not order.fsm_warehouse_id:
                    order.fsm_warehouse_id = self._get_fsm_warehouse_id(order.partner_id, order.company_id)
                order.order_line._action_fsm_launch_stock_rule()
        return res

    def _action_confirm(self):
        for order in self:
            if order.fsm_ok:
                if order.fsm_cancelled:
                    raise UserError(_('You cannot confirm an field service order which has been cancelled before.'))
                order.picking_ids.write({'fsm_pending': False})
        return super(SaleOrder, self)._action_confirm()

    def _action_cancel(self):
        self.write({'fsm_cancelled': True})
        return super(SaleOrder, self)._action_cancel()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('move_ids')
    def _compute_fsm_reserved_lot_ids(self):
        for line in self:
            line.fsm_reserved_lot_ids = [(6, 0, line.move_ids.mapped('move_line_ids.lot_id').ids)]

    fsm_reserved_lot_ids = fields.Many2many('stock.lot', string='Field Service Reserved Lots/Serials', compute='_compute_fsm_reserved_lot_ids', compute_sudo=True)

    def _action_fsm_launch_stock_rule(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if not line.product_id.type in ('consu', 'product'):
                continue
            qty = line._get_qty_procurement(False)
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) == 0:
                continue

            # Removed procurement.group logic as it is removed/deprecated in Odoo 19
            # group_id = line._get_procurement_group()
            # if not group_id:
            #     group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
            #     line.order_id.procurement_group_id = group_id
            # else:
            #     updated_vals = {}
            #     if group_id.partner_id != line.order_id.partner_shipping_id:
            #         updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
            #     if group_id.move_type != line.order_id.picking_policy:
            #         updated_vals.update({'move_type': line.order_id.picking_policy})
            #     if updated_vals:
            #         group_id.write(updated_vals)

            values = line._prepare_procurement_values() # Removed group_id argument
            product_qty = line.product_uom_qty - qty

            line_uom = line.product_uom
            quant_uom = line.product_id.uom_id
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
            
            # Use stock.rule.Procurement
            procurements.append(self.env['stock.rule'].Procurement(
                line.product_id, product_qty, procurement_uom,
                line.order_id.partner_shipping_id.property_stock_customer,
                line.product_id.display_name, line.order_id.name, line.order_id.company_id, values))
        if procurements:
             self.env['stock.rule'].run(procurements)

        orders = self.mapped('order_id')
        for order in orders:
            pickings = order.picking_ids.filtered(lambda p: p.state not in ['cancel', 'done'])
            if pickings:
                pickings.write({'fsm_pending': True})
                pickings.action_assign()
        if not self.fsm_reserved_lot_ids:
            raise UserError(_('The product you are about to order is out of stock.'))
        return True
