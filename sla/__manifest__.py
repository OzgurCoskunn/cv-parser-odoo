# -*- coding: utf-8 -*-
# Copyright © 2023 Projet (https://bulutkobi.io)
# Part of Projet License. See LICENSE file for full copyright and licensing details.
{
    'name': 'Service Level Agreement',
    'version': '19.0.1.0',
    'author': 'Projet',
    'website': 'https://bulutkobi.io',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'crm'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/sla_agreement.xml',
        'views/sla_ticket.xml',
        'views/sla_policy.xml',
        'views/sla_holiday.xml',
        'views/sla_worksheet.xml',
        'views/ir_ui_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sla/static/src/scss/backend.scss',
        ],
    },
    'installable': True,
    'application': True,
}
