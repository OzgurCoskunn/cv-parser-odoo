# -*- coding: utf-8 -*-
    
import os
import csv
from odoo import SUPERUSER_ID

def migrate(cr, version):
    cr.execute("""ALTER TABLE res_country_district ADD COLUMN parent_id integer""")

    path = os.path.dirname(os.path.realpath(__file__))

    district_rows = []
    district_data = os.path.join(path + '/../..', 'data', 'district.csv')
    with open(district_data, mode='r') as data:
        rows = csv.reader(data, delimiter=';')
        next(rows, None)
        for row in rows:
            district_rows.append(row)

    cr.execute("""INSERT INTO res_country_district (parent_id,code,name) VALUES %s""" % ",".join([
        """(%s,%s,$$%s$$)""" % (row[0], row[1], row[2]) for row in district_rows]
    ))

    cr.execute("""
        UPDATE res_country_district ds SET
            create_date = (now() at time zone 'UTC'),
            write_date = (now() at time zone 'UTC'),
            create_uid = %s,
            write_uid = %s,
            active = true,
            town_id = tw.id
        FROM (
            SELECT t.id, CAST (t.code AS INTEGER) AS code
            FROM res_country_town t
            JOIN res_country_state s ON s.id = t.state_id
            JOIN res_country c ON c.id = s.country_id
            WHERE c.code = 'TR'
        ) tw
        WHERE tw.code = ds.parent_id
    """, (SUPERUSER_ID, SUPERUSER_ID))

    cr.execute("""ALTER TABLE res_country_district DROP COLUMN parent_id""")
