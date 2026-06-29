# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # Computed fields for barcode form view
    product_reference_code = fields.Char(
        string='Product Reference',
        compute='_compute_product_info',
        readonly=True,
        store=False
    )
    
    formatted_product_barcode = fields.Char(
        string='Product Barcode',
        compute='_compute_product_info',
        readonly=True,
        store=False
    )
    
    image_1920 = fields.Image(
        string='Product Image',
        related='product_id.image_1920',
        readonly=True,
        store=False
    )
    
    product_stock_quant_ids = fields.One2many(
        comodel_name='stock.quant',
        inverse_name='id',
        string='Stock Quants',
        compute='_compute_product_stock_quants',
        readonly=True,
        store=False
    )
    
    hide_lot_name = fields.Boolean(
        string='Hide Lot Name',
        compute='_compute_lot_visibility',
        readonly=True,
        store=False
    )
    
    hide_lot = fields.Boolean(
        string='Hide Lot',
        compute='_compute_lot_visibility',
        readonly=True,
        store=False
    )
    
    tracking = fields.Selection(
        string='Tracking',
        related='product_id.tracking',
        readonly=True,
        store=False
    )
    
    state = fields.Selection(
        string='State',
        related='move_id.state',
        readonly=True,
        store=False
    )
    
    outermost_result_package_id = fields.Many2one(
        comodel_name='stock.package',
        string='Outermost Destination Package',
        help='The outermost package containing the result package (for nested packages)'
    )
    
    parent_location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Parent Source Location',
        related='picking_id.location_id',
        readonly=True,
        store=False,
        help='Parent location for source location domain'
    )
    
    parent_location_dest_id = fields.Many2one(
        comodel_name='stock.location',
        string='Parent Destination Location',
        related='picking_id.location_dest_id',
        readonly=True,
        store=False,
        help='Parent location for destination location domain'
    )
    
    qty_done = fields.Float(
        string='Done',
        compute='_compute_qty_done',
        inverse='_inverse_qty_done',
        digits='Product Unit of Measure',
        help='Quantity done (computed from quantity field for Odoo 19 compatibility)'
    )
    
    lot_properties = fields.Properties(
        string='Lot/Serial Properties',
        definition='product_id.lot_properties_definition',
        copy=False,
        help='Properties associated with the lot/serial number'
    )
    
    reserved_uom_qty = fields.Float(
        string='Reserved Quantity',
        related='move_id.product_uom_qty',
        readonly=True,
        store=False,
        help='Reserved quantity from the stock move'
    )

    @api.depends('product_id', 'product_id.default_code', 'product_id.barcode')
    def _compute_product_info(self):
        """Compute product reference code and formatted barcode"""
        for line in self:
            line.product_reference_code = line.product_id.default_code or ''
            line.formatted_product_barcode = line.product_id.barcode or ''

    @api.depends('product_id', 'location_id', 'lot_id', 'owner_id', 'package_id')
    def _compute_product_stock_quants(self):
        """Compute available stock quants for the product in relevant locations"""
        for line in self:
            if not line.product_id or not line.location_id:
                line.product_stock_quant_ids = False
                continue
            
            # Find quants for this product in the same location or child locations
            domain = [
                ('product_id', '=', line.product_id.id),
                ('location_id', 'child_of', line.location_id.id),
                ('quantity', '>', 0),
            ]
            
            # Filter by lot if specified
            if line.lot_id:
                domain.append(('lot_id', '=', line.lot_id.id))
            
            # Filter by owner if specified
            if line.owner_id:
                domain.append(('owner_id', '=', line.owner_id.id))
            
            # Filter by package if specified
            if line.package_id:
                domain.append(('package_id', '=', line.package_id.id))
            
            quants = self.env['stock.quant'].search(domain, order='quantity desc')
            line.product_stock_quant_ids = quants

    @api.depends('product_id', 'product_id.tracking', 'lot_id', 'lot_name')
    def _compute_lot_visibility(self):
        """Compute lot field visibility based on tracking and existing values"""
        for line in self:
            # Hide lot fields if product has no tracking
            if not line.product_id or line.product_id.tracking == 'none':
                line.hide_lot_name = True
                line.hide_lot = True
                continue
            
            # For products with tracking:
            # - hide_lot_name: hide the lot_name field (for creating new lots)
            #   Show it only when we need to create a new lot (incoming operations)
            # - hide_lot: hide the lot_id field (for selecting existing lots)
            #   Show it only when selecting from existing lots (outgoing/internal operations)
            
            picking_code = line.picking_id.picking_type_id.code if line.picking_id else False
            
            # Show lot_name for incoming, hide for outgoing/internal
            line.hide_lot_name = picking_code not in ['incoming', False]
            
            # Show lot_id for outgoing/internal, hide for incoming
            line.hide_lot = picking_code in ['incoming', False]
    
    @api.depends('quantity')
    def _compute_qty_done(self):
        """Compute qty_done from quantity for Odoo 19 compatibility"""
        for line in self:
            line.qty_done = line.quantity
    
    def _inverse_qty_done(self):
        """Set quantity when qty_done is changed"""
        for line in self:
            line.quantity = line.qty_done
