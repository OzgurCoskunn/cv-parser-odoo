# -*- coding: utf-8 -*-
from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def post_barcode_process(self, move_ids, quantities_by_move):
        """
        Post-process method called when exiting barcode interface.
        
        Called from JavaScript _onExit() method with aggregated quantities from 
        initialState.lines, grouped by move_id.
        
        :param move_ids: list of stock.move IDs (from this.moveIds in JS)
        :param quantities_by_move: dict mapping move_id (int) to dict with:
            - quantity_done: total qty_done from all move lines for this move
            - reserved_uom_qty: total reserved_uom_qty from all move lines
        
        Example quantities_by_move structure:
        {
            123: {'quantity_done': 10.0, 'reserved_uom_qty': 15.0},
            124: {'quantity_done': 5.0, 'reserved_uom_qty': 5.0}
        }
        """
        if not move_ids:
            return True
        
        # Convert string keys to integers (JSON converts dict keys to strings)
        if quantities_by_move and isinstance(next(iter(quantities_by_move.keys())), str):
            quantities_by_move = {int(k): v for k, v in quantities_by_move.items()}
        
        moves = self.browse(move_ids)
        
        for move in moves:
            if move.id not in quantities_by_move:
                continue
                
            qty_data = quantities_by_move[move.id]
            quantity_done = qty_data.get('quantity_done', 0.0)
            reserved_qty = qty_data.get('reserved_uom_qty', 0.0)
            
            # Log the processing for debugging
            _logger.info(
                f"Barcode exit - Move {move.id} ({move.product_id.display_name}): "
                f"Done={quantity_done}, Reserved={reserved_qty}"
            )
            
            # You can add custom business logic here:
            # - Check if move is complete (quantity_done >= reserved_uom_qty)
            # - Trigger notifications
            # - Update custom fields
            # - Generate reports
            # - etc.
            
            if quantity_done > 0 and move.state in ('assigned', 'partially_available'):
                # Move has been partially or fully processed
                pass
            
            if quantity_done >= reserved_qty and reserved_qty > 0:
                # Move is fully processed
                _logger.debug(f"Move {move.id} fully processed via barcode")
        
        return True
