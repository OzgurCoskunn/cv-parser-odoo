# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    type = fields.Selection(selection_add=[('service', 'Service Address')])
    mobile = fields.Char(string='Mobile')
    table_name = fields.Char(string='Table Name')
