# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class FsmServiceZone(models.Model):
    _name = 'fsm.service.zone'
    _description = 'Field Service Management: Service Zones'
    _order = 'state_id'

    def _compute_name(self):
        for zone in self:
            zone.name = '%s / %s (%s)' % (zone.state_id.name, zone.town_id.name, zone.type_id.name)

    name = fields.Char(compute='_compute_name')
    active = fields.Boolean(default=True)
    team_ids = fields.Many2many('crm.team', 'fsm_service_zone_team_rel', 'zone_id', 'team_id', string='Teams')
    state_id = fields.Many2one('res.country.state', string='City', ondelete='cascade', required=True)
    town_id = fields.Many2one('res.country.town', string='Town', ondelete='cascade', required=True)
    type_id = fields.Many2one('fsm.service.type', string='Type', ondelete='cascade', required=True)
    sla_id = fields.Many2one('sla.agreement', string='SLA', ondelete='cascade')
    location_id = fields.Many2one('stock.location', string='Location')
    value = fields.Integer(string='Level')

    def get_action(self):
        return self.env.ref('fsm.action_service_zone').sudo().read()[0]

    def get_value(self):
        return self.value

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'value' in fields:
            fields.remove('value')
        return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)


class FsmServiceType(models.Model):
    _name = 'fsm.service.type'
    _description = 'Field Service Management: Service Types'
    _order = 'sequence'

    name = fields.Char(required=True)
    code = fields.Char()
    sequence = fields.Integer(default=10)
