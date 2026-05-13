from . import mail_activity
from . import stock_picking
from . import stock_location
from . import stock_warehouse
from . import stock_quant
from . import stock_rule
from . import stock_lot
from . import sale_order
from . import fsm_project
from . import fsm_task
from . import fsm_type
from . import fsm_stage
from . import fsm_package
from . import fsm_button
from . import fsm_reason
from . import fsm_todo
from . import fsm_auto
from . import fsm_flow
from . import fsm_form
from . import fsm_service
from . import fsm_appointment
from . import sla_agreement
from . import sla_ticket
#from . import ir_ui_menu
from . import ir_attachment
from . import ir_model_fields
from . import ir_actions_actions
from . import account_analytic_line
from . import product_template
from . import res_partner
from . import res_users
from . import crm_team

from odoo import models


class FsmFile(models.AbstractModel):
    _name = 'fsm.file'
    _description = 'Field Service Management: Files'

    def _get_readable_fields(self):
        return {'type'}


class FsmReload(models.AbstractModel):
    _name = 'fsm.reload'
    _description = 'Field Service Management: Reload Action'

    def _get_readable_fields(self):
        return {'type'}
