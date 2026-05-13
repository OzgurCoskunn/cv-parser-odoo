from odoo import http
from odoo.http import request

class StockBarcodeController(http.Controller):

    @http.route('/odoo/barcode', type='http', auth='user')
    def master_data_import(self, **kw):
        return request.redirect('/web#action=barcode_wms.barcode_wms_action_main_menu&model=stock.quant')

    @http.route('/barcode_wms/get_main_menu_data', type='json', auth='user')
    def get_main_menu_data(self):
        return {
            'groups': {
                'locations': request.env.user.has_group('stock.group_stock_multi_locations'),
                'package': request.env.user.has_group('stock.group_tracking_lot'),
                'tracking': request.env.user.has_group('stock.group_production_lot'),
            },
            'quant_count': request.env['stock.quant'].search_count([('user_id', '=', request.env.user.id), ('location_id.usage', '=', 'internal')]),
            'play_sound': True, # Or fetch from config
        }

    @http.route('/barcode_wms/scan_from_main_menu', type='jsonrpc', auth='user')
    def scan_from_main_menu(self, barcode):
        picking = request.env['stock.picking'].search([('name', '=', barcode)], limit=1)
        if picking:
            action = request.env['ir.actions.actions']._for_xml_id('barcode_wms.barcode_wms_picking_client_action')
            action['xml_id'] = 'barcode_wms.barcode_wms_picking_client_action'
            # Handle context - can be string or dict
            ctx = action.get('context', {})
            if isinstance(ctx, str):
                import ast
                action_context = ast.literal_eval(ctx) if ctx else {}
            else:
                action_context = dict(ctx or {})
            action_context.update({'active_id': picking.id})
            action['context'] = action_context
            return {'action': action}

        location = request.env['stock.location'].search([
            '|',
            ('barcode', '=', barcode),
            ('name', '=', barcode),
        ], limit=1)
        if location:
            action = request.env['ir.actions.actions']._for_xml_id('barcode_wms.barcode_wms_picking_client_action')
            action['xml_id'] = 'barcode_wms.barcode_wms_picking_client_action'
            # Handle context - can be string or dict
            ctx = action.get('context', {})
            if isinstance(ctx, str):
                import ast
                action_context = ast.literal_eval(ctx) if ctx else {}
            else:
                action_context = dict(ctx or {})
            action_context.update({
                'active_id': location.id,
                'default_location_id': location.id,
            })
            action['context'] = action_context
            return {'action': action}
        
        product = request.env['product.product'].search([('barcode', '=', barcode)], limit=1)
        if product:
            action = request.env['ir.actions.actions']._for_xml_id('product.product_normal_action')
            action['xml_id'] = 'product.product_normal_action'
            # Handle context - can be string or dict
            ctx = action.get('context', {})
            if isinstance(ctx, str):
                import ast
                action_context = ast.literal_eval(ctx) if ctx else {}
            else:
                action_context = dict(ctx or {})
            action_context.update({'active_id': product.id, 'active_ids': [product.id]})
            action.update({
                'res_model': 'product.product',
                'res_id': product.id,
                'views': action.get('views') or [[False, 'form']],
                'context': action_context,
            })
            return {'action': action}

        return {'warning': 'No document found for barcode: %s' % barcode}

    @http.route('/barcode_wms/rid_of_message_demo_barcodes', type='json', auth='user')
    def rid_of_message_demo_barcodes(self):
        # Here you would typically store a user preference
        return True

    @http.route('/barcode_wms/get_barcode_data', type='json', auth='user')
    def get_barcode_data(self, model=None, res_id=None, **kw):
        if not model or not res_id:
            return {}
        
        try:
            record = request.env[model].browse(res_id)
            if not record.exists():
                return {}

            records = {}
            
            # Helper to append to grouped records
            def add_record(rec_vals):
                model_name = rec_vals.get('model')
                if not model_name: return
                if model_name not in records:
                    records[model_name] = []
                # Check for duplicates? or just append
                records[model_name].append(rec_vals)

            # Helper for reading
            def read_and_group(recordset, fields):
                if not recordset: return
                res = recordset.read(fields)
                if not res: return
                
                model_name = recordset._name
                if model_name not in records: records[model_name] = []
                
                for r in res:
                    r['model'] = model_name
                    records[model_name].append(r)

            # Helper to clean many2one fields (tuple -> id)
            def clean_m2o(vals):
                for k, v in vals.items():
                    if isinstance(v, (list, tuple)) and len(v) == 2 and isinstance(v[0], int) and isinstance(v[1], str):
                        vals[k] = v[0]
                return vals

            # Add the main record (Picking)
            picking_fields = ['name', 'state', 'partner_id', 'user_id', 'location_id', 'location_dest_id', 'move_ids', 'move_line_ids', 'picking_type_id', 'picking_type_code', 'company_id', 'note']
            vals = record.read(picking_fields)[0]
            vals = clean_m2o(vals)
            vals['model'] = model
            if 'picking_type_code' not in vals and record.picking_type_id:
                 vals['picking_type_code'] = record.picking_type_id.code
            add_record(vals)

            if record.picking_type_id:
                picking_type_vals = record.picking_type_id.read(['name', 'code', 'default_location_src_id', 'default_location_dest_id'])[0]
                picking_type_vals = clean_m2o(picking_type_vals)
                picking_type_vals['model'] = 'stock.picking.type'
                if 'stock.picking.type' not in records:
                    records['stock.picking.type'] = []
                records['stock.picking.type'].append(picking_type_vals)

            if record.partner_id:
                partner_vals = record.partner_id.read(['name', 'contact_address', 'display_name'])[0]
                # Partner vals usually don't need m2o cleaning for these fields but good practice
                partner_vals['model'] = 'res.partner'
                if 'res.partner' not in records:
                    records['res.partner'] = []
                records['res.partner'].append(partner_vals)


            # Add Moves (Required for Demand)
            moves = record.move_ids
            if moves:
                moves_data = moves.read(['product_id', 'product_uom_qty', 'product_uom', 'location_id', 'state', 'packaging_uom_id', 'packaging_uom_qty'])
                for move in moves_data:
                    move = clean_m2o(move)
                    move['model'] = 'stock.move'
                    
                    # Manual fetching of move_line_ids for move to match structure if needed
                    # move['move_line_ids'] = ... (Odoo usually handles this via relation)
                    
                    add_record(move)
                
            # Create a map for fast lookup of demand
            move_demand_map = {m['id']: m['product_uom_qty'] for m in moves.read(['product_uom_qty'])}

            # Add Move Lines
            lines = record.move_line_ids
            if lines:
                # Odoo 19/18 might not have reserved_uom_qty on line, fetch essentials
                line_fields = ['product_id', 'quantity', 'move_id', 'location_dest_id', 'lot_id', 'lot_name', 'package_id', 'result_package_id', 'owner_id', 'product_uom_id', 'state', 'picked', 'packaging_uom_id', 'packaging_uom_qty', 'location_id', 'display_name', 'product_category_name', 'product_barcode', 'description_picking', 'is_entire_pack', 'manual_consumption']
                # Note: some fields above might not exist on stock.move.line in standard, adapt as needed. 
                # Checking fields existence is safer.
                valid_fields = [f for f in line_fields if f in lines._fields]
                lines_data = lines.read(valid_fields)
                
                for line in lines_data:
                    line = clean_m2o(line)
                    line['model'] = 'stock.move.line'
                    
                    # Logic for Quantity vs Qty Done (Odoo 19 specific)
                    # If picked, quantity is done qty. If not picked, quantity is reserved.
                    # But for Barcode UI compatibility, we set both.
                    line['qty_done'] = line['quantity'] if line.get('picked') else 0.0
                    
                    # Inject reserved quantity from move (Demand)
                    move_id_val = line['move_id'] # Now an ID because of clean_m2o
                    line['reserved_uom_qty'] = move_demand_map.get(move_id_val, 0.0) if move_id_val else 0.0
                    
                    add_record(line)
            


            # Products: Union of products from moves and lines
            product_ids = moves.mapped('product_id') | lines.mapped('product_id')
            if product_ids:
                read_and_group(product_ids, ['name', 'barcode', 'default_code', 'tracking', 'uom_id', 'display_name', 'categ_id', 'has_image', 'is_storable'])
                
            # UOMs
            uom_ids = product_ids.mapped('uom_id') | lines.mapped('product_uom_id')
            if uom_ids:
                read_and_group(uom_ids, ['name', 'factor'])

            # Locations (Source and Dest + Children if needed)
            location_ids = lines.mapped('location_id') | lines.mapped('location_dest_id') | record.location_id | record.location_dest_id
            if record.picking_type_id.default_location_src_id:
                 location_ids |= record.picking_type_id.default_location_src_id
            if record.picking_type_id.default_location_dest_id:
                 location_ids |= record.picking_type_id.default_location_dest_id
            
            if location_ids:
                 read_and_group(location_ids, ['name', 'barcode', 'usage', 'display_name', 'parent_path'])

            # Add Nomenclature
            nomenclature = request.env.company.nomenclature_id
            if not nomenclature:
                nomenclature = request.env['barcode.nomenclature'].search([], limit=1)
            
            if nomenclature:
                nomenclature_data = nomenclature.read(['name', 'rule_ids', 'is_gs1_nomenclature', 'gs1_separator_fnc1'])[0]
                nomenclature_data['model'] = 'barcode.nomenclature'
                if 'barcode.nomenclature' not in records:
                    records['barcode.nomenclature'] = []
                records['barcode.nomenclature'].append(nomenclature_data)
                
                # Add Rules
                # Ensure rules are read and added to 'barcode.rule' in records
                read_and_group(nomenclature.rule_ids, ['name', 'barcode_nomenclature_id', 'sequence', 'type', 'encoding', 'pattern', 'alias', 'associated_uom_id', 'is_gs1_nomenclature'])

            # Fetch Views (Placeholder logic, can be improved to fetch actual xml_ids)
            # For now returning False or generic IDs if available. 
            # In a real port, you might want to fetch specific form/kanban views.
            
            return {
                'data': {
                    'records': records,
                    'nomenclature_id': [nomenclature.id] if nomenclature else [],
                    'source_location_ids': record.location_id.ids,
                    'destination_locations_ids': record.location_dest_id.ids,
                    'config': {
                        'barcode_allow_extra_product': True,
                        'barcode_validation_after_dest_location': False,
                        'barcode_validation_all_product_packed': False,
                        'barcode_validation_full': True,
                        'create_backorder': 'ask',
                        'restrict_scan_product': False,
                        'restrict_scan_tracking_number': False,
                        'restrict_scan_source_location': False,
                        'restrict_put_in_pack': 'optional',
                        'restrict_scan_dest_location': 'no',
                        'lines_need_to_be_packed': False,
                        'lines_need_destination_location': False,
                        'play_sound': True,
                        'barcode_separator_regex': '[;,]',
                        'barcode_rfid_batch_time': 1000,
                        'precision': 2,
                    },
                    'line_view_id': request.env.ref('barcode_wms.stock_move_line_product_selector').id,
                    'form_view_id': False,
                    'scrap_view_id': False,
                    'package_view_id': False,
                    'precision': 2,
                    'lines': [], 
                },
                'groups': {
                    'group_stock_multi_locations': request.env.user.has_group('stock.group_stock_multi_locations'),
                    'group_tracking_lot': request.env.user.has_group('stock.group_tracking_lot'),
                    'group_production_lot': request.env.user.has_group('stock.group_production_lot'),
                    'group_uom': request.env.user.has_group('uom.group_uom'),
                    'group_tracking_owner': request.env.user.has_group('stock.group_tracking_owner'),
                    'group_stock_sign_delivery': request.env.user.has_group('stock.group_stock_sign_delivery'),
                    'group_mrp_byproducts': request.env.user.has_group('mrp.group_mrp_byproducts'),
                },
            }
        except Exception as e:
            # Log the error properly in the server logs
            request.env.cr.rollback() # Important to verify if we need to rollback
            import traceback
            traceback.print_exc()
            return {'error': str(e)}



    @http.route('/barcode_wms/get_specific_barcode_data', type='json', auth='user')
    def get_specific_barcode_data(self, barcode=None, barcodes_by_model=None, domains_by_model=None):
        if not barcode and not barcodes_by_model and not domains_by_model:
            return {}

        result = {
            "stock.location": [],
            "product.product": [],
            "uom.uom": [],
            "product.uom": [],
            "stock.picking": [],
            "stock.lot": [],
            "stock.package": [],
            "stock.package.type": []
        }

        def read_records(model_name, domain, fields):
            records = request.env[model_name].search(domain)
            if not records:
                return []
            return records.read(fields)

        if barcode:
            products = read_records('product.product', [('barcode', '=', barcode)], 
                ['barcode', 'categ_id', 'code', 'default_code', 'display_name', 'has_image', 'is_storable', 'tracking', 'uom_id', 'has_image'])
            if products:
                result['product.product'].extend(products)
            
            locations = read_records('stock.location', [('barcode', '=', barcode)], 
                ['name', 'barcode', 'usage', 'display_name', 'parent_path'])
            if locations:
                result['stock.location'].extend(locations)

            packages = read_records('stock.package', [('name', '=', barcode)], ['name', 'package_type_id'])
            if packages:
                result['stock.package'].extend(packages)

            lots = read_records('stock.lot', [('name', '=', barcode)], ['name', 'product_id', 'ref'])
            if lots:
                result['stock.lot'].extend(lots)

            pickings = read_records('stock.picking', [('name', '=', barcode)], 
                ['name', 'state', 'partner_id', 'user_id'])
            if pickings:
                result['stock.picking'].extend(pickings)

        if barcodes_by_model:
            for model, barcodes in barcodes_by_model.items():
                if model == 'product.product':
                    products = read_records(model, [('barcode', 'in', barcodes)], 
                        ['barcode', 'categ_id', 'code', 'default_code', 'display_name', 'has_image', 'is_storable', 'tracking', 'uom_id', 'has_image'])
                    result['product.product'].extend(products)
                elif model == 'stock.location':
                     locations = read_records(model, [('barcode', 'in', barcodes)], 
                        ['name', 'barcode', 'usage', 'display_name', 'parent_path'])
                     result['stock.location'].extend(locations)
                elif model == 'stock.lot':
                    lots = read_records(model, [('name', 'in', barcodes)], ['name', 'product_id', 'ref'])
                    result['stock.lot'].extend(lots)
                elif model == 'stock.package':
                    packages = read_records(model, [('name', 'in', barcodes)], ['name', 'package_type_id'])
                    result['stock.package'].extend(packages)
        
        if domains_by_model:
            for model, domain in domains_by_model.items():
                fields = ['display_name']
                if model == 'product.product':
                    fields = ['barcode', 'categ_id', 'code', 'default_code', 'display_name', 'has_image', 'is_storable', 'tracking', 'uom_id', 'has_image']
                elif model == 'stock.location':
                    fields = ['name', 'barcode', 'usage', 'display_name', 'parent_path']
                elif model == 'stock.lot':
                    fields = ['name', 'product_id', 'ref']
                elif model == 'stock.package':
                    fields = ['name', 'package_type_id']
                
                records = read_records(model, domain, fields)
                if model in result:
                    result[model].extend(records)
                else:
                    result[model] = records

        product_uom_ids = set()
        for p in result['product.product']:
            if p.get('uom_id'):
                # uom_id is (id, name) tuple after read? No, usually (id, name) in read, but we need ID.
                # 'read' returns (id, name) for M2O, but we need to check how standard JS expects it.
                # In user example: "uom_id": 1. So we probably need to clean M2O or rely on clean_m2o like helper if used.
                # However, read() in Odoo returns tuple (id, name) for Many2one unless valid_fields logic is applied or clean.
                # Wait, user example: "uom_id": 1. This implies it's just the ID? 
                # Odoo 'read' method returns (id, display_name) for many2one fields by default. 
                # The user's example likely comes from an environment where this is cleaned or specific options used.
                # Let's assume we need to extract ID if it's a tuple.
                val = p['uom_id']
                if isinstance(val, (list, tuple)):
                    p['uom_id'] = val[0]
                    product_uom_ids.add(val[0])
                elif isinstance(val, int):
                    product_uom_ids.add(val)
        
        if product_uom_ids:
            uoms = request.env['uom.uom'].browse(list(product_uom_ids)).read(['name', 'factor'])
            result['uom.uom'].extend(uoms)

        return result

    @http.route('/barcode_wms/save_barcode_data', type='json', auth='user')
    def save_barcode_data(self, model, res_id, write_field, write_vals, **kw):
        """
        Save barcode data to database.
        
        :param model: Model name (e.g., 'stock.picking')
        :param res_id: Record ID
        :param write_field: Field name to write (e.g., 'move_line_ids')
        :param write_vals: Odoo command list for One2many/Many2many fields
            Example: [[1, 24, {qty_done: 3}]] → UPDATE line 24 with qty_done=3
            
        Odoo command format:
            [0, 0, values]    → CREATE
            [1, id, values]   → UPDATE
            [2, id, 0]        → DELETE
            [3, id, 0]        → UNLINK (remove relation but don't delete)
            [4, id, 0]        → LINK
            [5, 0, 0]         → UNLINK ALL
            [6, 0, ids]       → REPLACE WITH
        """
        try:
            record = request.env[model].browse(res_id)
            if not record.exists():
                return {'error': 'Record not found'}
            
            # Write the commands to the specified field
            record.write({write_field: write_vals})
            
            return {'status': 'ok'}
            
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error saving barcode data: {e}", exc_info=True)
            return {'error': str(e)}
