import base64
from odoo import http
from odoo.http import request, Response

class SyncOpsController(http.Controller):

    @http.route('/syncops/pdf/<string:barcode>', type='http', auth='public', website=True)
    def syncops_pdf(self, barcode,**kwargs):
        connect = request.env['syncops.connector'].sudo()._execute

        result, message = connect('delivery_get_order_pdf', params={
            "reference": [barcode],
        },company=request.env['res.company'].sudo().browse(1), message=True)
        raw_data = result[0].get('data', {}).get('labels', [])[0]
        if raw_data.startswith('data:application/pdf;base64,'):
            raw_data = raw_data.replace('data:application/pdf;base64,', '')

        pdf_binary = base64.b64decode(raw_data)
        return Response(
            pdf_binary,
            content_type='application/pdf',
            headers=[('Content-Disposition', 'inline; filename="zpl.pdf"')]
        )