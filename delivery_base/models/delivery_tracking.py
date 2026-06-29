# -*- coding: utf-8 -*-
from odoo import models, fields


class DeliveryTracking(models.Model):
    _name = 'delivery.tracking'
    _description = 'Delivery Tracking Status'
    _order = 'transaction_datetime'

    name = fields.Char(string='Name', readonly=True)
    carrier_id = fields.Many2one('delivery.carrier', string='Carrier', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Picking', readonly=True)
    location = fields.Char(string='Delivery Location', readonly=True)
    transaction = fields.Char(string='Transaction', readonly=True)
    transaction_datetime = fields.Datetime(string='Transaction Datetime', readonly=True)
    transaction_date = fields.Char(string='Transaction Date', readonly=True)
    transaction_time = fields.Char(string='Transaction Time', readonly=True)
    delivery_type = fields.Char(string='Delivery Type', readonly=True)
    delivery_status = fields.Selection([
        ('done', 'On Promised'),
        ('cancel', 'Not as Promised'),
        ('recall', 'Recalled'),
    ], string='Delivery Status')
    delivery_return_reason = fields.Char(string='Delivery Return Reason', readonly=True)
    delivery_return_reason_message = fields.Char(string='Delivery Return Reason Message', readonly=True)
    delivery_on_promised = fields.Boolean(string='On Promised')
    date_promised = fields.Datetime(string='Date Promised', readonly=True)
    customer_barcode = fields.Char(string='Customer Barcode', readonly=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', readonly=True)
    status = fields.Char(string='Status', readonly=True)
    state = fields.Selection([
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
    ], default='other', readonly=True)
    status_id = fields.Many2one('delivery.status', string='Carrier Status', readonly=True, copy=False)
    passing_time = fields.Char(string='Passing Time')
    passing_time_selection = fields.Selection([
        ('24', '24 Hours'),
        ('48', '48 Hours'),
        ('72', '72 Hours'),
        ('72+', 'More than 72 Hours'),
    ])
