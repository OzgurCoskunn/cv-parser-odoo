# -*- coding: utf-8 -*-
from odoo import models


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(self):
        modules = super(Http, self)._get_translation_frontend_modules_name()
        return modules + ['l10n_tr_address_website_sale']

