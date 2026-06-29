from odoo import models, fields, _


class StockReturnPickingHepsiJetWarning(models.TransientModel):
    _name = 'stock.return.picking.hepsijet.warning'
    _description = 'HepsiJet Stock Return Warning'

    return_id = fields.Many2one('stock.return.picking')

    def action_back(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('HepsiJet Return Date'),
            'res_model': 'stock.return.picking',
            'res_id': self.return_id.id,
            'view_mode': 'form',
            'target': 'new',
        }
