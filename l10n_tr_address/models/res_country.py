# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    town_ids = fields.One2many('res.country.town', 'state_id', string='Towns')


class ResCountryTown(models.Model):
    _name = 'res.country.town'
    _description = 'Town'

    state_id = fields.Many2one('res.country.state', string='State', ondelete='cascade')
    name = fields.Char('Town', required=True)
    active = fields.Boolean(default=True)
    code = fields.Char('Code')
    district_ids = fields.One2many('res.country.district', 'town_id', string='Districts')


class ResCountryDistrict(models.Model):
    _name = 'res.country.district'
    _description = 'District'

    town_id = fields.Many2one('res.country.town', string='Town', ondelete='cascade')
    street_ids = fields.One2many('res.country.street', 'district_id', string='Streets')
    name = fields.Char('District', required=True)
    active = fields.Boolean(default=True)
    code = fields.Char('Code')


class ResCountryStreet(models.Model):
    _name = 'res.country.street'
    _description = 'Street'

    district_id = fields.Many2one('res.country.district', string='District', ondelete='cascade')
    name = fields.Char('Street', required=True)
    active = fields.Boolean(default=True)
    code = fields.Char('Code')
