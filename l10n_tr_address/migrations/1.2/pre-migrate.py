# -*- coding: utf-8 -*-
from odoo.tools.sql import column_exists

def migrate(cr, version):
    if not column_exists(cr, "res_partner", "uavt_code"):
        cr.execute("ALTER TABLE res_partner ADD COLUMN uavt_code varchar")
