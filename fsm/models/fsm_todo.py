# -*- coding: utf-8 -*-

from pytz import timezone

from odoo import models, fields, tools, Command, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval, test_python_expr


class FsmTodo(models.Model):
    _name = 'fsm.todo'
    _description = 'Field Service Management: Todos'
    _order = 'sequence'

    name = fields.Char(required=True)
    code = fields.Char()
    required = fields.Boolean()
    sequence = fields.Integer(default=10)
    action_ids = fields.One2many('fsm.todo.action', 'todo_id', 'Actions', copy=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def _run_action(self, tasks, todo=None, actions=None):
        tasks = tasks.sudo()
        if not actions:
            actions = self.action_ids

        for action in actions:

            if action.type == 'code':
                if action.code:
                    context = {
                        'env': self.env,
                        'uid': self._uid,
                        'user': self.env.user,
                        'time': tools.safe_eval.time,
                        'datetime': tools.safe_eval.datetime,
                        'dateutil': tools.safe_eval.dateutil,
                        'timezone': timezone,
                        'tasks': tasks,
                        'todo': todo,
                        'Command': Command,
                        'UserError': UserError,
                    }
                    safe_eval(action.code.strip(), context, mode='exec')
                    if 'action' in context:
                        return context

            elif action.type == 'stage':
                if action.stage_type == '2':
                    if action.reason_id:
                        tasks.with_context(no_reason=True).write({
                            'flow_stage_id': action.flow_stage_id.id,
                            'reason_id': action.reason_id.id,
                            'close_success': action.stage_success,
                            'close_date': fields.Datetime.now(),
                            'close_done': True,
                        })
                    else:
                        tasks.with_context(**{
                            'default_stage_success': action.stage_success,
                            'default_reason_desc': action.reason_desc,
                        }).write({
                            'flow_stage_id': action.flow_stage_id.id,
                        })
                else:
                    if action.reason_id:
                        tasks.with_context(no_reason=True).write({
                            'flow_stage_id': action.flow_stage_id.id,
                            'reason_id': action.reason_id.id,
                        })
                    tasks.with_context(**{
                        'default_stage_success': action.stage_success,
                        'default_reason_desc': action.reason_desc,
                    }).write({
                        'flow_stage_id': action.flow_stage_id.id,
                    })

            elif action.type == 'picking':
                if action.picking_create or self.env.context.get('force'):
                    for task in tasks:
                        values = {
                            'fsm_task_todo_action_id': action.id,
                            'fsm_task_todo_id': todo and todo.id or False,
                            **self.env.context.get('values_stock_picking', {})
                        }
                        moves = {}
                        if action.picking_product_id:
                            moves = {
                                'name': action.picking_product_id.name,
                                'product_id': action.picking_product_id.id,
                                'product_uom_qty': 1,
                            }
                        moves.update({**self.env.context.get('values_stock_move', {})})

                        picking_values = task._prepare_picking_values(action=action, values=values, moves=moves)
                        picking = self.env['stock.picking'].sudo().create(picking_values)
                        picking.action_assign()

                        products = task.product_ids.filtered(lambda p: p.product_id.id == moves.get('product_id', 0))
                        product = products and products[0] or False
                        if action.picking_product_lot_update:
                            if todo.picking_product_lot_id_raw and product:
                                product.write({'product_lot_id': todo.picking_product_lot_id_raw.id, 'todo_id': todo.id})
                        if action.picking_product_lot_ok:
                            for line in picking.move_line_ids:
                                line.write({
                                    'lot_id': self.env.context.get('values_stock_move_line', {}).get('lot_id', action.picking_product_lot_id.id or (product and product.product_lot_id.id) or False)
                                })
                        if action.picking_done:
                            for move in picking.move_ids:
                                move.write({'quantity': move.product_uom_qty})
                            picking.button_validate()

            elif action.type == 'action':
                active_ids = tasks.ids
                active_id = active_ids[0]
                context = {
                    'active_id': active_id,
                    'active_ids': active_ids,
                    'active_model': tasks._name,
                    'default_task_id': active_id,
                    'default_task_ids': [(6, 0, active_ids)],
                }
                result = action.action_id.with_context(**context).run()
                if result:
                    return {'action': result}

        return {}


class FsmTodoAction(models.Model):
    _name = 'fsm.todo.action'
    _description = 'Field Service Management: Todo Actions'
    _order = 'sequence'

    @api.depends('type')

    def _compute_name(self):
        types = dict(self._fields['type'].selection)
        for action in self:
            action.name = _(types.get(action.type)) if action.type else False

    @api.depends('picking_product_id')
    def _compute_picking_product_lot_ok(self):
        for action in self:
            action.picking_product_lot_ok = action.picking_product_id.tracking in ('serial', 'lot')

    todo_id = fields.Many2one('fsm.todo', ondelete='cascade', copy=False)
    flow_stage_todo_id = fields.Many2one('fsm.flow.stage.todo', ondelete='cascade', copy=False)
    name = fields.Char(compute='_compute_name')
    sequence = fields.Integer(default=10)
    type = fields.Selection([
        ('photo', 'Take Photo'),
        ('picking', 'Create Picking'),
        ('action', 'Execute Action'),
        ('stage', 'Change Stage'),
        ('code', 'Run Code'),
    ])
    code = fields.Text()
    file_size = fields.Char(string='File Size')
    file_type = fields.Char(string='File Type')
    stage_id = fields.Many2one('fsm.stage', string='Stage', related='flow_stage_id.stage_id', store=True, readonly=False)
    stage_type = fields.Selection(related='stage_id.type')
    stage_success = fields.Boolean(string='Stage Successful', default=True)
    reason_id = fields.Many2one('fsm.reason', string='Reason')
    reason_desc = fields.Text(string='Reason Description')
    flow_stage_id = fields.Many2one('fsm.flow.stage', string='Stage', domain='[("id", "in", flow_stage_ids)]')
    flow_stage_ids = fields.Many2many(related='flow_stage_todo_id.stage_id.stage_next_ids')
    picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type')
    picking_product_id = fields.Many2one('product.product', string='Picking Product', domain='[("fsm_product_type", "=", picking_product_type)]')
    picking_product_type = fields.Selection([
        ('POS', 'POS'),
        ('SIM', 'SIM'),
        ('MALZEME', 'MALZEME'),
        ('YEDEK_PARCA', 'YEDEK PARÇA'),
    ], string='Picking Product Product Type')
    picking_product_lot_id = fields.Many2one('stock.lot', string='Picking Product Lot/Serial', domain='[("product_id", "=", picking_product_id)]')
    picking_product_lot_ok = fields.Boolean(string='Picking Is Product Lot/Serial', compute='_compute_picking_product_lot_ok')
    picking_product_lot_update = fields.Boolean(string='Picking Update Serial/Lot')
    picking_create = fields.Boolean(string='Picking Create Automatically')
    picking_location_id = fields.Many2one('stock.location', string='Picking Location', domain='[("company_id", "=", picking_type_company_id)]')
    picking_location_dest_id = fields.Many2one('stock.location', string='Picking Location Destination', domain='[("company_id", "=", picking_type_company_id)]')
    picking_done = fields.Boolean(string='Picking Mark as Done')
    picking_type_company_id = fields.Many2one('res.company', related='picking_type_id.company_id')
    action_id = fields.Reference(selection=[
        ('ir.actions.report', 'Report'),
        ('ir.actions.server', 'Server'),
        ('ir.actions.client', 'Client'),
        ('ir.actions.act_url', 'Address'),
        ('ir.actions.act_window', 'Window'),
    ])

    @api.constrains('code')
    def _check_code(self):
        for action in self:
            if action.type == 'stage' and not action.stage_id:
                raise ValidationError(_('Stage field cannot be empty.'))
            elif action.type == 'picking' and not action.picking_type_id:
                raise ValidationError(_('Picking type field cannot be empty.'))
            elif action.type == 'code' and action.code:
                msg = test_python_expr(expr=action.code.strip(), mode='exec')
                if msg:
                    raise ValidationError(msg)

    @api.onchange('type')
    def onchange_type(self):
        if self.type == 'picking' and not self.picking_type_id:
            types = self.env['stock.picking.type'].sudo().search([('company_id', '=', self.env.company.id)])
            type = types.filtered(lambda t: t.code == 'internal')
            type = type[0] if type else types[0]
            self.picking_type_id = type.id

    @api.onchange('picking_type_id')
    def onchange_picking_type(self):
        if self.type == 'picking' and self.picking_type_id:
            location_customer, location_supplier = self.env['stock.warehouse']._get_partner_locations()
            self.picking_location_id = self.picking_type_id.default_location_src_id.id
            if not self.picking_location_id and self.picking_type_id.code == 'incoming':
                self.picking_location_id = location_supplier.id

            self.picking_location_dest_id = self.picking_type_id.default_location_dest_id.id
            if not self.picking_location_dest_id and self.picking_type_id.code == 'outgoing':
                self.picking_location_dest_id = location_customer.id
        else:
            self.picking_location_id = False
            self.picking_location_dest_id = False
