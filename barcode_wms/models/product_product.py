# -*- coding: utf-8 -*-
from operator import itemgetter
from itertools import groupby
from datetime import date

from odoo import models, _, fields


class Product(models.Model):
    _inherit = 'product.product'

    def _compute_has_image(self):
        for product in self:
            product.has_image = bool(product.image_1920)

    has_image = fields.Boolean(compute='_compute_has_image', string='Has Image', store=False)

    def _get_barcode_data(self):
        type = ''
        if self.is_storable:
            type = _("Storable Product")
        elif self.type == 'consu':
            type = _("Consumable")
        elif self.type == 'service':
            type = _("Service")

        return {
            "id": self.id,
            "type": type,
            "name": self.name,
            "categ_id": self.categ_id.display_name,
            "weight": self.weight,
            "tracking": self.tracking,
            "list_price": self.list_price,
            "standard_price": self.standard_price,
            "write_date": self.write_date,
            "qty_available": self.qty_available,
            "virtual_available": self.virtual_available,
            "uom_id": self.uom_id.display_name,
            "uom_po_id": self.uom_po_id.display_name if hasattr(self, 'uom_po_id') else self.uom_id.display_name,
            "volume": self.volume,
            "sale_delay": self.sale_delay,
            "volume_uom_name": self.volume_uom_name,
            "weight_uom_name": self.weight_uom_name,
            "barcode": self.barcode if self.barcode else '-',
            "description_sale": self.description_sale if self.description_sale else '-',
            "default_code": self.default_code if self.default_code else '-',
            "display_name": self.with_context(lang=self.env.user.lang or "en_US").display_name if self.display_name else '-',
        }

    def get_barcode_data(self, quantity, edit=False):
        if not self:
             return {}
        self.ensure_one()

        uid = self.env.user.id
        if self.env.context.get('allowed_company_ids', []):
            companies = self.env.context['allowed_company_ids']
        else:
            companies = [self.env.company.id]

        currency_id = self.env.company.currency_id
        currency = {
            'symbol': currency_id.symbol,
            'name': currency_id.name,
            'position': currency_id.position,
        }

        pricelists = self.env['product.pricelist'].search(['|', ('company_id', 'in', companies), ('company_id', '=', False)])
        pricelists_data = []
        for pricelist in pricelists:
            price = pricelist._get_product_price(self, quantity)
            pricelists_data.append({
                'id': pricelist.id,
                'name': pricelist.name,
                'price': price,
                'currency': {
                    'name': pricelist.currency_id.name,
                    'symbol': pricelist.currency_id.symbol,
                    'position': pricelist.currency_id.position
                }
            })
        pricelists = pricelists_data
    
        product = self._get_barcode_data()

        warehouses = [{
            'name': w.name,
            'id': w.id,
            'stock_location': w.lot_stock_id.display_name,
            'child_locations': [{
                'location': location.display_name,
                'available_quantity': self.with_context({'location': location.id}).qty_available,
                'forecasted_quantity': self.with_context({'location': location.id}).virtual_available,
                'lot_lines': [{
                    'lot_id': stock_lot_lines.lot_id.name,
                    'quantity': stock_lot_lines.quantity
                    }
                    for stock_lot_lines in self.env['stock.quant'].search([
                        ('product_id', '=', self.id),
                        ('location_id', '=', location.id),
                    ]) if stock_lot_lines.lot_id.name
                ],
            } for location in w.internal_location_ids],
            'available_quantity': self.with_context({'location': w.internal_location_ids.ids}).qty_available,
            'forecasted_quantity': self.with_context({'location': w.internal_location_ids.ids}).virtual_available,
            'uom': self.uom_name
        } for w in self.env['stock.warehouse'].search([('company_id', 'in', companies)])]

        # Warehouses
        warehouses_ready = [{
            'name': w.name,
            'id': w.id,
            'stock_location': w.lot_stock_id.display_name,
            'child_locations': [{
                'location': location.display_name,
                'available_quantity': self.with_context({'location': location.id}).qty_available,
                'forecasted_quantity': self.with_context({'location': location.id}).virtual_available,
                'lot_lines': [{
                    'lot_id': stock_lot_lines.lot_id.name,
                    'quantity': stock_lot_lines.quantity
                } for stock_lot_lines in self.env['stock.quant'].search([
                    ('product_id', '=', self.id),
                    ('location_id', '=', location.id)]) if stock_lot_lines.lot_id.name],
                } for location in w.internal_location_ids if self.with_context({'location': location.id}).qty_available != 0],
            'available_quantity': self.with_context({'location': w.internal_location_ids.ids}).qty_available,
            'forecasted_quantity': self.with_context({'location': w.internal_location_ids.ids}).virtual_available,
            'uom': self.uom_name,
        } for w in self.env['stock.warehouse'].search([('company_id', 'in', companies)])]

        # Packages
        packages = []
        if edit:
            packages = self.env['stock.quant'].search([('product_id', '=', self.id)])
            packages = [[package.package_id.id, package.package_id.name, package.lot_id.name, package.quantity] for package in packages if package.package_id.id]

        # Suppliers
        key = itemgetter('display_name')
        suppliers = []
        for key, group in groupby(sorted(self.seller_ids, key=key), key=key):
            for s in list(group):
                if not (
                    (s.date_start and s.date_start > date.today()) or \
                    (s.date_end and s.date_end < date.today()) or \
                    (s.min_qty > quantity)
                ):
                    suppliers.append({
                        'id': s.id,
                        'name': s.display_name,
                        'delay': s.delay,
                        'price': s.price,
                        'min_qty': s.min_qty,
                        'product_uom': s.product_uom_id.display_name,
                        'currency': {
                            'name': s.currency_id.name,
                            'symbol': s.currency_id.symbol,
                            'position': s.currency_id.position
                        }
                    })
                    break

        # Variants
        variants = [{
            'name': attribute_line.attribute_id.name,
            'values': list(map(lambda attr_name: {
                'name': attr_name,
                'search': '%s %s' % (self.name, attr_name)
            }, attribute_line.value_ids.mapped('name')))
        } for attribute_line in self.attribute_line_ids]

        return {
            'user': uid,
            'product': product,
            'currency': currency,
            'company': companies[0],
            'packages': packages,
            'variants': variants,
            'suppliers': suppliers,
            'pricelists': pricelists,
            'warehouses': warehouses,
            'warehouses_ready': warehouses_ready,
        }
