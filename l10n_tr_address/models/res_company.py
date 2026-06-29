# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResCompany(models.Model): 
    _inherit = 'res.company'

    def _inverse_street3(self):
        for company in self:
            company.partner_id.street3 = company.street3

    def _inverse_town(self):
        for company in self:
            company.partner_id.town_id = company.town_id

    def _inverse_district(self):
        for company in self:
            company.partner_id.district_id = company.district_id

    def _inverse_street(self):
        for company in self:
            company.partner_id.street_id = company.street_id

    city = fields.Char(string='City Name')
    street = fields.Char(string='District Name')
    street2 = fields.Char(string='Street Number')

    street3 = fields.Char(compute='_compute_address', inverse='_inverse_street3', string='Address Details')
    town_id = fields.Many2one('res.country.town', compute='_compute_address', inverse='_inverse_town', string='Town', domain="[('state_id','=',state_id)]")
    district_id = fields.Many2one('res.country.district', compute='_compute_address', inverse='_inverse_district', string='District', domain="[('town_id','=',town_id)]")
    street_id = fields.Many2one('res.country.street', compute='_compute_address', inverse='_inverse_street', string='Street', domain="[('district_id','=',district_id)]")

    field_town_selection = fields.Boolean('Use Town Selection List')
    field_district_selection = fields.Boolean('Use District Selection List')
    field_street_selection = fields.Boolean('Use Street Selection List')
    field_table_name_selection = fields.Boolean('Use Table Name')

    def _get_company_address_field_names(self):
        return super()._get_company_address_field_names() + [
            'street3',
            'town_id',
            'district_id',
            'street_id',
        ]

    @api.onchange('state_id')
    def _onchange_state_id(self):
        self.town_id = False

    @api.onchange('town_id')
    def _onchange_town_id(self):
        self.district_id = False

    @api.onchange('district_id')
    def _onchange_district_id(self):
        self.street_id = False
