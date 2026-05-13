from odoo.addons.portal.controllers import portal
from odoo.http import request, route


class CustomerPortal(portal.CustomerPortal):

    @route(['/my/account/states/<model("res.country.state"):state>'], type='jsonrpc', auth="user", methods=['POST'], website=True)
    def account_states(self, state):
        return dict(towns = [[st.id, st.name] for st in state.sudo().town_ids])

    @route(['/my/account/towns/<model("res.country.town"):town>'], type='jsonrpc', auth="user", methods=['POST'], website=True)
    def account_towns(self, town):
        return dict(districts = [[ds.id, ds.name] for ds in town.sudo().district_ids])

    @route(['/my/account/districts/<model("res.country.district"):district>'], type='jsonrpc', auth="user", methods=['POST'], website=True)
    def account_districts(self, district):
        return dict(streets = [[st.id, st.name] for st in district.sudo().street_ids])

    @route(['/my/account'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        company = request.env.company.sudo()
        values.update({
            'error': {},
            'error_message': [],
            'field_town_selection': company.field_town_selection,
            'field_district_selection': company.field_district_selection,
            'field_street_selection': company.field_street_selection,
        })

        if post and request.httprequest.method == 'POST':
            error, error_message = self.details_form_validate(post)
            values.update({'error': error, 'error_message': error_message})
            values.update(post)
            if not error:
                # Odoo 19: Directly use post data instead of MANDATORY/OPTIONAL_BILLING_FIELDS
                values = {key: post[key] for key in post.keys() if key not in ['redirect']}
                for field in set(['country_id', 'state_id', 'town_id', 'district_id', 'street_id']) & set(values.keys()):
                    try:
                        values[field] = int(values[field])
                    except:
                        values[field] = False
                values.update({'zip': values.pop('zipcode', '')})
                self.on_account_update(values, partner)
                partner.sudo().write(values)
                if redirect:
                    return request.redirect(redirect)
                return request.redirect('/my/home')

        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])
        country_towns = request.env['res.country.town'].sudo().search([('state_id', '=', partner.state_id.id)]) or []
        country_districts = request.env['res.country.district'].sudo().search([('town_id', '=', partner.town_id.id)]) or []
        country_streets = request.env['res.country.street'].sudo().search([('district_id', '=', partner.district_id.id)]) or []

        values.update({
            'redirect': redirect,
            'partner': partner,
            'countries': countries,
            'states': states,
            'country_towns': country_towns,
            'country_districts': country_districts,
            'country_streets': country_streets,
            'page_name': 'my_details',
            'partner_can_edit_vat': partner.can_edit_vat(),
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
        })

        response = request.render("portal.portal_my_details", values)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response
