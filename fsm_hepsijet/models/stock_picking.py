# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.tools import float_is_zero


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _hepsijet_get_egyg_location_id(self):
        return self.fsm_button_action_id.picking_carrier_hepsijet_egyg_location_id or super()._hepsijet_get_egyg_location_id()

    def _hepsijet_get_customer_order_id(self):
        name = None
        if self.fsm_task_id and self.delivery_hepsijet_egyg_ok:
            egyg_id = self.delivery_hepsijet_egyg_picking_id
            egyg_res_id = self.delivery_hepsijet_egyg_picking_res_id
            if not egyg_id and not egyg_res_id:
                task = self.fsm_task_id
                subtask = None
                if task.parent_id:
                    code = task.parent_id.type_id.code
                    subtask = task.parent_id.child_ids.filtered(lambda t: t.type_id.code == '%s_GERI_ALIM' % code)
                    if subtask:
                        subtask = subtask[0]
                if subtask:
                    name = subtask.product_lot_id.name
            elif egyg_id:
                name = fields.first(egyg_id.move_line_ids).lot_id.name
            elif egyg_res_id:
                name = fields.first(self.move_line_ids).lot_id_name
        return name


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _prepare_move_default_values(self, return_line, new_picking):
        vals = super(StockReturnPicking, self)._prepare_move_default_values(return_line, new_picking)
        product_id = self.env.context.get('egyg_product_id')
        if product_id:
            vals.update({'product_id': product_id})
            if float_is_zero(vals.get('product_uom_qty', 0.0), precision_rounding=return_line.product_id.uom_id.rounding):
                vals.update({'product_uom_qty': 1.0})
        return vals

    def _create_returns(self):
        if not self.env.context.get('egyg'):
            return super(StockReturnPicking, self)._create_returns()

        task = None
        subtask = None
        product = None
        if self.picking_id.delivery_hepsijet_egyg_ok and not self.picking_id.delivery_hepsijet_egyg_picking_id and not self.picking_id.delivery_hepsijet_egyg_picking_res_id:
            task = self.picking_id.fsm_task_id
            if task.parent_id:
                code = task.parent_id.type_id.code
                subtask = task.parent_id.child_ids.filtered(lambda t: t.type_id.code == '%s_GERI_ALIM' % code)
                if subtask:
                    subtask = subtask[0]
                    product = subtask.product_id
                else:
                    product = task.product_id

        if product:
            self = self.with_context(egyg_product_id=product.id)
            for line in self.product_return_moves:
                if float_is_zero(line.quantity, precision_rounding=line.product_id.uom_id.rounding):
                    line.quantity = 1

        np, pti = super(StockReturnPicking, self)._create_returns()
        if task:
            picking = self.env['stock.picking'].browse(np)
            if subtask:
                picking.write({'fsm_task_id': subtask.id})
                for line in picking.move_line_ids:
                    line.write({'lot_id': subtask.product_lot_id.id})
            else:
                picking.write({'fsm_task_id': task.id})
        return np, pti
