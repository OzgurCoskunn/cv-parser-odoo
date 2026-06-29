# -*- coding: utf-8 -*-

def migrate(cr, version):
    cr.execute("""UPDATE fsm_api_spec_service SET ref = temp_ref""")
    cr.execute("""UPDATE fsm_api_spec_service SET soap_ref = temp_soap_ref""")
    cr.execute("""ALTER TABLE fsm_api_spec_service DROP COLUMN temp_ref""")
    cr.execute("""ALTER TABLE fsm_api_spec_service DROP COLUMN temp_soap_ref""")
