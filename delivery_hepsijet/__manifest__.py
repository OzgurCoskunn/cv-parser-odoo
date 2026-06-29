# -*- coding: utf-8 -*-
# Copyright © 2024 Projet (https://bulutkobi.io)
# Part of Projet License. See LICENSE file for full copyright and licensing details.
{
    'name': 'Delivery: HepsiJet',
    'version': '19.0.1.0',
    'author': 'Projet',
    'website': 'https://bulutkobi.io',
    'license': 'OPL-1',
    'depends': ['delivery_base', 'l10n_tr_address', 'delivery_syncops', 'queue_job'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/queue_job_data.xml',
        'report/report.xml',
        'views/delivery_carrier.xml',
        'views/stock_picking.xml',
        'views/sale_order.xml',
        'views/stock_warehouse.xml',
        'wizards/stock_return_picking.xml',
        'wizards/stock_return_picking_hepsijet_warning.xml',
    ],
}
