from odoo import models, fields, api, _


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    def get_action_picking_tree_ready(self):
        action = super(StockPickingType, self).get_action_picking_tree_ready()
        if self.env.context.get('barcode_view'):
            view_id = self.env.ref('barcode_wms.stock_picking_view_kanban_barcode', raise_if_not_found=False)
            if view_id:
                action['views'] = [(view_id.id, 'kanban')]
                action['view_mode'] = 'kanban'
                action['target'] = 'fullscreen'
        return action
