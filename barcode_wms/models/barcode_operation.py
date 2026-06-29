# -*- coding: utf-8 -*-
from odoo import models, api, _

def _value(value):
    if value:
        return [value.id, value.display_name]
    return False

def _product(product, *fields):
    values = {
        'id': product.id,
        'name': product.name,
        'type': product.type,
        'barcode': product.barcode,
        'default_code': product.default_code,
        'display_name': product.display_name,
        'weight': product.weight,
        'tracking': product.tracking,
        'qty_available': product.qty_available,
        'uom_id': _value(product.uom_id),
        'categ_id': _value(product.categ_id),
    }

    for field in fields:
        values.update({field: getattr(product, field)})
    return values


class BarcodeOperation(models.AbstractModel):
    _name = 'barcode.operation'
    _description = 'Barcode Operation'

    @api.model    
    def get_barcode_data(self, barcode):
        product, picking, location, operation = False, False, False, False

        product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1) or False
        if product:
            product = barcode
        else:
            producthy = self.env['product.product'].search([('barcode', 'like', '%%%s%%' % barcode)], limit=1)
            if (producthy):
                product = '%%%s%%' % barcode
            else:
                location = self.env['stock.location'].search([('barcode', '=', barcode)], limit=1) or False
                if location:
                    type = self.env['stock.picking.type'].search([
                        ('warehouse_id', '=', location.warehouse_id.id),
                        ('code', '=', 'internal'),
                    ], limit=1)
                    if type:
                        location = {
                            'type': type.id,
                            'value': _value(location),
                        }
                    else:
                        location = False
                else:
                    operation = self.env['stock.picking.type'].search([('barcode', '=', barcode)], limit=1) or False
                    if operation:
                        operation = {'id': operation.id}
                    else:
                        picking = self.env['stock.picking'].search([('name', '=', barcode)], limit=1) or False
                        if picking:
                            picking = {
                                'id': picking.id,
                                'type': picking.picking_type_id.id,
                            }

        return {
            'product': product,
            'picking': picking,
            'location': location,
            'operation': operation,
        }

    @api.model    
    def get_barcode_product(self, barcode):
        products = self.env['product.product'].search([
            '|', '|',
            ('name', 'ilike', barcode),
            ('barcode', 'ilike', barcode),
            ('default_code', 'ilike', barcode),
        ], limit=30)

        return [_product(product) for product in products]


class BarcodeQuantOperation(models.AbstractModel):
    _name = 'barcode.quant.operation'
    _description = 'Barcode Quant Operation'

    @api.model
    def get_data(self):
        uid = self.env.user.id
        company = self.env.company
        quants = self.env['stock.quant'].search([
            ('user_id', '=', uid),
            ('company_id', '=', company.id),
            ('inventory_quantity_set', '=', True),
            ('location_id.usage', 'in', ['internal', 'transit']),
        ])
        lines = [{
            'location_id': _value(quant.location_id),
            'product_id': quant.product_id._get_barcode_data(),
            'user_id': quant.user_id.id,
            'id': quant.id,
            'qty': quant.quantity,
            'number': quant.lot_id.name,
            'qty_done': quant.inventory_quantity,
        } for quant in quants]

        warehouses = [{
            'warehouse': _value(warehouse),
            'locations': [_value(location) for location in warehouse.internal_location_ids],
        } for warehouse in self.env['stock.warehouse'].search([('company_id', '=', company.id)])]

        locations = []
        for warehouse in warehouses:
            locations.extend(warehouse['locations'])

        return {
            'user': uid,
            'company': company.id,
            'warehouses': warehouses,
            'locations': locations,
            'lines': lines,
            'groups': {
                'group_uom': self.env.user.has_group('uom.group_uom'),
                'group_stock_user': self.env.user.has_group('stock.group_stock_user'),
                'group_tracking_lot': self.env.user.has_group('stock.group_tracking_lot'),
                'group_multi_company': self.env.user.has_group('base.group_multi_company'),
                'group_stock_manager': self.env.user.has_group('stock.group_stock_manager'),
                'group_production_lot': self.env.user.has_group('stock.group_production_lot'),
                'group_tracking_owner': self.env.user.has_group('stock.group_tracking_owner'),
            },
        }

    @api.model
    def get_location_data(self, product_id, location_id, package_id):
        company_id = self.env.company.id
        domain = [
            ('location_id', '=', location_id),
            ('product_id', '=', product_id),
            ('company_id', '=', company_id),
            ('lot_id', '=', False)
        ]
        if package_id:
            domain.append(('package_id', '=', package_id))

        data = {}
        quants = self.env['stock.quant'].search(domain)
        if len(quants) == 1:
            line = quants[0]
            data = {
                'product_id': line.product_id._get_barcode_data(),
                'id': line.id,
                'user_id': line.user_id.id,
                'qty': line.quantity,
                'qty_done': line.inventory_quantity,
            }

        return data

    @api.model
    def get_package_data(self, barcode, location_id):
        company_id = self.env.company.id

        domain = [
            ('package_id.name', '=', barcode),
            ('company_id', '=', company_id),
        ]
        if location_id:
            domain.append(('location_id', '=', location_id))

        quant = self.env['stock.quant'].search(domain, limit=1)
        if not quant:
            return {}

        return {
            'product_id': quant.product_id.id,
            'package_id': quant.package_id.id,
            'quantity': quant.quantity
        }

    @api.model    
    def print_barcode_line(self, name):
        package = self.env['stock.quant.package'].search([('name', '=', name)])
        if package:
            return self.env.ref('stock.action_report_quant_package_barcode_small').report_action(package)


