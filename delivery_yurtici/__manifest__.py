# -*- coding: utf-8 -*-
# Copyright © 2023 Projet (https://bulutkobi.io)
# Part of Projet License. See LICENSE file for full copyright and licensing details.
{
    'name': 'Delivery: Yurtiçi Kargo',
    'version': '19.0.1.0',
    'author': 'Projet',
    'website': 'https://bulutkobi.io',
    'license': 'LGPL-3',
    'depends': [
        'delivery_base',
        'l10n_tr_address',
        'connector_syncops',
        'queue_job',
    ],
    'data': [
        'data/data.xml',
        'data/queue_job_data.xml',
        'views/delivery_carrier.xml',
        'views/stock_picking.xml',
        'views/sale_order.xml',
        'wizards/stock_return_picking.xml',
    ],
}
