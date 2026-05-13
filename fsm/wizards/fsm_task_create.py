# -*- coding: utf-8 -*-

from odoo import models, fields, api


class FsmTaskCreate(models.TransientModel):
    _name = 'fsm.task.create'
    _description = 'Field Service Management: Task Create Wizard'

    @api.depends('project_id')
    def _compute_type_ids(self):
        for wizard in self:
            wizard.type_ids = wizard.project_id.type_ids.mapped('type_id').ids

    project_id = fields.Many2one('fsm.project', required=True, ondelete='cascade')
    project_item_id = fields.Many2one('fsm.project.item', ondelete='cascade')
    type_id = fields.Many2one('fsm.type', domain='[("id", "=", type_ids)]', required=True)
    type_ids = fields.Many2many('fsm.type', compute='_compute_type_ids')

    def confirm(self):
        project = self.project_id
        item = self.project_item_id
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'fsm.task',
            'view_mode': 'form',
            'context': {
                'default_project_id': project.id,
                'default_project_item_id': item.id,
                'default_type_id': self.type_id.id,
                'default_partner_id': project.partner_id.id,
            }
        }
        if project.stage_ids:
            action['context']['default_stage_id'] = project.stage_ids[0]['id']
        if project.sla_ids:
            sla = project.sla_ids.filtered(lambda s: s.type == 'partner')
            action['context']['default_sla_id'] = sla and sla['id'] or False
        return action
