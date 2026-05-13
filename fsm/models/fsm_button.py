# -*- coding: utf-8 -*-

from pytz import timezone

from odoo import models, fields, api, tools, Command, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval, test_python_expr


class FsmButton(models.Model):
    _name = 'fsm.button'
    _description = 'Field Service Management: Buttons'
    _order = 'sequence'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    description = fields.Text()
    custom_theme = fields.Selection([
        ('secondary', 'Secondary'),
        ('primary', 'Primary'),
        ('dark', 'Dark'),
        ('light', 'Light'),
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('danger', 'Danger'),
    ], default='secondary', string='Theme')
    custom_class = fields.Char(string='Class')
    custom_style = fields.Text(string='Style')
    visible_ok = fields.Boolean(string='Always Visible', default=True)
    visible_code = fields.Text(string='Visibility Condition')
    group_ids = fields.Many2many('res.groups', 'fsm_button_group_rel', 'button_id', 'group_id', string='Groups')
    action_ids = fields.One2many('fsm.button.action', 'button_id', 'Actions', copy=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def _run_action(self, tasks, actions=None):
        tasks = tasks.sudo()
        defaults = self.env.context.get('defaults', {})
        if not actions:
            actions = self.action_ids

        for action in actions:
            action_id = str(action.id)

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
                        'Command': Command,
                        'UserError': UserError,
                    }
                    safe_eval(action.code.strip(), context, mode='exec', nocopy=True)
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
                        tasks.with_context(no_reason=action_id in defaults).with_context(**{
                            'default_stage_success_readonly': True,
                            'default_stage_success': action.stage_success,
                            'default_reason_desc': action.reason_desc,
                            'default_button_action_id': action.id,
                        }).write({
                            'flow_stage_id': action.flow_stage_id.id,
                        })
                else:
                    if action.reason_id:
                        tasks.with_context(no_reason=True).write({
                            'flow_stage_id': action.flow_stage_id.id,
                            'reason_id': action.reason_id.id,
                        })
                    else:
                        if action_id in defaults:
                            active_ids = tasks.ids
                            active_id = active_ids[0]
                            context = {
                                'active_id': active_id,
                                'active_ids': active_ids,
                                'active_model': tasks._name,
                                'default_task_id': active_id,
                                'default_task_ids': [(6, 0, active_ids)],
                                'default_button_action_id': action.id,
                            }
                            wizard = self.env['fsm.stage.reason'].with_context(**context).create({
                                **defaults[action_id],
                                'button_action_id': False,
                            })
                            wizard.confirm()
                        else:
                            tasks.with_context(**{
                                'defaults': defaults,
                                'default_reason_desc': action.reason_desc,
                                'default_button_action_id': action.id,
                            }).write({
                                'flow_stage_id': action.flow_stage_id.id,
                            })

            elif action.type == 'picking':
                for task in tasks:
                    commit = False
                    picking = False
                    carrier_id = action.picking_carrier_id.id
                    if action.picking_carrier_ok and not carrier_id:
                        carrier_id = self.env.context.get('carrier_id')
                        if not carrier_id:
                            return {
                                'action': {
                                    'type': 'ir.actions.act_window',
                                    'name': _('Select Delivery Carrier'),
                                    'res_model': 'fsm.task.delivery.select',
                                    'views': [(False, 'form')],
                                    'target': 'new',
                                    'context': {
                                        'default_button_id': self.id,
                                        'default_task_ids': [(6, 0, tasks.ids)],
                                    },
                                }
                            }

                    values = {'carrier_id': carrier_id}
                    moves = {}
                    if action.picking_product_id:
                        moves = {
                            'name': action.picking_product_id.name,
                            'product_id': action.picking_product_id.id,
                            'product_uom_qty': 1,
                        }
                    picking_values = task._prepare_picking_values(action=action, values=values, moves=moves)
                    if action.picking_return_ok:
                        if action_id in defaults:
                            if defaults[action_id] is None:
                                continue

                            picking_values.update(defaults[action_id])
                            picking = self.env['stock.picking'].sudo().create(picking_values)
                            commit = True
                            defaults[action_id] = None
                        else:
                            self.env.cr.rollback()
                            picking = self.env['stock.picking'].sudo().new({**picking_values, 'state': 'done'})
                            return_picking = self.env['stock.return.picking'].sudo().with_context(picking=picking).create({
                                'fsm_button_action_id': action.id,
                                'fsm_task_id': task.id,
                                'picking_id': picking.id,
                            })
                            return_picking._onchange_picking_id()
                            return {
                                'action': {
                                    'type': 'ir.actions.act_window',
                                    'name': _('Prepare Return'),
                                    'res_model': 'stock.return.picking',
                                    'res_id': return_picking.id,
                                    'views': [(False, 'form')],
                                    'target': 'new',
                                }
                            }
                    else:
                        picking = self.env['stock.picking'].sudo().create(picking_values)

                    if picking:
                        picking.action_assign()

                        product = task.product_ids and task.product_ids[0] or False
                        if product and not task.flow_id.misc_use_material_product:
                            for line in picking.move_line_ids:
                                line.write({'lot_id': product.product_lot_id.id})
                        if action.picking_done:
                            for move in picking.move_ids:
                                move.write({'quantity': move.product_uom_qty})
                            picking.button_validate()
                        action._postprocess_picking(task, picking)

                    if commit:
                        self.env.cr.commit()

            elif action.type == 'action':
                active_ids = tasks.ids
                active_id = active_ids[0]
                context = {
                    'active_id': active_id,
                    'active_ids': active_ids,
                    'active_model': tasks._name,
                    'default_task_id': active_id,
                    'default_task_ids': [(6, 0, active_ids)],
                    'default_button_action_id': action.id,
                }
                if action.action_id._name == 'ir.actions.report':
                    result = action.action_id.with_context(**context).report_action(active_ids)
                else:
                    result = action.action_id.with_context(**context).run()
                if result:
                    if action_id in defaults:
                        wizard = self.env[result['res_model']].with_context(**context).create({
                            **defaults[action_id],
                            'button_action_id': False,
                        })
                        wizard.confirm()
                        continue

                    self.env.cr.rollback()
                    result['context'] = {
                        **context,
                        **result.get('context', {}),
                    }

                    return {'action': result}

        return {'type': 'fsm.reload'}
        #return {'type': 'ir.actions.client', 'tag': 'reload'}


