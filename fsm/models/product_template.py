# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.depends('fsm_partner_id')
    def _compute_fsm_subpartner_ids(self):
        for product in self:
            if product.fsm_partner_id:
                product.fsm_subpartner_ids = self.env['fsm.project.subpartner'].sudo().search([
                    ('project_id.partner_id', '=', product.fsm_partner_id.id),
                ]).mapped('partner_id').ids
            else:
                product.fsm_subpartner_ids = False

    def _domain_fsm_partner_id(self):
        return [('id', 'in', self.env['fsm.project'].sudo().search([]).mapped('partner_id').ids)]

    fsm_ok = fields.Boolean('Available in Field Service')
    fsm_os = fields.Selection([
        ('ANDROID', 'Android'),
        ('LINUX', 'Linux'),
        ('OTHER', 'Other'),
    ], string='Field Service Operation System')
    fsm_product_type = fields.Selection([
        ('POS', 'POS'),
        ('SIM', 'SIM'),
        ('MALZEME', 'MALZEME'),
        ('YEDEK_PARCA', 'YEDEK PARÇA'),
    ], string='Field Service Operation Product Type')
    fsm_partner_id = fields.Many2one('res.partner', string='Field Service Owner', domain=_domain_fsm_partner_id)
    fsm_subpartner_id = fields.Many2one('res.partner', string='Field Service Subpartner', domain='[("id", "in", fsm_subpartner_ids)]')
    fsm_subpartner_ids = fields.Many2many('res.partner', compute='_compute_fsm_subpartner_ids')

    @api.onchange('fsm_partner_id')
    def onchange_fsm_partner_id(self):
        self.fsm_subpartner_id = False

    def _compute_display_name(self):
        for template in self:
            template.display_name = '%s%s%s' % (
                template.default_code and '[%s] ' % template.default_code or '',
                template.name,
                template.fsm_partner_id and ' / %s' % template.fsm_partner_id.name.split(' ', 1)[0] or '',
            )

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            domain = [('name', operator, name)]
        return self._search(domain, limit=limit, order=order)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _compute_display_name(self):
        for product in self:
            product.display_name = '%s%s%s' % (
                product.default_code and '[%s] ' % product.default_code or '',
                product.name,
                product.fsm_partner_id and ' / %s' % product.fsm_partner_id.name.split(' ', 1)[0] or '',
            )

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            domain = [('name', operator, name)]
        return self._search(domain, limit=limit, order=order)
