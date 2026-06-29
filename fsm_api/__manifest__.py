# -*- coding: utf-8 -*-
# Copyright © 2023 Projet (https://bulutkobi.io)
# Part of Projet License. See LICENSE file for full copyright and licensing details.
{
    'name': 'Field Service: API',
    'version': '1.1',
    'author': 'Projet',
    'website': 'https://bulutkobi.io',
    'license': 'LGPL-3',
    'depends': ['fsm', 'base_rest', 'base_rest_datamodel'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/fsm_api_spec_data.xml',
        'views/fsm_api_auth.xml',
        'views/fsm_api_spec.xml',
        'views/fsm_api_proxy.xml',
        'views/fsm_api_log.xml',
        'views/fsm_task.xml',
        'views/ir_ui_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fsm_api/static/src/scss/backend.scss',
            'fsm_api/static/src/xml/response_type.xml',
            'fsm_api/static/src/js/response_type.js',
        ],
    },
}
