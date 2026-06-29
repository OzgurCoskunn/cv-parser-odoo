# -*- coding: utf-8 -*-
from odoo import models, fields


class FsmButtonAction(models.Model):
    _inherit = 'fsm.button.action'

    picking_carrier_hepsijet_egyg = fields.Boolean(string='Picking Delivery Carrier HepsiJet EGYG')
    picking_carrier_hepsijet_egyg_location_id = fields.Many2one('stock.location', string='Picking Delivery Carrier HepsiJet EGYG Location')
    picking_carrier_hepsijet_contract = fields.Boolean(string='Picking Delivery Carrier HepsiJet Contract')

    def _postprocess_picking(self, task, picking):
        if picking.delivery_hepsijet_ok:
            if self.picking_carrier_hepsijet_egyg:
                picking.write({'delivery_hepsijet_egyg_ok': True})
            if self.picking_carrier_hepsijet_contract:
                product = self.env.ref('delivery_hepsijet.product_contract')
                for subtask in task.child_ids:
                    contract = picking.create({
                        'picking_type_id': picking.picking_type_id.id,
                        'fsm_task_id': subtask.id,
                        'fsm_flow_stage_id': subtask.flow_stage_id.id,
                        'partner_id': subtask.merchant_service_id.id,
                        'location_id': picking.location_id.id,
                        'location_dest_id': picking.location_dest_id.id,
                        'carrier_id': picking.carrier_id.id,
                        'delivery_hepsijet_contract_picking_res_id': picking.id,
                        'move_ids': [(0, 0, {
                            'name': product.name,
                            'product_id': product.id,
                            'product_uom_qty': 1,
                            'location_id': picking.location_id.id,
                            'location_dest_id': picking.location_dest_id.id,
                        })]
                    })
                    contract.action_assign()
                    picking.write({'delivery_hepsijet_contract_picking_id': contract.id})
