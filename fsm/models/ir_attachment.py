# -*- coding: utf-8 -*-
from odoo import models, fields


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    avatar_128 = fields.Image(related='datas')
    fsm_document_type = fields.Selection([('itf', 'İşlem Takip Formu')])
    fsm_document_serial = fields.Char()

    def unlink_fsm_file(self):
        record = self.env[self.res_model].browse(self.res_id)
        self.unlink()
        if hasattr(record, 'unlink_fsm_file'):
            record.unlink_fsm_file()
        return {'type': 'fsm.reload'}
