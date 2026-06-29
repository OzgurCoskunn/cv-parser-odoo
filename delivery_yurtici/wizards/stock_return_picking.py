# -*- coding: utf-8 -*-
import random

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.depends('picking_id')
    def _compute_delivery_yurtici_ok(self):
        for rec in self:
            rec.delivery_yurtici_ok = rec.picking_id.carrier_id.delivery_type == 'yurtici'

    delivery_yurtici_start_date = fields.Datetime(string='Yurtiçi Kargo Start Date')
    delivery_yurtici_end_date = fields.Datetime(string='Yurtiçi Kargo Return Date')
    delivery_yurtici_ok = fields.Boolean(compute='_compute_delivery_yurtici_ok')

    def create_returns(self):
        if self.env.context.get('skip_carrier'):
            return super(StockReturnPicking, self).create_returns()

        if self.delivery_yurtici_ok:
            today = fields.Datetime.today()
            if not self.delivery_yurtici_start_date or self.delivery_yurtici_start_date < today:
                raise UserError(_('The start date must be after today.'))
            if not self.delivery_yurtici_end_date or self.delivery_yurtici_start_date < today:
                raise UserError(_('The end date must be after today.'))

            params = {
                "returnCode": ''.join(random.choice('0123456789') for _ in range(10)),
                "startDate": self.delivery_yurtici_start_date.strftime("%Y%m%d"),
                "endDate": self.delivery_yurtici_end_date.strftime("%Y%m%d"),
            }
            connectors = self.picking_id.syncops_connector_id or self.picking_id.carrier_id.delivery_yurtici_connector_id
            result = self.env['syncops.connector'].sudo()._execute('delivery_post_order_return', params=params, reference=str(self.picking_id.id), connectors=connectors)
            if not result:
                raise ValidationError(_('An error occured. Please check the logs for further detail.'))

            result = result[0]

            if result['flag'] != '0':
                raise ValidationError(result['result'])

            res = super(StockReturnPicking, self).create_returns()
            returned = self.env['stock.picking'].browse(res['res_id'])
            returned.write({
                'carrier_id': self.picking_id.carrier_id.id,
                'carrier_tracking_ref': params['returnCode'],
            })
            return res

        return super(StockReturnPicking, self).create_returns()
