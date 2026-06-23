# -*- coding: utf-8 -*-
# Copyright © 2024 Projet (https://bulutkobi.io)
# Part of Projet License. See LICENSE file for full copyright and licensing details.
{
    'name': 'Delivery: Base',
    'version': '19.0.1.0',
    'author': 'Projet',
    'website': 'https://bulutkobi.io',
    'license': 'OPL-1',
    'depends': ['stock_delivery'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/delivery_status.xml',
        'views/delivery_carrier.xml',
        'views/delivery_log.xml',
        'views/stock_picking.xml',
        'views/sale_order.xml',
        'wizards/stock_return_picking.xml',
    ],
}
