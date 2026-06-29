# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import Query


class ResPartner(models.Model):
    _inherit='res.partner'

    @api.depends('town_id')
    def _compute_field_city(self):
        for partner in self:
            partner.city = partner.town_id.name

    @api.depends('district_id')
    def _compute_field_street(self):
        for partner in self:
            partner.street = partner.district_id.name

    @api.depends('street_id')
    def _compute_field_street2(self):
        for partner in self:
            partner.street2 = partner.street_id.name

    @api.depends('active')
    def _compute_field_selection(self):
        company = self.env.company
        for partner in self:
            partner.field_town_selection = company.field_town_selection
            partner.field_district_selection = company.field_district_selection
            partner.field_street_selection = company.field_street_selection
            partner.field_table_name_selection = company.field_table_name_selection

    def _compute_contact_id(self):
        for partner in self:
            contact = self.search([
                ('parent_id', '=', partner.id),
                ('is_company', '=', False),
                ('type', '=', 'contact'),
            ], limit=1, order='id desc')
            partner.contact_id = contact.id
            
    def _search_contact_id(self, operator, value):
        domain = [
            ('parent_id', '!=', False),
            ('is_company', '=', False),
            ('type', '=', 'contact'),
        ]
        if isinstance(value, Query):
            domain.append(('id', 'in', value._result))
        else:
            domain.append(('name', operator, value))
        return domain

    city = fields.Char(compute='_compute_field_city', tracking=True, store=True, readonly=False, string='City Name')
    street = fields.Char(compute='_compute_field_street', tracking=True, store=True, readonly=False, string='District Name')
    street2 = fields.Char(compute='_compute_field_street2', tracking=True, store=True, readonly=False, string='Street Number')
    street3 = fields.Char(string='Address Details', tracking=True)

    country_id = fields.Many2one(tracking=True)
    state_id = fields.Many2one(tracking=True)
    town_id = fields.Many2one('res.country.town', string='Town', domain="[('state_id','=',state_id)]")
    district_id = fields.Many2one('res.country.district', string='District', domain="[('town_id','=',town_id)]")
    street_id = fields.Many2one('res.country.street', string='Street', domain="[('district_id','=',district_id)]")
    table_name = fields.Char(string='Table Name')
    uavt_code = fields.Char(string='UAVT Code')
    contact_id = fields.Many2one('res.partner', compute='_compute_contact_id', search='_search_contact_id')

    field_town_selection = fields.Boolean(compute='_compute_field_selection', compute_sudo=True)
    field_district_selection = fields.Boolean(compute='_compute_field_selection', compute_sudo=True)
    field_street_selection = fields.Boolean(compute='_compute_field_selection', compute_sudo=True)
    field_table_name_selection = fields.Boolean(compute='_compute_field_selection', compute_sudo=True)

    @api.model
    def _address_fields(self):
        return super()._address_fields() + ['street3']

    @api.model
    def _get_default_address_format(self):
        return "%(street)s %(street2)s %(street3)s %(zip)s %(city)s %(state_name)s / %(country_name)s"

    @api.model
    def _get_address_format(self):
        return self._get_default_address_format()

    @api.onchange('state_id')
    def _onchange_state_id(self):
        self.town_id = False

    @api.onchange('town_id')
    def _onchange_town_id(self):
        self.district_id = False

    @api.onchange('district_id')
    def _onchange_district_id(self):
        self.street_id = False

    def _get_name(self):
        name = super()._get_name()
        if self._context.get('show_contact') and self.contact_id:
            name += ' [%s]' % self.contact_id.name
        return name
