# -*- coding: utf-8 -*-

from odoo.http import request
from odoo import models, http, _
from odoo.addons.website_sale.controllers import main


class WebsiteSale(main.WebsiteSale):

    main.WebsiteSale.WRITABLE_PARTNER_FIELDS.append('street3')

    def _get_country_related_render_values(self, kw, render_values):
        res = super(WebsiteSale, self)._get_country_related_render_values(kw, render_values)
        company = request.env.company.sudo()
        res['field_town_selection'] = company.field_town_selection
        res['field_district_selection'] = company.field_district_selection
        res['field_street_selection'] = company.field_street_selection
        res['field_table_name_selection'] = company.field_table_name_selection

        if not res['country']:
            res['country'] = company.country_id

        res['country_towns'] = []
        res['country_districts'] = []
        res['country_streets'] = []
        values = render_values['checkout']
        if values:
            if 'state_id' in values:
                if isinstance(values['state_id'], str):
                    values['state_id'] = request.env['res.country.state'].sudo().browse(int(values['state_id']))
                res['country_towns'] = values['state_id'].sudo().town_ids
                res['tax_offices'] = getattr(values['state_id'].sudo(), 'tax_office_ids', [])

            if 'town_id' in values:
                if isinstance(values['town_id'], str):
                    values['town_id'] = request.env['res.country.town'].sudo().browse(int(values['town_id']))
                res['country_districts'] = values['town_id'].sudo().district_ids

            if 'district_id' in values:
                if isinstance(values['district_id'], str):
                    values['district_id'] = request.env['res.country.district'].sudo().browse(int(values['district_id']))
                res['country_streets'] = values['district_id'].sudo().street_ids

            if isinstance(values, models.Model):
                res['is_company'] = values['parent_id'] and values['parent_id']['is_company'] or values['is_company']
            else:
                res['is_company'] = values.get('company_type') == 'company'

        return res

    @http.route(['/shop/country_infos/<model("res.country"):country>'], type='json', auth="public", methods=['POST'], website=True)
    def country_infos(self, country, mode, **kw):
        res = super(WebsiteSale, self).country_infos(country, mode, **kw)
        res['state_required'] = True
        del res['fields']
        return res

    @http.route(['/shop/state_infos/<model("res.country.state"):state>'], type='json', auth="public", methods=['POST'], website=True)
    def state_infos(self, state, **kw):
        return dict(
            towns = [[st.id, st.name] for st in state.sudo().town_ids],
            tax_offices = [[to.id, to.name] for to in getattr(state.sudo(), 'tax_office_ids', [])]
        )

    @http.route(['/shop/town_infos/<model("res.country.town"):town>'], type='json', auth="public", methods=['POST'], website=True)
    def town_infos(self, town, **kw):
        return dict(districts = [[ds.id, ds.name] for ds in town.sudo().district_ids])

    @http.route(['/shop/district_infos/<model("res.country.district"):district>'], type='json', auth="public", methods=['POST'], website=True)
    def district_infos(self, district, **kw):
        return dict(streets = [[st.id, st.name] for st in district.sudo().street_ids])

    def _get_mandatory_fields_billing(self, country_id=False):
        res = super(WebsiteSale, self)._get_mandatory_fields_billing(country_id)
        res.remove('street')
        res.remove('city')
        return res

    def _get_mandatory_fields_shipping(self, country_id=False):
        res = super(WebsiteSale, self)._get_mandatory_fields_shipping(country_id)
        res.remove('street')
        res.remove('city')
        return res

    def _checkout_form_save(self, mode, checkout, all_values):
        partner_id = super(WebsiteSale, self)._checkout_form_save(mode, checkout, all_values)

        Partner = request.env['res.partner']
        company = request.env.company.sudo()
        partner = Partner.sudo().browse(partner_id)

        if mode[1] == 'billing':
            partner.write({
                'type': 'contact',
                'is_company': False,
                'company_name': False,
            })

            values = {
                'vat': all_values.get('vat'),
                'zip': all_values.get('zip'),
                'name': all_values.get('name'),
                'email': all_values.get('email'),
                'phone': all_values.get('phone'),
                'street3': all_values.get('street3'),
                'table_name': all_values.get('table_name'),
            }

            if 'state_id' in all_values:
                values.update({'state_id': all_values['state_id'] and int(all_values['state_id']) or False})
            if 'tax_office_id' in all_values:
                values.update({'tax_office_id': all_values['tax_office_id'] and int(all_values['tax_office_id']) or False})
            if 'country_id' in all_values:
                values.update({'country_id': all_values['country_id'] and int(all_values['country_id']) or Partner.sudo().env.ref('base.tr').id})
            else:
                values.update({'country_id': Partner.sudo().env.ref('base.tr').id})
            if company.field_town_selection:
                values.update({'town_id': all_values['town_id'] and int(all_values['town_id']) or False})
            else:
                values.update({'city': all_values.get('city')})
            if company.field_district_selection:
                values.update({'district_id': all_values['district_id'] and int(all_values['district_id']) or False})
            else:
                values.update({'street': all_values.get('street')})
            if company.field_street_selection:
                values.update({'street_id': all_values['street_id'] and int(all_values['street_id']) or False})
            else:
                values.update({'street2': all_values.get('street2')})

            is_company = all_values.get('company_type') == 'company'
            values.update({
                'type': 'invoice',
                'is_company': is_company,
                'name': is_company and all_values.get('company_name') or all_values.get('name'),
            })
            if mode[0] == 'new':
                parent = Partner.sudo().with_context(tracking_disable=True).create(values)
                partner.write({'parent_id': parent.id})
            elif mode[0] == 'edit':
                parent = partner.commercial_partner_id
                if partner.id == parent.id:
                    parent = Partner.sudo().with_context(tracking_disable=True).create(values)
                    partner.write({'parent_id': parent.id})
                else:
                    parent.write(values)
        elif mode[1] == 'shipping':
            partner.write({
                'type': 'delivery',
                'is_company': False,
                'company_name': False,
            })

        return partner_id

    def checkout_form_validate(self, mode, all_form_values, data):
        error, error_message = super().checkout_form_validate(mode, all_form_values, data)
        company = request.env.company.sudo()
        if company.field_town_selection and not data.get('town_id'):
            error['town_id'] = 'error'
            error_message.append(_('Please select a town.'))
        if company.field_district_selection and not data.get('district_id'):
            error['district_id'] = 'error'
            error_message.append(_('Please select a district.'))
        if company.field_street_selection and not data.get('street_id'):
            error['street_id'] = 'error'
            error_message.append(_('Please select a street.'))
        if not company.field_town_selection and not data.get('city'):
            error['city'] = 'error'
            error_message.append(_('Please fill city/town field.'))
        if not company.field_district_selection and not data.get('street'):
            error['street'] = 'error'
            error_message.append(_('Please fill district field.'))
        if not company.field_street_selection and not data.get('street2'):
            error['street2'] = 'error'
            error_message.append(_('Please fill street field.'))
        if not data.get('street3'):
            error['street3'] = 'error'
            error_message.append(_('Please fill apartment / flat number field.'))
        if mode[1] == 'billing' and not data.get('vat'):
            error['vat'] = 'error'
            error_message.append(_('Please fill VAT number field.'))
        if mode[1] == 'billing' and data.get('company_type') == 'company' and not data.get('tax_office_id'):
            error['tax_office_id'] = 'error'
            error_message.append(_('Please fill tax office field.'))
        if data.get('zip'):
            country = request.env['res.country'].sudo().browse(int(data['country_id']))
            state = request.env['res.country.state'].sudo().browse(int(data['state_id']))
            if country and country == country.env.ref('base.tr') and state and state.code and data['zip'][0:2] != state.code:
                error['zip'] = 'error'
                error_message.append(_('The prefix of the zip code and the state code do not match.'))
            elif country and country == country.env.ref('base.tr') and len(data['zip']) != 5:
                error['zip'] = 'error'
                error_message.append(_('Zip format is incorrect.'))
        return error, error_message
