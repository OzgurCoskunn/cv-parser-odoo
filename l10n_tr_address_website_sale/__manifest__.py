# -*- coding: utf-8 -*-
# Copyright © 2023 Projet (https://bulutkobi.io)
# Part of Projet License. See LICENSE file for full copyright and licensing details.
{
    'name': 'Turkey - Addresses on eCommerce',
    'version': '1.0',
    'author': 'Projet',
    'website': 'https://bulutkobi.io',
    'license': 'LGPL-3',
    'depends': ['l10n_tr_address', 'website_sale'],
    'data': [
        'data/data.xml',
        'views/address.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_tr_address_website_sale/static/src/lib/imask.js',
            'l10n_tr_address_website_sale/static/src/js/address.js',
        ],
    },
}
