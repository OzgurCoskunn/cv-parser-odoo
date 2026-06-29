# -*- coding: utf-8 -*-
from odoo import models, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def save_barcode_data(self, lines):
        quants = self.env['stock.quant']
        for line in lines:
            number = False
            domain = [
                ('location_id', '=', line['location_id'][0]),
                ('product_id', '=', line['product_id']['id']),
            ]
            if line['product_id']['tracking'] in ('serial', 'lot'):
                number = line['number']
                domain.append(('lot_id.name', '=', number))

            quant = quants.search(domain, limit=1)
            if quant:
                quant.write({
                    'user_id': self.env.user.id,
                    'inventory_quantity': line['qty_done'],
                })
            else:
                values = {
                    'user_id': self.env.user.id,
                    'location_id': line['location_id'][0],
                    'product_id': line['product_id']['id'],
                    'inventory_quantity': 0,
                }
                if number:
                    lot = self.env['stock.lot'].search([('name', '=', number)], limit=1)
                    if not lot:
                        lot = self.env['stock.lot'].create({
                            'name': number,
                            'product_id': line['product_id']['id'],
                        })
                    values['lot_id'] = lot.id
                quant = quant.create(values)
                quant.write({
                    'inventory_quantity': line['qty_done'],
                })

            quants |= quant

        ids = quants.ids
        locations = quants.mapped('location_id').ids
        domain = [
            ('id', 'not in', ids),
            ('location_id', 'in', locations),
            ('inventory_quantity_set', '=', True),
        ]
        quants = quants.search(domain)

        raise Exception(quants)
        for quant in quants:
            quant.action_set_inventory_quantity_to_zero()
        return ids
