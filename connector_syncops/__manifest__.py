# -*- coding: utf-8 -*-
# Copyright © 2025 Projet (https://bulutkobi.io)
# Part of Paylox License. See LICENSE file for full copyright and licensing details.

{
    'name': 'syncOPS Connector',
    'version': '1.0',
    'author': 'Projet',
    'website': 'https://bulutkobi.io',
    'license': 'LGPL-3',
    'sequence': 1071,
    'depends': ['base'],
    'data': [
        #'data/data.xml',
        'views/syncops.xml',
        'views/config.xml',
        'wizards/log.xml',
        'wizards/sync.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'connector_syncops/static/src/scss/sync.scss',
            'connector_syncops/static/src/xml/sync_list.xml',
            'connector_syncops/static/src/js/sync_list_controller.js',
            'connector_syncops/static/src/js/sync_list_view.js',
        ],
    },
    'auto_install': False,
}
