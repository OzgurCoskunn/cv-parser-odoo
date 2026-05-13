# -*- coding: utf-8 -*-
# Copyright © 2026 Projet (https://bulutkobi.io)
# Part of Projet License. See LICENSE file for full copyright and licensing details.
{
    'name': 'Delivery: Aras Cargo',
    'version': '19.0.1.0',
    'author': 'Projet',
    'website': 'https://bulutkobi.io',
    'license': 'LGPL-3',
    'depends': [
        'delivery',
        'connector_syncops',
        'queue_job',
    ],
    'data': [
        'data/data.xml',
        'data/queue_job_data.xml',
        'views/stock_move.xml',
        'views/stock_picking.xml',
        'views/stock_warehouse.xml',
        'views/delivery_carrier.xml',
    ],
}