class BarcodeTransferOperation(models.AbstractModel):
    _name = 'barcode.transfer.operation'
    _description = 'Barcode Transfer Operation'

    @api.model
    def get_data(self, type):
        domain = [('id', '=', type)] if type else []
        operations = self.env['stock.picking.type'].search_read(domain, ['id', 'default_location_src_id', 'default_location_dest_id', 'display_name', 'name', 'warehouse_id'], limit=100)

        picking = self.env['stock.picking'].search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id),
            ('state', 'not in', ('done', 'cancel')),
        ], limit=1, order='id desc')
        moves = []
        if picking:
            for move in picking.move_line_ids:
                moves.append({
                    'id': move.id,
                    'display_name': move.display_name,
                    'qty': move.quantity,
                    'qty_done': move.quantity if move.picked else 0,
                    'location_id': _value(move.location_id),
                    'location_dest_id': _value(move.location_dest_id),
                    'package_id': _value(move.package_id),
                    'result_package_id': _value(move.result_package_id),
                    'number': move.lot_id.name if picking.picking_type_id.use_existing_lots else move.lot_name,
                    'product_id': _product(move.product_id),
                })

        return {
            'picking': {
                'id': picking.id,
                'state': picking.id,
                'type': picking.picking_type_id.id,
                'moves': moves,
            },
            'operations': operations,
        }

    @api.model
    def get_barcode_data(self, barcode):
        product, number, location, operation, packaging = False, False, False, False, False

        product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1) or False
        if product:
            product = _product(product)
        else:
            number = self.env['stock.lot'].search([('name', '=', barcode)], limit=1) or False
            if (number):
                product = _product(number.product_id)
                number = barcode
            else:
                location = self.env['stock.location'].search([('barcode', '=', barcode)], limit=1) or False
                if location:
                    location = _value(location)
                else:
                    operation = self.env['stock.picking.type'].search([('barcode', '=', barcode)], limit=1) or False
                    if operation:
                        operation = {
                            'id': operation.id,
                            'name': operation.name,
                            'display_name': operation.display_name,
                            'src': operation.default_location_src_id.id,
                            'dest': operation.default_location_dest_id.id,
                            'warehouse_id': _value(operation.warehouse_id),
                        }
                    else:
                        packaging = self.env['stock.quant.package'].search([('name', '=', barcode)], limit=1) or False
                        if packaging:
                            packaging = [{
                                'id': pack.package_id.id,
                                'name': pack.package_id.name,
                                'line': pack.id,
                                'qty': pack.quantity,
                                'number': pack.lot_id.name,
                                'product': _product(pack.product_id),
                            } for pack in packaging.quant_ids]

        return {
            'product': product,
            'number': number,
            'location': location,
            'operation': operation,
            'packaging': packaging,
        }

    @api.model
    def get_operation_data(self, operation_type_id):
        user_id = self.env.user.id
        company_id = self.env.company.id
        default_location_id = []
        default_location_dest_id = []

        operation_type = self.env['stock.picking.type'].search([('id', '=', operation_type_id)])
        if operation_type:
            if operation_type.default_location_src_id:
                location_id = _value(operation_type.default_location_src_id)
            else:
                location_id = []

            if operation_type.default_location_dest_id:
                location_dest_id = _value(operation_type.default_location_dest_id)
            else:
                location_dest_id = []

            location_ids = [_value(location) for location in operation_type.default_location_src_id.warehouse_id.internal_location_ids]
            location_dest_ids = [_value(location) for location in operation_type.default_location_dest_id.warehouse_id.internal_location_ids]

            if operation_type.code == 'incoming':
                if operation_type.default_location_src_id:
                    default_location_id = _value(operation_type.default_location_src_id)
                else:
                    customer_location_id, supplier_location_id = self.env['stock.warehouse']._get_partner_locations()
                    default_location_id = _value(supplier_location_id)
                default_location_dest_id = _value(operation_type.default_location_dest_id)
            elif operation_type.code == 'outgoing':
                if operation_type.default_location_dest_id:
                    default_location_dest_id = _value(operation_type.default_location_dest_id)
                else:
                    customer_location_id, supplier_location_id = self.env['stock.warehouse']._get_partner_locations()
                    default_location_dest_id = _value(customer_location_id)
                default_location_id = _value(operation_type.default_location_src_id)
            elif operation_type.code == 'internal':
                if not self.user_has_groups('stock.group_stock_multi_locations'):
                    return {
                        'warning': {
                            'message': _('You need to activate storage locations to be able to do internal operation types.')
                        }
                    }
                else:
                    default_location_id = _value(operation_type.default_location_src_id)
                    default_location_dest_id = _value(operation_type.default_location_dest_id)

            groups = {
                'group_uom': self.env.user.has_group('uom.group_uom'),
                'group_stock_user': self.env.user.has_group('stock.group_stock_user'),
                'group_tracking_lot': self.env.user.has_group('stock.group_tracking_lot'),
                'group_multi_company': self.env.user.has_group('base.group_multi_company'),
                'group_stock_manager': self.env.user.has_group('stock.group_stock_manager'),
                'group_production_lot': self.env.user.has_group('stock.group_production_lot'),
                'group_tracking_owner': self.env.user.has_group('stock.group_tracking_owner'),
            }

            return {
                'groups': groups,
                'user_id': user_id,
                'company_id': company_id,
                'location_id': location_id or default_location_id,
                'location_dest_id': location_dest_id or default_location_dest_id,
                'location_ids': location_ids or [default_location_id],
                'location_dest_ids': location_dest_ids or [default_location_dest_id],
                'settings': {
                    'edit_package': self.env.user.has_group('stock.group_tracking_lot'),
                },
            }


