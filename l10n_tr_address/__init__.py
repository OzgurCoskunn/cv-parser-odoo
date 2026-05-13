# -*- coding: utf-8 -*-
from . import models

import os
import csv
from odoo import SUPERUSER_ID
from odoo.tools.sql import table_exists

def _post_init(env):
    cr = env.cr
    cr.execute("""ALTER TABLE res_country_town ADD COLUMN parent_id integer""")
    cr.execute("""ALTER TABLE res_country_district ADD COLUMN parent_id integer""")
    cr.execute("""ALTER TABLE res_country_street ADD COLUMN parent_id integer""")

    path = os.path.dirname(os.path.realpath(__file__))

    town_rows = []
    town_data = os.path.join(path, 'data', 'town.csv')
    with open(town_data, mode='r') as data:
        rows = csv.reader(data, delimiter=';')
        next(rows, None)
        for row in rows:
            town_rows.append(row)

    district_rows = []
    district_data = os.path.join(path, 'data', 'district.csv')
    with open(district_data, mode='r') as data:
        rows = csv.reader(data, delimiter=';')
        next(rows, None)
        for row in rows:
            district_rows.append(row)

    street_rows = []
    street_data = os.path.join(path, 'data', 'street.csv')
    with open(street_data, mode='r') as data:
        rows = csv.reader(data, delimiter=';')
        next(rows, None)
        for row in rows:
            street_rows.append(row)


    if town_rows:
        cr.execute("""INSERT INTO res_country_town (parent_id,code,name) VALUES %s""" % ",".join([
            """(%s,%s,$$%s$$)""" % (row[0], row[1], row[2]) for row in town_rows]
        ))
    if district_rows:
        cr.execute("""INSERT INTO res_country_district (parent_id,code,name) VALUES %s""" % ",".join([
            """(%s,%s,$$%s$$)""" % (row[0], row[1], row[2]) for row in district_rows]
        ))
    if street_rows:
        cr.execute("""INSERT INTO res_country_street (parent_id,code,name) VALUES %s""" % ",".join([
            """(%s,%s,$$%s$$)""" % (row[0], row[1], row[2]) for row in street_rows]
        ))


    cr.execute("""
        UPDATE res_country_town tw SET
            create_date = (now() at time zone 'UTC'),
            write_date = (now() at time zone 'UTC'),
            create_uid = %s,
            write_uid = %s,
            active = true,
            state_id = st.id
        FROM (
            SELECT s.id, CAST (s.code AS INTEGER) AS code
            FROM res_country_state s
            JOIN res_country c ON c.id = s.country_id
            WHERE c.code = 'TR'
        ) st
        WHERE st.code = tw.parent_id
    """, (SUPERUSER_ID, SUPERUSER_ID))
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
    cr.execute("""
        UPDATE res_country_street sr SET
            create_date = (now() at time zone 'UTC'),
            write_date = (now() at time zone 'UTC'),
            create_uid = %s,
            write_uid = %s,
            active = true,
            district_id = ds.id
        FROM (
            SELECT d.id, CAST (d.code AS INTEGER) AS code
            FROM res_country_district d
            JOIN res_country_town t ON t.id = d.town_id
            JOIN res_country_state s ON s.id = t.state_id
            JOIN res_country c ON c.id = s.country_id
            WHERE c.code = 'TR'
        ) ds
        WHERE ds.code = sr.parent_id
    """, (SUPERUSER_ID, SUPERUSER_ID))

    cr.execute("""ALTER TABLE res_country_town DROP COLUMN parent_id""")
    cr.execute("""ALTER TABLE res_country_district DROP COLUMN parent_id""")
    cr.execute("""ALTER TABLE res_country_street DROP COLUMN parent_id""")

def _uninstall(env):
    cr = env.cr
    if table_exists(cr, "res_country_street"):
        cr.execute("""DROP TABLE res_country_street CASCADE""")
    if table_exists(cr, "res_country_district"):
        cr.execute("""DROP TABLE res_country_district CASCADE""")
    if table_exists(cr, "res_country_town"):
        cr.execute("""DROP TABLE res_country_town CASCADE""")
