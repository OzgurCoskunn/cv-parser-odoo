# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SlaAgreement(models.Model):
    _name = 'sla.agreement'
    _description = 'Service Level Agreement: Agreements'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    def _compute_ticket_count(self):
        for agreement in self:
            agreement.ticket_count = self.env['sla.ticket'].sudo().search_count([('agreement_id', '=', agreement.id)])

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    user_id = fields.Many2one('res.users', string='User', domain='[("share", "=", False)]')
    team_id = fields.Many2one('crm.team', string='Team')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),
    ], default='draft', required=True)
    type = fields.Selection([
        ('partner', 'Partner'),
        ('user', 'User'),
        ('team', 'Team'),
    ], default='partner', required=True)
    ticket_count = fields.Integer(compute='_compute_ticket_count')
    ticket_ids = fields.One2many('sla.ticket', 'agreement_id', string='Tickets')
    policy_id = fields.Many2one('sla.policy')
    worksheet_id = fields.Many2one('sla.worksheet', required=True)
    stage_ids = fields.One2many('sla.agreement.stage', 'agreement_id', string='Stages', copy=True)
    stage_model_name = fields.Char()
    hour_model_id = fields.Many2one('ir.model', domain=[('model', 'like', '%.zone')])
    hour_model = fields.Boolean(default=False)
    hour_total = fields.Float(string='Total Hour(s)')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    def action_confirm(self):
        self.write({'state': 'confirm'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_ticket(self):
        self.ensure_one()
        if not self.stage_ids:
            raise UserError(_('Please define at least one stage in your SLA policy.'))

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'sla.ticket',
            'view_mode': 'form',
            'context': {
                'default_agreement_id': self.id,
                'default_stage_id': self.stage_ids[0]['id'],
            }
        }
        return action

    def action_view_tickets(self):
        action = self.env.ref('sla.action_ticket').sudo().read()[0]
        action['context'] = {'default_agreement_id': self.id}
        action['domain'] = [('agreement_id', '=', self.id)]
        return action

    def action_view_hours(self):
        try:
            action = self.env[self.hour_model_id.model].get_action()
        except:
            raise ValidationError(_('This model is not suitable to be an SLA hour model.'))
        action['context'] = {
            'model': self.hour_model_id.model,
            'default_sla_id': self.id,
        }
        action['domain'] = [('sla_id', '=', self.id)]
        return action

    def unlink(self):
        for agreement in self:
            if agreement.state != 'draft':
                raise UserError(_('Only "Draft" agreements can be deleted'))
        return super().unlink()

    @api.onchange('policy_id')
    def onchange_policy_id(self):
        self.worksheet_id = self.policy_id.worksheet_id.id
        self.hour_total = self.policy_id.hour_total
        self.stage_model_name = self.policy_id.stage_model_name
        self.stage_ids = [(5, 0, 0)] + [(0, 0, {
            'name': stage.name,
            'type': stage.type,
            'description': stage.description,
            'stage_id': stage.stage_id,
            'stage_ref': stage.stage_ref,
            'stage_model': stage.stage_model,
        }) for stage in self.policy_id.stage_ids]


class SlaAgreementStage(models.Model):
    _name = 'sla.agreement.stage'
    _inherit = 'sla.policy.stage'
    _description = 'Service Level Agreement: Agreement Stages'

    agreement_id = fields.Many2one('sla.agreement', ondelete='cascade')
