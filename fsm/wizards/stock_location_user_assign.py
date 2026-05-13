# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockLocationUserAssign(models.TransientModel):
    _name = 'stock.location.user.assign'
    _description = 'Field Service Management: Assign User to Location'

    line_ids = fields.One2many('stock.location.user.assign.line', 'wizard_id', string='Lines')
    type = fields.Selection([('active', 'Activate Locations'), ('archieve', 'Archieve Locations')], string='Type', default='active')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)

        lines = {}
        company = self.env.company
        users = self.env['res.users'].sudo().browse(self.env.context.get('active_ids', []))
        warehouses = self.env['fsm.project'].sudo().search([('company_id', '=', company.id)]).mapped('warehouse_ids')
        for wh in warehouses:
            lines.update({
                wh.id: {
                    'id': wh.id,
                    'name': wh.display_name,
                    'users': {
                        usr.id: {
                            'id': usr.id,
                            'name': usr.name,
                            'solid': False,
                            'faulty': False,
                            'repair': False,
                        } for usr in users
                    },
                }
            })

        locations = self.env['stock.location'].sudo().with_context(active_test=False).search([
            ('warehouse_id', 'in', warehouses.ids),
            ('fsm_user_id', 'in', users.ids),
            ('fsm_user_type', '!=', False),
            ('company_id', '=', company.id),
        ])
        for loc in locations:
            lines[loc.warehouse_id.id]['users'][loc.fsm_user_id.id][loc.fsm_user_type] = True

        line_ids = []
        for line in lines.values():
            line_ids.append((0, 0, {'display_type': 'line_section', 'name': line['name']}))
            for usr in line['users'].values():
                line_ids.append((0, 0, {
                    'name': usr['name'],
                    'user_id': usr['id'],
                    'warehouse_id': line['id'],
                    'solid': usr['solid'],
                    'faulty': usr['faulty'],
                    'repair': usr['repair'],
                }))
        res.update({'line_ids': line_ids})
        return res

    def confirm(self):
        company = self.env.company
        active = self.type == 'active'
        locations = self.env['stock.location'].sudo().with_context(active_test=False)

        for line in self.line_ids:
            if line.display_type:
                continue
            
            types = {'solid': False, 'faulty': False, 'repair': False}
            locs = locations.search([
                ('warehouse_id', '=', line.warehouse_id.id),
                ('fsm_user_id', '=', line.user_id.id),
                ('fsm_user_type', '!=', False),
                ('company_id', '=', company.id),
            ])
            for loc in locs:
                types[loc.fsm_user_type] = loc

            for key, val in types.items():
                if val:
                    val.write({'active': active})
                    if not loc.location_id:
                        val.write({'location_id': line.warehouse_id.view_location_id.id})

                elif active:
                    locations.create({
                        'name': '%s (%s)' % (line.user_id.name, _(key.capitalize())),
                        'location_id': line.warehouse_id.view_location_id.id,
                        'fsm_user_id': line.user_id.id,
                        'fsm_user_type': key,
                    })

        return {'type': 'ir.actions.act_window_close'}


class StockLocationUserAssign(models.TransientModel):
    _name = 'stock.location.user.assign.line'
    _description = 'Field Service Management: Assign User to Location Lines'

    wizard_id = fields.Many2one('stock.location.user.assign')
    warehouse_id = fields.Many2one('stock.warehouse')
    user_id = fields.Many2one('res.users')
    name = fields.Char(readonly=True)
    solid = fields.Boolean(readonly=True)
    faulty = fields.Boolean(readonly=True)
    repair = fields.Boolean(readonly=True)
    display_type = fields.Selection([('line_section', 'Section'), ('line_note', 'Note')], default=False)