class BarcodeWarehouseOperation(models.AbstractModel):
    _name = 'barcode.warehouse.operation'
    _description = 'Barcode Warehouse Operation'

    @api.model
    def get_barcode_data(self, barcode):
        product, number, location, operation, packaging, packing = False, False, False, False, False, False

        product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1) or False
        if product:
            product = _product(product)
        else:
            number = self.env['stock.lot'].search([('name', '=', barcode)], limit=1) or False
            if (number):
                product = _product(number.product_id)
                number = barcode
            else:
                location = self.env['stock.location'].search([('barcode', '=', barcode)], limit=1) or False
                if location:
                    location = _value(location)
                else:
                    operation = self.env['stock.picking.type'].search([('barcode', '=', barcode)], limit=1) or False
                    if operation:
                        operation = {
                            'id': operation.id,
                            'name': operation.name,
                            'display_name': operation.display_name,
                            'src': operation.default_location_src_id.id,
                            'dest': operation.default_location_dest_id.id,
                            'warehouse_id': _value(operation.warehouse_id),
                        }
                    else:
                        packing = self.env['product.packaging'].search([('barcode', '=', barcode)], limit=1) or False
                        if packing:
                            packing = {
                                'id': packing.id,
                                'qty': packing.qty,
                                'pid': packing.product_id.id,
                            }
                        else:
                            packaging = self.env['stock.quant.package'].search([('name', '=', barcode)], limit=1) or False
                            if packaging:
                                packaging = [{
                                    'id': pack.package_id.id,
                                    'name': pack.package_id.name,
                                    'line': pack.id,
                                    'qty': pack.quantity,
                                    'number': pack.lot_id.name,
                                    'product': _product(pack.product_id),
                                } for pack in packaging.quant_ids]

        return {
            'product': product,
            'number': number,
            'location': location,
            'operation': operation,
            'packaging': packaging,
            'packing': packing,
        }
    
    @api.model
    def get_operations(self):
        operations = []
        types = self.env['stock.picking.type'].read_group(domain=[], fields=[], groupby=['warehouse_id'], lazy=False)
        warehouse = False
        for type in types:
            if type.get('warehouse_id', False) and len(type.get('warehouse_id')) > 1:
                warehouse = self.env['stock.warehouse'].search([
                    ('id', '=', type['warehouse_id'][0]),
                    '|', ('user_ids', 'in', [self.env.user.id]), ('user_ids', '=', False)
                ])
            else:
                continue
            if not warehouse:
                continue

            ptypes = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', type['warehouse_id'][0])
            ])
            operations.append({
                'id': warehouse.id,
                'warehouse': _value(warehouse),
                'types': [{
                    'id': ptype.id,
                    'name': ptype.name,
                    'display_name': ptype.display_name,
                    'warehouse_id': ptype.warehouse_id.id,
                    'count': ptype.count_picking,
                    'draft': ptype.count_picking_draft,
                    'late': ptype.count_picking_late,
                    'ready': ptype.count_picking_ready,
                    'waiting': ptype.count_picking_waiting,
                    'backorder': ptype.count_picking_backorders,
                    'src': ptype.default_location_src_id.id,
                    'dest': ptype.default_location_dest_id.id,
                } for ptype in ptypes],
            })
        return operations

    @api.model
    def get_pickings(self, picking_id):
        picking = self.env['stock.picking'].browse(picking_id)
        type = picking.picking_type_id
        if type.code == 'internal':
            if not self.user_has_groups('stock.group_stock_multi_locations'):
                return {
                    'warning': {
                        'message': _('You need to activate storage locations to be able to do internal operation types.'),
                    }
                }

        location_id = _value(picking.location_id)
        location_dest_id = _value(picking.location_dest_id)
        location_ids = [_value(location) for location in type.default_location_src_id.child_internal_location_ids]
        location_dest_ids = [_value(location) for location in type.default_location_dest_id.child_internal_location_ids]

        if type.barcode_lot_create_method == 'block':
            if type.code == 'incoming':
                move_ids = picking.move_line_nosuggest_ids
            else:
                move_ids = picking.move_line_ids
        else:
            move_ids = picking.move_line_ids

        moves = [{
            'id': move_id.id,
            'display_name': move_id.display_name,
            'qty': move_id.quantity,
            'qty_done': move_id.quantity if move_id.picked else 0,
            'location_id': _value(move_id.location_id),
            'location_dest_id': _value(move_id.location_dest_id),
            'package_id': _value(move_id.package_id),
            'result_package_id': _value(move_id.result_package_id),
            'number': move_id.lot_id.name if picking.picking_type_id.use_existing_lots else move_id.lot_name,
            'product_id': _product(move_id.product_id),
        } for move_id in move_ids]

        reports = self.env['ir.actions.report'].search([('model', '=', 'stock.picking')])
        reports =  [{
            'id': report.id,
            'name': report.name,
            'report_name': report.report_name,
        } for report in reports]

        return {
            'picking': {
                'id': picking.id,
                'name': picking.name,
                'state': picking.state,
            },
            'operation': {
                'id': type.id,
                'lot': type.use_existing_lots,
                'src': type.default_location_src_id.id,
                'dest': type.default_location_dest_id.id
            },
            'packages': [[pack.id, pack.name] for pack in (picking.move_line_ids.mapped('result_package_id') | picking.move_line_ids.mapped('package_id'))],
            'moves': moves,
            'reports': reports,
            'location_id': location_id,
            'location_ids': location_ids or [location_id],
            'location_dest_id': location_dest_id,
            'location_dest_ids': location_dest_ids or [location_dest_id],
            'settings': {
                'edit_location': True,
                'lot_create_method': type.barcode_lot_create_method,
                'line_create_method': type.barcode_lot_create_method,
                'save_before_closing': self.env.company.barcode_save_before_closing,
            },
            'groups': {
                'group_tracking_lot': self.env.user.has_group('stock.group_tracking_lot'),
                'group_production_lot': self.env.user.has_group('stock.group_production_lot'),
                'group_stock_user': self.env.user.has_group('stock.group_stock_user'),
                'group_stock_manager': self.env.user.has_group('stock.group_stock_manager'),
            }
        }


class BarcodeInventoryOperation(models.AbstractModel):
    _name = 'barcode.inventory.operation'
    _description = 'Barcode Inventory Operation'

    @api.model
    def get_barcode_data(self, barcode):
        product, number, location, packaging = False, False, False, False

        product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1) or False
        if product:
            product = _product(product)
        else:
            number = self.env['stock.lot'].search([('name', '=', barcode)], limit=1) or False
            if (number):
                product = _product(number.product_id.with_context(lot_id=barcode))
                number = barcode
            else:
                location = self.env['stock.location'].search([('barcode', '=', barcode)], limit=1) or False
                if location:
                    location = _value(location)
                else:
                    packaging = self.env['product.packaging'].search([('barcode', '=', barcode)], limit=1) or False
                    if packaging:
                        packaging = {
                            'id': packaging.id,
                            'qty': packaging.qty,
                            'pid': packaging.product_id.id,
                        }

        return {
            'product': product,
            'number': number,
            'location': location,
            'packaging': packaging,
        }
    
