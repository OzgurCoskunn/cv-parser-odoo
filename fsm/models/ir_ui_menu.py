# -*- coding: utf-8 -*-
from odoo import models

class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def get_user_roots(self):
        if self.env.user.has_group('fsm.group_base'):
            return self.env.ref('fsm.menu_main')
        return super().get_user_roots()
