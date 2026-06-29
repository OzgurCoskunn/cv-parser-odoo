# -*- coding: utf-8 -*-
from odoo import models


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    def _compute_display_name(self):
        if self.env.context.get('without_model'):
            for field in self:
                field.display_name = field.field_description
            return
        return super()._compute_display_name()
