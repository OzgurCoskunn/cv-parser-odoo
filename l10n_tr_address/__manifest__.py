# -*- coding: utf-8 -*-
# Copyright © 2024 Projet (https://bulutkobi.io)
# Part of Paylox License. See LICENSE file for full copyright and licensing details.
{
    'name': 'Turkey - Addresses',
    'version': '19.0.1.2',
    'author': 'Projet',
    'website': 'https://bulutkobi.io',
    'license': 'LGPL-3',
    'depends': ['base_setup', 'base_geolocalize'],
    'post_init_hook': '_post_init',
    'uninstall_hook': '_uninstall',
    'data': [
        'views/res_country.xml',
        'views/res_partner.xml',
        'views/res_company.xml',
        'views/res_config.xml',
        'security/ir.model.access.csv',
    ],
}
