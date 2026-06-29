# -*- coding: utf-8 -*-

import json
import time
import logging
import codecs
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class DeliveryHepsiJetWebhookController(http.Controller):

    @http.route(['/hjstatusupdate'], type='http', auth='public', csrf=False, methods=['POST'])
    def hepsijet_status_update(self, **post):
        json_string = request.httprequest.data
        if isinstance(json_string, bytes):
            json_string = json_string.decode('utf-8')

        json_string = codecs.decode(json_string, 'unicode_escape').encode('latin1').decode('utf-8')
        data = json.loads(json_string)
        tracking_ref = data.get('trackingEvent', {}).get('packageInfo', {}).get('trackingCode')
        picking = request.env['stock.picking'].sudo().search([('carrier_tracking_ref', '=', tracking_ref)], limit=1)

        log = {
            'method': 'webhook',
            'now': time.time(),
            'url': request.httprequest.url,
            'request': json.dumps(data, default=str, ensure_ascii=False),
            'headers': json.dumps(request.httprequest.headers, default=str, ensure_ascii=False),
            'reference': tracking_ref,
            'picking_id': picking.id if picking else False,
            'environment': picking.carrier_id.prod_environment if picking else 'P',
        }
        if not picking:
            message = _('Picking not found for tracking reference: %s') % tracking_ref
            status = 404
            log.update({
                'status': False,
                'message': message,
                'code': status,
            })
            request.env['delivery.log'].sudo()._log(log)
            return request.make_response(
                message,
                status=status,
                headers=[('Content-Type', 'application/json')]
            )

        picking.update_delivery_hepsijet_state()
        #result = picking._update_delivery_hepsijet_webhook_state(data)
        #if isinstance(result, str):
        #    message = _('An error occured')
        #    status = 500
        #    log.update({
        #        'status': False,
        #        'message': message,
        #        'code': status,
        #        'debug': result
        #    })
        #    request.env['delivery.log'].sudo()._log(log)
        #    return request.make_response(
        #        message,
        #        status=status,
        #        headers=[('Content-Type', 'application/json')]
        #    )

        message = _('Webhook has been processed successfully')
        status = 200
        log.update({
            'status': True,
            'message': message,
            'code': status,
        })
        request.env['delivery.log'].sudo()._log(log)
        return request.make_response(
            message,
            status=status,
            headers=[('Content-Type', 'application/json')]
        )
