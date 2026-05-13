# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError, RedirectWarning

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    fsm_task_id = fields.Many2one('fsm.task', string='FSM Task')
    fsm_stage_id = fields.Many2one('fsm.stage', related='fsm_flow_stage_id.stage_id', string='FSM Stage')
    fsm_flow_stage_id = fields.Many2one('fsm.flow.stage', string='FSM Flow Stage')
    fsm_task_todo_id = fields.Many2one('fsm.task.todo', string='FSM Task Todo')
    fsm_task_todo_action_id = fields.Many2one('fsm.todo.action', string='FSM Task Todo Action')
    fsm_button_action_id = fields.Many2one('fsm.button.action', string='FSM Button Action')
    fsm_pending = fields.Boolean(string='FSM Pending')

    def _write(self, values):
        res = super()._write(values)
        for picking in self.sudo():
            if picking.fsm_task_id:
                autos = picking.fsm_task_id.flow_stage_id.mapped('auto_ids').filtered(lambda a: a.trigger == 'picking')
                try:
                    autos.run_pickings(picking.fsm_task_id.id, autos.ids, values)
                except Exception as e:
                    if self.env.uid == SUPERUSER_ID:
                        _logger.error('An error occured when triggering an automation for task #%s.\n%s' % (picking.fsm_task_id.id, e))
                        continue
                    raise
        return res

    def action_view_task(self):
        action = self.env.ref('fsm.action_task').sudo().read()[0]
        action['res_id'] = self.fsm_task_id.id
        action['views'] = [(False, 'form')]
        return action

    def button_validate(self):
        for picking in self:
            if picking.fsm_pending:
                raise UserError(_('You cannot mark this transfer as done, because it is in pending state. Please confirm related sale orders first.'))
            if picking.fsm_task_id:
                products = picking.fsm_task_id.product_ids
                for line in self.move_line_ids:
                    if line.lot_id:
                        product = products.filtered(lambda p: p.product_id.id == line.product_id.id)
                        for prod in product:
                            if line.lot_id.id != prod.product_lot_id.id:
                                raise ValidationError(_('Lot/serial are mismatched.\nTask: %s\nPicking: %s') % (prod.product_lot_id.name or _('No lot/serial set'), line.lot_id.name or _('No lot/serial assigned')))
        return super(StockPicking, self).button_validate()

    def _action_done(self):
        if self.env.user.has_group('fsm.group_user'):
            return super(StockPicking, self.sudo())._action_done()
        return super(StockPicking, self)._action_done()


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _key_assign_picking(self):
        keys = super()._key_assign_picking()
        keys += (self.picking_id.fsm_task_id,)
        return keys

    def _get_available_move_lines(self, assigned_moves_ids, partially_available_moves_ids):
        if self.picking_id.fsm_task_id:
            return {}
        return super()._get_available_move_lines(assigned_moves_ids, partially_available_moves_ids)

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        res = super()._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
        if res.get('lot_id') and not self.env.context.get('force'):
            product = self.picking_id.fsm_task_id.product_ids.filtered(lambda p: p.product_id.id == self.product_id.id)
            if product:
                if product.product_lot_id:
                    if product.product_lot_id.id != res['lot_id']:
                        raise UserError(_('You can only assign %s as lot/serial number for product %s') % (product.product_lot_id.name, product.product_id.display_name))
                else:
                    raise UserError(_('You must assing a lot/serial number in related task for product %s') % product.product_id.display_name)
        else:
            context_lot_id = self.env.context.get('values_stock_move_line', {}).get('lot_id')
            if context_lot_id:
                res['lot_id'] = context_lot_id
            else:
                product = self.picking_id.fsm_task_id.product_ids.filtered(lambda p: p.product_id.id == self.product_id.id)
                if product and product.product_lot_id:
                    res['lot_id'] = product.product_lot_id.id
        return res

    def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None, owner_id=None, strict=True):
        self.ensure_one()
        context_lot_id = self.env.context.get('values_stock_move_line', {}).get('lot_id')
        if context_lot_id:
            context_lot_id = self.env['stock.lot'].sudo().browse(context_lot_id)
            lot_id = context_lot_id
        else:
            product = self.picking_id.fsm_task_id.product_ids.filtered(lambda p: p.product_id.id == self.product_id.id)
            if product and product.product_lot_id:
                lot_id = product.product_lot_id

        return super()._update_reserved_quantity(need, available_quantity, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)

    def _get_available_quantity(self, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False):
        self.ensure_one()
        context_lot_id = self.env.context.get('values_stock_move_line', {}).get('lot_id')
        if context_lot_id:
            context_lot_id = self.env['stock.lot'].sudo().browse(context_lot_id)
        else:
            product = self.picking_id.fsm_task_id.product_ids.filtered(lambda p: p.product_id.id == self.product_id.id)
            if product and product.product_lot_id:
                lot_id = product.product_lot_id                    

        res = super()._get_available_quantity(location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict, allow_negative=allow_negative)
        if not res:
            task = self.env.context.get('task')
            if task:
                task = self.env['fsm.task'].browse(task)
                product = task.product_ids.filtered(lambda p: p.product_id.id == self.product_id.id)
                if product and product.product_id.tracking in ('serial', 'lot'):
                    if product.product_lot_id:
                        msg = _('%s %s cannot be assigned because it has already been reserved for another picking or it has no stock for this location.' % (
                            _('Serial') if product.product_id.tracking == 'serial' else _('Lot'),
                            product.product_lot_id.name,
                        ))
                        if self.env.user.has_group('fsm.group_manager'):
                            lines = self.env['stock.move.line'].search([('lot_id', '=', product.product_lot_id.id)])
                            pickings = self.env['stock.picking'].search([('name', 'in', lines.mapped('reference'))])
                            raise RedirectWarning(msg, {
                                'name': _('Transfers of %s') % product.product_lot_id.name,
                                'type': 'ir.actions.act_window',
                                'target': 'current',
                                'res_model': 'stock.picking',
                                'views': [(False, 'tree'), (False, 'form')],
                                'domain': [('id', 'in', pickings.ids)],
                                'context': {'create': False, 'edit': True, 'delete': False},
                            }, _('View Transfer'))
                        else:
                            raise UserError(msg)
        return res


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.depends('product_id', 'company_id')
    def _compute_fsm_lot_ids(self):
        for line in self:
            line.fsm_lot_ids = line.picking_id.fsm_task_id.product_ids.mapped('product_lot_id').ids

    def _compute_fsm_lot_id(self):
        for line in self:
            line.fsm_lot_id = line.lot_id.id

    def _set_fsm_lot_id(self):
        for line in self:
            line.lot_id = line.fsm_lot_id.id

    fsm_lot_ids = fields.Many2many('stock.lot', compute='_compute_fsm_lot_ids')
    fsm_lot_id = fields.Many2one('stock.lot', 'Field Service Lot/Serial Number', domain="[('product_id', '=', product_id), ('company_id', '=', company_id), ('id', 'in', fsm_lot_ids)]", check_company=True, compute='_compute_fsm_lot_id', inverse='_set_fsm_lot_id')


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    fsm_task_id = fields.Many2one('fsm.task')
    fsm_button_action_id = fields.Many2one('fsm.button.action')

    def _confirm(self):
        if self.fsm_button_action_id:
            button = self.fsm_button_action_id.flow_stage_button_id
            carrier_type = 'hepsijet' #TODO make it parametric
            defaults = {
                **self.env.context.get('defaults', {}),
                str(self.fsm_button_action_id.id): self.env.context.get('values', {}),
                'fsm.appointment': {
                    'default_date': getattr(self, 'delivery_%s_date_suitable' % carrier_type, False)
                }
            }
            action = button.with_context(defaults=defaults)._run_action(self.fsm_task_id)
            if isinstance(action, dict) and 'action' in action:
                return action['action']
            return action

    def create_returns(self):
        action = self._confirm()
        if action:
            return action
 
        res = super().create_returns()
        if isinstance(res, dict) and res.get('res_id'):
            npicking = self.env['stock.picking'].browse(res['res_id'])
            if npicking.fsm_task_todo_id:
                for move in npicking.move_ids:
                    move.write({'quantity': move.product_uom_qty})
                if npicking.fsm_task_todo_id.picking_product_lot_id:
                    for line in npicking.move_line_ids:
                        line.write({'lot_id': npicking.fsm_task_todo_id.picking_product_lot_id.id})
                npicking.button_validate()
                npicking.write({'state': 'cancel'})
                npicking.fsm_task_todo_id.write({'done': False, 'picking_product_lot_id': False})
                npicking.fsm_task_id.product_ids.filtered(lambda p: p.todo_id.id == npicking.fsm_task_todo_id.id and p.product_lot_id and p.product_id.id == npicking.fsm_task_todo_id.picking_product_id.id).write({'product_lot_id': False})
        return res
