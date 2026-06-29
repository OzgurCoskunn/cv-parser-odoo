# -*- coding: utf-8 -*-
from odoo import models, fields


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    delivery_contract_rendered = fields.Boolean('Rendered Delivery Contract')
    delivery_contract_signed = fields.Boolean('Signed Delivery Contract')
