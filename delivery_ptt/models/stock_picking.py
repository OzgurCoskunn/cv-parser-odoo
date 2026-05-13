# -*- coding: utf-8 -*-
import requests
import gc
from dateutil import parser
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.depends('carrier_id')
    def _compute_delivery_ptt_ok(self):
        for picking in self:
            picking.delivery_ptt_ok = picking.carrier_id.delivery_type == 'ptt'

    @api.depends('delivery_tracking_ids')
    def _compute_delivery_ptt_done(self):
        for picking in self:
            picking.delivery_ptt_done = any(line.transaction == 'Teslim Edildi' or line.transaction == 'Satıcıya İade Edildi' for line in picking.delivery_tracking_ids)

    delivery_ptt_ok = fields.Boolean(string='Ptt Kargo', compute='_compute_delivery_ptt_ok', store=True)
    delivery_ptt_done = fields.Boolean(string='Ptt Kargo Delivered', compute='_compute_delivery_ptt_done', store=True)
    delivery_ptt_tracking_url = fields.Char(string='Ptt Kargo Tracking URL')
    delivery_ptt_connector_ok = fields.Boolean(string='Ptt Kargo Connector')
    delivery_ptt_connector_state = fields.Boolean(string='Ptt Kargo Connector State', readonly=True)
    delivery_ptt_connector_message = fields.Char(string='Ptt Kargo Connector Message', readonly=True)

    def get_delivery_ptt_log(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        connectors = self.env['syncops.connector'].sudo().with_context(active_test=False)._find('delivery_get_order', company=company)
        if not connectors:
            raise UserError(_('No syncOPS connector found'))

        if not self.id:
            raise UserError(_('Please save picking before checking connector logs'))

        result = []
        try:
            url = self.env['ir.config_parameter'].sudo().get_param('syncops.url')
            if not url:
                raise ValidationError(_('No syncOPS endpoint URL found'))

            url += '/api/v1/log'
            connector = connectors[0]
            response = requests.get(url, params={
                'username': connector.username,
                'token': ','.join(connectors.mapped('token')),
                'reference': str(self.id),
            })
            if response.status_code == 200:
                results = response.json()
                if not results['status'] == 0:
                    raise UserError(results['message'])
                logs = results.get('logs', [])
                for log in logs:
                    result.append({
                        'connector_id': connector.id,
                        'company_id': self.env.company.id,
                        'date': parser.parse(log['date']),
                        'partner_name': log['partner'],
                        'connector_name': log['connector'],
                        'token_name': log['token'],
                        'method_name': log['method'],
                        'status': log['status'],
                        'state': log['state'],
                        'message': log['message'],
                        'request_data': log['request_data'],
                        'request_method': log['request_method'],
                        'request_url': log['request_url'],
                        'response_code': log['response_code'],
                        'response_message': log['response_message'],
                        'response_data': log['response_data'],
                    })
            else:
                raise UserError(response.text or response.reason)
        except Exception as e:
            raise UserError(str(e))

        if result:
            logs = self.env['syncops.log'].sudo().create(result)
            action = self.env.ref('connector_syncops.action_log').sudo().read()[0]
            action['context'] = {'create': False, 'delete': False, 'edit': False, 'import': False}
            action['domain'] = [('id', 'in', logs.ids)]
            return action
        else:
            raise UserError(_('No log found'))
        
    def _get_delivery_ptt_domain(self):
        return [
            ('state', '=', 'done'),
            ('delivery_ptt_ok', '=', True),
            ('delivery_ptt_done', '=', False),
            ('carrier_tracking_ref', '!=', False),
        ]

    def update_delivery_ptt_state(self):
        domain = self._get_delivery_ptt_domain()
        if self:
            domain.append(('id', 'in', self.ids))

        pickings = self.search(domain, order='id desc')
        pickings._update_delivery_ptt_state()

    def _get_delivery_ptt_state(self, code):
        return self.carrier_id.delivery_status_mapping_ids.get_status(code=code)

    def _delivery_ptt_generate_barcode(self):
        seq = self.env['ir.sequence'].next_by_code('delivery.barcode')
        check_digit = self._delivery_ptt_calculate_check_digit(seq)
        return seq + str(check_digit)
    
    def _delivery_ptt_calculate_check_digit(self, barcode):
        multipliers = [1, 3] * 6
        total = sum(int(barcode[i]) * multipliers[i] for i in range(len(barcode)))
        check_digit = (10 - (total % 10)) % 10
        return check_digit

    @api.model
    def _update_delivery_ptt_state(self):
        if not self:
            return

        params = {
            'first_barcode': self[0].carrier_tracking_ref,
            'las_barcode': self[-1].carrier_tracking_ref,
        }
        result = self.env['syncops.connector'].sudo()._execute('delivery_get_order', params=params, reference=str(self[0].id), connectors=self[0].carrier_id.delivery_ptt_connector_id) or []
        for res in result[0].get('dongu', []):
            picking = self.filtered(lambda p: p.carrier_tracking_ref == res.get('barkod_no'))
            if not picking:
                continue

            if res['barkod_no']:
                date_obj = datetime.strptime(res['son_islem_tarihi'], '%Y%m%d')
                tx_date = date_obj.strftime('%d-%m-%Y')
                status_code = res['gonderi_durumu']
                if not picking.delivery_tracking_ids.filtered(lambda t: t.status == status_code):
                    tx_state = picking._get_delivery_ptt_state(status_code)
                    picking.delivery_tracking_ids.sudo().create({
                        'name': picking.carrier_id.name,
                        'picking_id': picking.id,
                        'carrier_id': picking.carrier_id.id,
                        'customer_barcode': res.get('barkod_no'),
                        'transaction': res['gonderi_durum_aciklama'],
                        'location': res['kabul_merkezi'],
                        'delivery_type': 'RETAIL',
                        'sale_order_id': picking.sale_id.id,
                        'transaction_datetime': date_obj - timedelta(hours=3),
                        'transaction_date': tx_date,
                        'status': status_code,
                        'state': tx_state.code,
                        'status_id': tx_state.id,
                    })
                    picking.write({
                        'carrier_state': tx_state.code,
                        'carrier_status_id': tx_state.id,
                        'carrier_doc_id': res.get('tracking_reference'),
                    })

    def cancel_shipment(self):
        if self.delivery_ptt_ok:
            params = {
                'reference' : self.carrier_tracking_ref,
                'document_name' : self.carrier_doc_id,
            }
            result = self.env['syncops.connector'].sudo()._execute('delivery_patch_order_cancel', params=params, reference=str(self.id), connectors=self.carrier_id.delivery_ptt_connector_id)
            if not result:
                raise ValidationError(_('An error occured. Please check the logs for further detail.'))

            for r in result:
                if r['error'] != '1':
                    raise ValidationError(_('Connector process failed. %s') % (r.get('description')))

        return super(StockPicking, self).cancel_shipment()

    def action_cancel(self):
        for picking in self:
            if picking.delivery_ptt_ok:
                picking.cancel_shipment()
        return super(StockPicking, self).action_cancel()
