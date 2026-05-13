# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    barcode_lot_create_method = fields.Selection([
        ('no', 'None'),
        ('warning', 'Warning'),
        ('block', 'Block'),
    ], string='Barcode Operations Lot Creation Method', default='no')
    barcode_show_all_lines = fields.Boolean('Show All Lines in Barcode Wms', default=False)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if self.env.context.get('quick_validate'):
            for r in res:
                r.button_validate()
        return res

    def save_barcode_data(self, values):
        ready = True
        if not self:
            ready = False
            self = self.create({
                'location_id': values.get('src', False),
                'location_dest_id': values.get('dest', False),
                'picking_type_id': values.get('type', False),
                'immediate_transfer': True,
            })

        move_line_ids = []
        use_existing_lots = self.picking_type_id.use_existing_lots
        lines = values.get('lines', [])
        for line in lines:
            if line['number']:
                if use_existing_lots:
                    line['lot_id'] = self.env['stock.lot'].search([
                        ('name', '=', line['number']),
                        ('product_id', '=', line['product_id']['id']),
                    ], limit=1).id
                    line['lot_name'] = False
                else:
                    line['lot_id'] = False
                    line['lot_name'] = line['number']
                del line['number']
            else:
                line['lot_name'] = False
                line['lot_id'] = False

        lines = {line['id']: line for line in lines}
        for line in self.move_line_ids:
            if line.id in lines:
                move_line_ids.append((1, line.id, {
                    'location_id': lines[line.id]['location_id'][0],
                    'location_dest_id': lines[line.id]['location_dest_id'][0],
                    'lot_id': lines[line.id]['lot_id'],
                    'lot_name': lines[line.id]['lot_name'],
                    'qty_done': lines[line.id]['qty_done'],
                    'package_id': lines[line.id]['package_id'] and lines[line.id]['package_id'][0],
                    'result_package_id': lines[line.id]['result_package_id'] and lines[line.id]['result_package_id'][0],
                }))
                del lines[line.id]
            else:
                move_line_ids.append((2, line.id, 0))

        for line in lines.values():
            move_line_ids.append((0, 0, {
                'product_id': lines[line['id']]['product_id']['id'],
                'product_uom_id': lines[line['id']]['product_id']['uom_id'][0],
                'location_id': lines[line['id']]['location_id'][0],
                'location_dest_id': lines[line['id']]['location_dest_id'][0],
                'lot_id': lines[line['id']]['lot_id'],
                'lot_name': lines[line['id']]['lot_name'],
                'qty_done': lines[line['id']]['qty_done'],
                'package_id': lines[line['id']]['package_id'] and lines[line['id']]['package_id'][0],
                'result_package_id': lines[line['id']]['result_package_id'] and lines[line['id']]['result_package_id'][0],
            }))

        self.move_line_ids = move_line_ids

        if not ready:
            self.action_confirm()
        if values.get('validate'):
            return self.button_validate()
        return self.id

    def print_barcode_report(self, report_id):
        return self.env['ir.actions.report'].browse(report_id).report_action(self)
