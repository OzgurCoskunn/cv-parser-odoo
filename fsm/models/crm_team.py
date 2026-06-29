# -*- coding: utf-8 -*-
from odoo import models, fields


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    fsm_user_ids = fields.Many2many('res.users', 'crm_team_fsm_users_rel', 'team_id', 'user_id', string='FSM Users')
