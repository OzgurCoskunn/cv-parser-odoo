# -*- coding: utf-8 -*-
import re
import xlrd
import base64

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class FsmTaskImport(models.TransientModel):
    _name = 'fsm.task.import'
    _description = 'Field Service: Import Tasks'

    file = fields.Binary()
    filename = fields.Char()
    line_ids = fields.One2many('fsm.task.import.line', 'wizard_id', 'Lines', readonly=True)

    def _prepare_row(self, line):
        return {
            'project_id': line.project_id.id,
            'type_id': line.type_id.id,
            'sla_id': line.sla_id.id,
            'setup_key': line.setup_key,
            'setup_uid': line.setup_uid,
            'setup_merchant_uid': line.setup_merchant_uid,
            'merchant_id': line.merchant_id.id,
            'merchant_service_id': line.merchant_id.id,
            'product_id': line.product_id.id,
            'product_lot_id': line.product_lot_id.id,
            'product_lot_ref': line.product_lot_ref,
        }

    @api.onchange('file')
    def onchange_file(self):
        if self.file:
            data = base64.b64decode(self.file)
            wb = xlrd.open_workbook(file_contents=data)
            sheet = wb.sheet_by_index(0)
            values = []
            cols = []
            projects = self.env['fsm.project'].sudo()
            lots = self.env['stock.lot'].sudo()
            for i in range(sheet.nrows):
                row = sheet.row_values(i)
                if not i:
                    cols = row
                    if not 'PROJE ADI' in cols:
                        raise UserError(_('Please create a "PROJE ADI" column'))
                    elif not 'TÜR' in cols:
                        raise UserError(_('Please create a "TÜR" column'))
                    elif not 'SLA' in cols:
                        raise UserError(_('Please create a "SLA" column'))
                    #elif not 'KURULUM ANAHTARI' in cols:
                    #    raise UserError(_('Please create a "KURULUM ANAHTARI" column'))
                    #elif not 'KURULUM NO' in cols:
                    #    raise UserError(_('Please create a "KURULUM NO" column'))
                    #elif not 'KURULUM SATICI NO' in cols:
                    #    raise UserError(_('Please create a "KURULUM SATICI NO" column'))
                    elif not 'SATICI ADI' in cols:
                        raise UserError(_('Please create a "SATICI ADI" column'))
                    elif not 'ÜRÜN ADI' in cols:
                        raise UserError(_('Please create a "ÜRÜN ADI" column'))
                    elif not 'ÜRÜN LOT/SERİ NO' in cols:
                        raise UserError(_('Please create a "ÜRÜN LOT/SERİ NO" column'))
                    elif not 'ÜRÜN LOT/SERİ REFERANSI' in cols:
                        raise UserError(_('Please create a "ÜRÜN LOT/SERİ REFERANSI" column'))
                else:
                    row = [re.sub(r'\.0$', '', str(r)) for r in row]
                    value = dict(zip(cols, row))
                    project = projects.search([('name', '=', value['PROJE ADI'])])
                    if not project:
                        raise ValidationError(_('Project "%s" cannot be found.') % value['PROJE ADI'])
                    if len(project) > 1:
                        raise ValidationError(_('Project name "%s" belongs to more than one project.') % value['PROJE ADI'])

                    if value['TÜR'] not in project.type_ids.mapped('type_id.name'):
                        raise ValidationError(_('Type "%s" cannot be used in project "%s".') % (value['TÜR'], value['PROJE ADI']))

                    product = project.product_ids.filtered(lambda p: p.name == str(value['ÜRÜN ADI']))
                    if not product:
                        raise ValidationError(_('Product "%s" cannot be used in project "%s".') % (value['ÜRÜN ADI'], value['PROJE ADI']))
                    product = product[0]

                    lot = lots.search([('product_id', '=', product.id), ('name', '=', str(value['ÜRÜN LOT/SERİ NO']))], limit=1)
                    if not lot:
                        raise ValidationError(_('Lot "%s" cannot be found.') % value['ÜRÜN LOT/SERİ NO'])
                    if lot.ref != str(value['ÜRÜN LOT/SERİ REFERANSI']):
                        raise ValidationError(_('Lot reference "%s" are not matched with reference of lot/serial "%s".') % (value['ÜRÜN LOT/SERİ REFERANSI'], value['ÜRÜN LOT/SERİ NO']))

                    values.append({
                        'project_id': project.id,
                        'setup_key': value.get('KURULUM ANAHTARI', ''),
                        'setup_uid': value.get('KURULUM NO', ''),
                        'setup_merchant_uid': value.get('KURULUM SATICI NO', ''),
                        'product_id': product.id,
                        'product_lot_id': lot.id,
                        'product_lot_ref': lot.ref,
                        'sla_id': project.sla_ids.filtered(lambda s: s.name == str(value['SLA'])),
                        'type_id': self.env['fsm.type'].search([('name', '=', str(value['TÜR']))], limit=1).id,
                        'merchant_id': self.env['res.partner'].search([('name', '=', str(value['SATICI ADI']))], limit=1).id,
                    })
            self.line_ids = [(5, 0, 0)] + [(0, 0, value) for value in values]

        else:
            self.line_ids = [(5, 0, 0)]

    def confirm(self):
        tasks = self.env['fsm.task']
        for line in self.line_ids:
            row = self._prepare_row(line)
            tasks.create(row)
        return {'type': 'fsm.reload'}


class FsmTaskImportLine(models.TransientModel):
    _name = 'fsm.task.import.line'
    _description = 'Field Service: Import Task Lines'

    wizard_id = fields.Many2one('fsm.task.import')
    project_id = fields.Many2one('fsm.project', readonly=True, required=True)
    type_id = fields.Many2one('fsm.type', readonly=True, required=True)
    sla_id = fields.Many2one('sla.agreement', readonly=True, required=True)
    setup_key = fields.Char(readonly=True)
    setup_uid = fields.Char(readonly=True)
    setup_merchant_uid = fields.Char(readonly=True)
    merchant_id = fields.Many2one('res.partner', readonly=True, required=True)
    product_id = fields.Many2one('product.product', readonly=True, required=True)
    product_lot_id = fields.Many2one('stock.lot', readonly=True)
    product_lot_ref = fields.Char(readonly=True)
    company_id = fields.Many2one('res.company', readonly=True, required=True, default=lambda self: self.env.company)
