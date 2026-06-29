# -*- coding: utf-8 -*-

from odoo import models, fields


class SlaAgreement(models.Model):
    _inherit = 'sla.agreement'

    fsm_project_ids = fields.Many2many('fsm.project', 'fsm_project_sla_rel', 'sla_id', 'project_id', string='Field Service Projects', domain='[("state", "=", "confirm")]')
