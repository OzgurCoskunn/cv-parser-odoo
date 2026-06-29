# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel): 
    _inherit = 'res.config.settings'

    field_town_selection = fields.Boolean(related='company_id.field_town_selection', readonly=False)
    field_district_selection = fields.Boolean(related='company_id.field_district_selection', readonly=False)
    field_street_selection = fields.Boolean(related='company_id.field_street_selection', readonly=False)
    field_table_name_selection = fields.Boolean(related='company_id.field_table_name_selection', readonly=False)
