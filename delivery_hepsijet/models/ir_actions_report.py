# -*- coding: utf-8 -*-
import base64
from odoo import models, fields


class Report(models.Model):
    _inherit='ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if isinstance(report_ref, str) and report_ref == 'delivery_hepsijet.template_zpl_pdf':
            pickings = self.env['stock.picking'].sudo().browse(res_ids)
            pairs = {}
            for picking in pickings:
                key = picking.syncops_connector_id.id or picking.carrier_id.delivery_hepsijet_connector_id.id
                if key not in pairs:
                    pairs[key] = self.env['stock.picking']
                pairs[key] |= picking
            for connector_id, picking_ids in pairs.items():
                params = {'reference': picking_ids.mapped('carrier_tracking_ref')}
                connectors = self.env['syncops.connector'].browse(connector_id)
                result, message = self.env['syncops.connector'].sudo()._execute('delivery_get_order_pdf', params=params, connectors=connectors, company=self.env.company, message=True)
                if message:
                    raise Exception('Error: %s' % message)

                pdf = None
                if result:
                    labels = result[0].get('labels', [])
                    for label in labels:
                        raw = label.replace('data:application/pdf;base64,', '')
                        pdf = base64.b64decode(raw)
                        break
                return pdf, 'pdf'
                #width, height = 4, 6
                #report = self._get_report(report_ref)
                #if report.paperformat_id:
                #    inch = 0.0393701
                #    width = round(report.paperformat_id.page_width * inch, 2)
                #    height = round(report.paperformat_id.page_height * inch, 2)

                #zpl = self._render_qweb_text(report_ref, res_ids, data=data)[0]
                #url = f'http://api.labelary.com/v1/printers/8dpmm/labels/{width}x{height}/0/'
                #files = {'file': zpl}
                #headers = {'Accept': 'application/pdf'}
                #response = requests.post(url, headers=headers, files=files, stream=True)

                #if response.status_code == 200:
                #    response.raw.decode_content = True
                #    return response.content, 'pdf'
                #else:
                #    Exception('Error: ' + response.text)
        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
