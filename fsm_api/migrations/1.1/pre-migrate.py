# -*- coding: utf-8 -*-

def migrate(cr, version):
    cr.execute("""ALTER TABLE fsm_api_spec_service ADD COLUMN temp_ref varchar""")
    cr.execute("""ALTER TABLE fsm_api_spec_service ADD COLUMN temp_soap_ref varchar""")
    cr.execute("""UPDATE fsm_api_spec_service SET temp_ref = code""")
    cr.execute("""UPDATE fsm_api_spec_service SET temp_soap_ref = soap_method""")
