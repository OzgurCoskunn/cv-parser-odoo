/** @odoo-module **/

import publicWidget from 'web.public.widget';
import { _t } from 'web.core';

publicWidget.registry.portalDetails.include({
    events: _.extend({
        'change select[name="state_id"]': '_onChangeState',
        'change select[name="town_id"]': '_onChangeTown',
        'change select[name="district_id"]': '_onChangeDistrict',
    }, publicWidget.registry.portalDetails.prototype.events),

    _adaptAddressForm: function () {
        const $country = this.$('select[name=country_id]');
        const cid = $country.val() || 0;
        const sid = this.$state.val() || '';

        this.$stateOptions.detach();
        const $displayedState = this.$stateOptions.filter('[data-country_id=' + cid + ']');
        const length = $displayedState.appendTo(this.$state).show().length;
        this.$state.parent().toggle(length >= 1);
        this.$state.val(sid);
    },

    _onCountryChange: function () {
        this._super.apply(this, arguments);
        const length = this.$stateOptions.length;
        $("select[name='town_id']").val('').parent().toggle(length >= 1);
        $("select[name='district_id']").val('').parent().toggle(length >= 1);
        $("select[name='street_id']").val('').parent().toggle(length >= 1);
    },

    _onChangeState: function (ev) {
        ev.stopPropagation();
        if (!$(ev.currentTarget).val()) {
            return;
        }

        this._rpc({
            route: '/my/account/states/' + $(ev.currentTarget).val(),
        }).then(function (data) {
            const inputTowns = $("input[name='city']");
            const selectTowns = $("select[name='town_id']");
            const selectDistricts = $("select[name='district_id']");
            const selectStreets = $("select[name='street_id']");
            if (data.towns.length) {
                selectTowns.html('');
                selectDistricts.html('');
                selectStreets.html('');
                selectTowns.append($('<option>').text(_t('Town...')).attr('value', '').attr('disabled', 'disabled'));
                selectDistricts.append($('<option>').text(_t('District...')).attr('value', '').attr('disabled', 'disabled'));
                selectStreets.append($('<option>').text(_t('Street...')).attr('value', '').attr('disabled', 'disabled'));
                _.each(data.towns, function (x) {
                    const opt = $('<option>').text(x[1]).attr('value', x[0]);
                    selectTowns.append(opt);
                });
                selectTowns.val('').change();
                selectDistricts.val('').change();
                selectStreets.val('').change();
                selectTowns.parent('div').show();
                inputTowns.parent('div').show();
            } else {
                inputTowns.val('').parent('div').hide();
                selectTowns.val('').parent('div').hide();
            }
        });
    },

    _onChangeTown: function (ev) {
        ev.stopPropagation();
        if (!$(ev.currentTarget).val()) {
            return;
        }

        this._rpc({
            route: '/my/account/towns/' + $(ev.currentTarget).val(),
        }).then(function (data) {
            const inputDistricts = $("input[name='street']");
            const selectDistricts = $("select[name='district_id']");
            const selectStreets = $("select[name='street_id']");
            if (data.districts.length) {
                selectDistricts.html('');
                selectStreets.html('');
                selectDistricts.append($('<option>').text(_t('District...')).attr('value', '').attr('disabled', 'disabled'));
                selectStreets.append($('<option>').text(_t('Street...')).attr('value', '').attr('disabled', 'disabled'));
                _.each(data.districts, function (x) {
                    const opt = $('<option>').text(x[1]).attr('value', x[0]);
                    selectDistricts.append(opt);
                });
                selectDistricts.val('').change();
                selectStreets.val('').change();
                selectDistricts.parent('div').show();
                inputDistricts.parent('div').show();
            } else {
                selectDistricts.val('').parent('div').hide();
                inputDistricts.val('').parent('div').hide();
            }
        });
    },

    _onChangeDistrict: function (ev) {
        ev.stopPropagation();
        if (!$(ev.currentTarget).val()) {
            return;
        }

        this._rpc({
            route: '/my/account/districts/' + $(ev.currentTarget).val(),
        }).then(function (data) {
            const selectStreets = $("select[name='street_id']");
            const inputStreets = $("input[name='street2']");
            const inputStreet = $("input[name='street3']");
            const inputZip = $("input[name='zip']");
            if (data.streets.length) {
                selectStreets.html('');
                selectStreets.append($('<option>').text(_t('Street...')).attr('value', '').attr('disabled', 'disabled'));
                _.each(data.streets, function (x) {
                    const opt = $('<option>').text(x[1]).attr('value', x[0])
                        selectStreets.append(opt);
                });
                selectStreets.val('').change();
                selectStreets.parent('div').show();
                inputStreets.parent('div').show();
                inputStreet.parent('div').show();
                inputZip.parent('div').show();
            } else {
                selectStreets.val('').parent('div').hide();
                inputStreets.val('').parent('div').hide();
                inputStreet.val('').parent('div').hide();
                inputZip.val('').parent('div').hide();
            }
        });
    },
});