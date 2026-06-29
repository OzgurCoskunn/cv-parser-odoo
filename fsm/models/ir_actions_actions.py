# -*- coding: utf-8 -*-
from odoo import models, api


class IrActions(models.Model):
    _inherit = 'ir.actions.actions'

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if 'model' in self.env.context:
            if not args:
                args = []
            if self._name == 'ir.actions.report':
                args.append(('model', '=', self.env.context['model']))
            elif self._name == 'ir.actions.server':
                args.append(('model_name', '=', self.env.context['model']))
            elif self._name == 'ir.actions.client':
                args.append(('res_model', '=', self.env.context['model']))
            elif self._name == 'ir.actions.act_window':
                args.append(('res_model', '=', self.env.context['model']))
            #elif self._name == 'ir.actions.act_url':
            #    args.append(('_model', '=', self.env.context['model']))
        return super()._name_search(name, args, operator, limit, name_get_uid)