class FsmButtonAction(models.Model):
    _name = 'fsm.button.action'
    _description = 'Field Service Management: Button Actions'
    _order = 'sequence'

    @api.depends('type')
    def _compute_name(self):
        types = dict(self._fields['type'].selection)
        for action in self:
            action.name = _(types.get(action.type))

    button_id = fields.Many2one('fsm.button', ondelete='cascade', copy=False)
    flow_stage_button_id = fields.Many2one('fsm.flow.stage.button', ondelete='cascade', copy=False)
    name = fields.Char(compute='_compute_name')
    sequence = fields.Integer(default=10)
    type = fields.Selection([
        ('stage', 'Change Stage'),
        ('picking', 'Create Picking'),
        ('action', 'Execute Action'),
        ('code', 'Run Code'),
    ], required=True, default='code')
    code = fields.Text()
    stage_id = fields.Many2one('fsm.stage', string='Stage', related='flow_stage_id.stage_id', store=True, readonly=False)
    stage_type = fields.Selection(related='stage_id.type')
    stage_success = fields.Boolean(string='Stage Successful', default=True)
    reason_id = fields.Many2one('fsm.reason', string='Reason')
    reason_desc = fields.Text(string='Reason Description')
    flow_stage_id = fields.Many2one('fsm.flow.stage', string='Stage', domain='[("id", "in", flow_stage_ids)]')
    flow_stage_ids = fields.Many2many(related='flow_stage_button_id.stage_id.stage_next_ids')
    picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type')
    picking_product_id = fields.Many2one('product.product', string='Picking Product')
    picking_location_id = fields.Many2one('stock.location', string='Picking Location', domain='[("company_id", "=", picking_type_company_id)]')
    picking_location_dest_id = fields.Many2one('stock.location', string='Picking Location Destination', domain='[("company_id", "=", picking_type_company_id)]')
    picking_return_ok = fields.Boolean(string='Picking Return')
    picking_carrier_ok = fields.Boolean(string='Picking With Delivery Carrier')
    picking_carrier_id = fields.Many2one('delivery.carrier', string='Picking Delivery Carrier', domain='[("delivery_type", "not in", ("fixed", "base_on_rule"))]')
    picking_carrier_type = fields.Selection(related='picking_carrier_id.delivery_type')
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

    def _postprocess_picking(self, task, picking):
        pass

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
