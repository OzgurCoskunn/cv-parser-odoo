# -*- coding: utf-8 -*-
from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    def _compute_delivery_contract(self):
        for picking in self:
            attachments = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', picking._name),
                ('res_id', '=', picking.id),
            ], order='id')
            if attachments:
                rendered = attachments.filtered(lambda a: a.delivery_contract_rendered)
                signed = attachments.filtered(lambda a: a.delivery_contract_signed)
                picking.delivery_contract_rendered_id = rendered and rendered[0] or False
                picking.delivery_contract_signed_id = signed and signed[0] or False
            else:
                picking.delivery_contract_rendered_id = False
                picking.delivery_contract_signed_id = False

    def _compute_delivery_log_count(self):
        for picking in self:
            picking.delivery_log_count = len(picking.delivery_log_ids)

    carrier_state = fields.Selection([
        ('collected', 'Collected'),
        ('transferring', 'Transferring'),
        ('on_delivery_branch', 'On Delivery Branch'),
        ('on_delivery_courier', 'Courier On Delivery'),
        ('delivered', 'Delivered'),
        ('undelivered', 'Undelivered'),
        ('return_to_seller', 'Return to Seller'),
        ('unable_to_collect', 'Receiver Aborted Return'),
        ('retry', 'Retry'),
        ('signing', 'Signing'),
        ('signed', 'Signed'),
        ('not_signed', 'Not Signed'),
        ('dispatching', 'Dispatching'),
        ('other', 'Other'),
    ], string='Carrier State', readonly=True, copy=False)
    carrier_status_id = fields.Many2one('delivery.status', string='Carrier Status', readonly=True, copy=False)
    carrier_doc_id = fields.Char('Carrier Document ID', readonly=True, copy=False)
    delivery_tracking_ids = fields.One2many('delivery.tracking', 'picking_id', string='Delivery Tracking Status', readonly=True)
    delivery_log_count = fields.Integer(string='Delivery Log Count', compute='_compute_delivery_log_count')
    delivery_log_ids = fields.One2many('delivery.log', 'picking_id', string='Delivery Logs', readonly=True)
    delivery_contract_rendered_id = fields.Many2one('ir.attachment', string='Rendered Delivery Contract', compute='_compute_delivery_contract')
    delivery_contract_signed_id = fields.Many2one('ir.attachment', string='Signed Delivery Contract', compute='_compute_delivery_contract')

    def action_view_delivery_logs(self):
        self.ensure_one()
        action = self.env.ref('delivery_base.action_log').sudo().read()[0]
        action['domain'] = [('picking_id', '=', self.id)]
        return action
