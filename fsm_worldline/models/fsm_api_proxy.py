# -*- coding: utf-8 -*-
from odoo import models, api


class FsmApiProxy(models.Model):
    _inherit = 'fsm.api.proxy'

    @api.onchange('provider_id')
    def onchange_provider_id(self):
        super().onchange_provider_id()
        if self.provider_id.code == 'worldline':
            if not self.name:
                self.name = self.provider_id.name
            self.update({
                'type': self.provider_id.type,
                'code': self.provider_id.code,
                'type_ok': True,
                'bank_ok': True,
                'city_ok': True,
                'town_ok': True,
                'status_ok': True,
            })
