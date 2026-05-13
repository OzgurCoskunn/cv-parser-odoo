# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockBarcodeInventory(models.Model):
    _name = 'stock.barcode.inventory'
    _description = 'Stock Barcode Inventory Adjustments'
    _rec_name = 'create_date'

    @api.depends('done')
    def _compute_state(self):
        for inv in self:
            inv.state = 'done' if inv.done else 'draft'

    done = fields.Boolean()
    state = fields.Selection([('draft', 'Ongoing'), ('done', 'Done')], compute='_compute_state')
    location_id = fields.Many2one('stock.location', required=True)
    line_ids = fields.One2many('stock.barcode.inventory.line', 'inventory_id', 'Lines')

    def _compute_display_name(self):
        for record in self:
            record.display_name = '%s/#%s - %s (%s)' % (
                record.location_id.display_name,
                record.id,
                record.create_date.strftime('%d/%m/%Y %H:%M:%S'),
                _('Done') if record.done else _('Ongoing'),
            )

    def action_validate(self):
        action = self.env.ref('barcode_wms.action_inventory_wizard').read()[0]
        action['name'] = _('Adjustment Validation')
        action['context'] = {'default_inventory_id': self.id, 'default_type': 'validate', 'dialog_size': 'small'}
        return action

    def action_remove(self):
        action = self.env.ref('barcode_wms.action_inventory_wizard').read()[0]
        action['name'] = _('Adjustment Removal')
        action['context'] = {'default_inventory_id': self.id, 'default_type': 'remove', 'dialog_size': 'small'}
        return action

    def validate(self):
        if self.done:
            raise ValidationError(_('This inventory operation has already been validated'))

        location = self.location_id
        products = self.line_ids.mapped('product_id').ids

        quants = self.env['stock.quant'].search([('product_id', 'in', products), ('location_id', '=', location.id)])
        products = quants.mapped('product_id').ids

        lines = self.env['stock.barcode.inventory.line'].read_group([('inventory_id', '=', self.id)], ['quantity:sum'], ['product_id'])
        for line in lines:
            if line['product_id'][0] not in products:
                quants |= quants.create({
                    'product_id': line['product_id'][0],
                    'location_id': location.id,
                    'quantity': 0,
                    'lot_id': False,
                    'package_id': False,
                    'owner_id': False,
                    'in_date': fields.Datetime.now(),
                })
        del products

        lines = {line['product_id'][0]: line['quantity'] for line in lines}
        for quant in quants:
            quant.inventory_quantity += lines[quant.product_id.id]
        self.done = True


class StockBarcodeInventoryLine(models.Model):
    _name = 'stock.barcode.inventory.line'
    _description = 'Stock Barcode Inventory Adjustment Lines'
    _order = 'id desc'

    @api.depends('location_id', 'product_id')
    def _compute_onhand(self):
        quants = self.env['stock.quant']
        for line in self:
            quant = quants.search([('location_id', '=', line.location_id.id), ('product_id', '=', line.product_id.id)], limit=1)
            line.onhand = quant.quantity if quant else 0

    @api.depends('inventory_id.done')
    def _compute_state(self):
        for line in self:
            line.state = False if not line.inventory_id else 'done' if line.inventory_id.done else 'draft'

    inventory_id = fields.Many2one('stock.barcode.inventory', ondelete='cascade', required=True, readonly=True)
    location_id = fields.Many2one('stock.location', related='inventory_id.location_id', store=True)
    state = fields.Selection([('draft', 'Ongoing'), ('done', 'Done')], compute='_compute_state')
    product_id = fields.Many2one('product.product', required=True)
    barcode = fields.Char(related='product_id.barcode', store=True)
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id')
    quantity = fields.Float()
    onhand = fields.Float(string='On Hand', compute='_compute_onhand')

    def remove(self):
        self.unlink()
        return {'type': 'stock.barcode.inventory.line.reload'}

    @api.model
    def append(self, values):
        inventory = self.env['stock.barcode.inventory'].browse(values[0]['inventory_id'])
        if inventory.done:
            inventory = self.env['stock.barcode.inventory'].create({'location_id': inventory.location_id.id})
            for value in values:
                value['inventory_id'] = inventory.id
        line = self.create(values)
        return line.inventory_id.id


class StockBarcodeInventoryLineReload(models.AbstractModel):
    _name = 'stock.barcode.inventory.line.reload'
    _description = 'Stock Barcode Inventory Line Reload'

    def _get_readable_fields(self):
        return {}


class StockBarcodeInventoryWizard(models.TransientModel):
    _name = 'stock.barcode.inventory.wizard'
    _description = 'Stock Barcode Inventory Adjustment Wizard'

    inventory_id = fields.Many2one('stock.barcode.inventory')
    type = fields.Char()

    def validate(self):
        self.inventory_id.validate()
        return {'type':'ir.actions.act_window_close'}

    def remove(self):
        self.inventory_id.unlink()
        return {'type':'ir.actions.act_window_close'}
