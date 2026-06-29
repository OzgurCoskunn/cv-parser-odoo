# -*- coding: utf-8 -*-

from odoo import models, fields


class FsmProjectConfirm(models.TransientModel):
    _name = 'fsm.project.confirm'
    _description = 'Field Service Management: Project Confirmation Wizard'

    project_id = fields.Many2one('fsm.project', ondelete='cascade')
    stage_ids = fields.Many2many('fsm.stage', 'fsm_project_confirm_stage_rel', 'wizard_id', 'stage_id')
