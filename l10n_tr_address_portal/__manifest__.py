# -*- coding: utf-8 -*-
# Copyright © 2023 Projet (https://bulutkobi.io)
# Part of Projet License. See LICENSE file for full copyright and licensing details.
{
    'name': 'Turkey - Addresses on Portal',
    'version': '19.0.1.0',
    'author': 'Projet',
    'website': 'https://bulutkobi.io',
    'license': 'LGPL-3',
    'depends': ['l10n_tr_address', 'portal'],
    'data': [
        'views/portal.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_tr_address_portal/static/src/js/portal.js',
        ],
    },
}
