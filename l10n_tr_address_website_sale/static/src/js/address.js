/** @odoo-module **/

import { WebsiteSale } from 'website_sale.website_sale';
import { _t } from 'web.core';

WebsiteSale.include({
    events: _.extend({
        'change select[name="state_id"]': '_onChangeState',
        'change select[name="town_id"]': '_onChangeTown',
        'change select[name="district_id"]': '_onChangeDistrict',
        'change input[name="company_type"]': '_changeCompanyType',
    }, WebsiteSale.prototype.events),
    jsLibs: [...(WebsiteSale.prototype.jsLibs || []), '/l10n_tr_address_website_sale/static/src/lib/imask.js'],

    init: function () {
        this._super.apply(this, arguments);
        this._changeState = _.debounce(this._changeState.bind(this), 500);
        this._changeTown = _.debounce(this._changeTown.bind(this), 500);
        this._changeDistrict = _.debounce(this._changeDistrict.bind(this), 500);
    },

    start: function () {
        return this._super.apply(this, arguments).then(() => {
            const $phone = $('input[name="phone"]');
            if ($phone.length) {
                $phone.val($phone.val().replace(/\D/g, ''));
                IMask($phone[0], {
                    mask: '{+9\\0} (000) 000 00 00',
                    lazy: false,
                })
            }
        });
    },

    _formatPhone: function (phone) {
        if (!phone) {
            return phone;
        }

        let code = '+90 ';
        let number = code;
        let match = phone.match(/(5\d{0,2})(\d{0,3})(\d{0,4})/);
        if (match) {
            if (match[1]) {
                number += `(${match[1]})`;
                if (match[2]) {
                    number += ` ${match[2]}`;
                    if (match[3]) {
                        number += ` ${match[3]}`;
                    }
                }
            }
        }
        return number;
    },

    _onBeforeInputPhone: function (ev) {
        const $phone = $(ev.currentTarget);
        $phone.val($phone.val().replace(/\D/g, ''));
    },

    _onInputPhone: function (ev) {
        const $phone = $(ev.currentTarget);
        $phone.val(this._formatPhone($phone.val()));
    },

    _onChangeState: function () {
        if (!this.$('.checkout_autoformat').length) {
            return;
        }
        this._changeState();
    },

    _onChangeTown: function () {
        if (!this.$('.checkout_autoformat').length) {
            return;
        }
        this._changeTown();
    },

    _onChangeDistrict: function () {
        if (!this.$('.checkout_autoformat').length) {
            return;
        }
        this._changeDistrict();
    },

    _changeCountry: function () {
        if (!$("#country_id").val()) {
            return;
        }
        this._rpc({
            route: "/shop/country_infos/" + $("#country_id").val(),
            params: {
                mode: $("#country_id").attr('mode'),
            },
        }).then(function (data) {
            $("input[name='phone']").attr('placeholder', data.phone_code !== 0 ? '+'+ data.phone_code : '');
            const selectStates = $("select[name='state_id']");
            const selectTowns = $("select[name='town_id']");
            const selectDistricts = $("select[name='district_id']");
            const selectStreets = $("select[name='street_id']");
            if (selectStates.data('init')===0 || selectStates.find('option').length===1) {
                if (data.states.length || data.state_required) {
                    selectStates.html('');
                    selectTowns.html('');
                    selectDistricts.html('');
                    selectStreets.html('');
                    selectStates.append($('<option>').text(_t('State / Province...')).attr('value', '').attr('disabled', 'disabled'));
                    selectTowns.append($('<option>').text(_t('Town...')).attr('value', '').attr('disabled', 'disabled'));
                    selectDistricts.append($('<option>').text(_t('District...')).attr('value', '').attr('disabled', 'disabled'));
                    selectStreets.append($('<option>').text(_t('Street...')).attr('value', '').attr('disabled', 'disabled'));
                    _.each(data.states, function (x) {
                        const opt = $('<option>').text(x[1]).attr('value', x[0]).attr('data-code', x[2]);
                        selectStates.append(opt);
                    });
                    selectStates.val('').change();
                    selectTowns.val('').change();
                    selectDistricts.val('').change();
                    selectStreets.val('').change();
                    selectStates.parent('div').show();
                } else {
                    selectStates.val('').parent('div').hide();
                }
                selectStates.data('init', 0);
            } else {
                selectStates.data('init', 0);
            }

            if (data.fields) {
                if ($.inArray('zip', data.fields) > $.inArray('city', data.fields)){
                    $(".div_zip").before($(".div_city"));
                } else {
                    $(".div_zip").after($(".div_city"));
                }
                var all_fields = ["street", "zip", "city", "country_name"]; // "state_code"];
                _.each(all_fields, function (field) {
                    $(".checkout_autoformat .div_" + field.split('_')[0]).toggle($.inArray(field, data.fields)>=0);
                });
            }

            if ($("label[for='zip']").length) {
                $("label[for='zip']").toggleClass('label-optional', !data.zip_required);
                $("label[for='zip']").get(0).toggleAttribute('required', !!data.zip_required);
            }
            if ($("label[for='zip']").length) {
                $("label[for='state_id']").toggleClass('label-optional', !data.state_required);
                $("label[for='state_id']").get(0).toggleAttribute('required', !!data.state_required);
            }
        });
    },

    _changeState: function () {
        if (!$('select[name="state_id"]').val()) {
            return;
        }
        this._rpc({
            route: "/shop/state_infos/" + $('select[name="state_id"]').val(),
            params: {},
        }).then(function (data) {
            const inputTowns = $("input[name='city']");
            const selectTowns = $("select[name='town_id']");
            const selectTaxOffices = $("select[name='tax_office_id']");
            const selectDistricts = $("select[name='district_id']");
            const selectStreets = $("select[name='street_id']");
            if (selectTowns.data('init')===1 || selectTowns.data('init')===0 || selectTowns.find('option').length===1) {
                if (data.towns.length) {
                    selectTowns.html('');
                    selectDistricts.html('');
                    selectStreets.html('');
                    selectTaxOffices.html('');
                    selectTowns.append($('<option>').text(_t('Town...')).attr('value', '').attr('disabled', 'disabled'));
                    selectTaxOffices.append($('<option>').text(_t('Tax Office...')).attr('value', '').attr('disabled', 'disabled'));
                    selectDistricts.append($('<option>').text(_t('District...')).attr('value', '').attr('disabled', 'disabled'));
                    selectStreets.append($('<option>').text(_t('Street...')).attr('value', '').attr('disabled', 'disabled'));
                    _.each(data.towns, function (x) {
                        const opt = $('<option>').text(x[1]).attr('value', x[0]);
                        selectTowns.append(opt);
                    });
                    _.each(data.tax_offices, function (x) {
                        const opt = $('<option>').text(x[1]).attr('value', x[0]);
                        selectTaxOffices.append(opt);
                    });
                    selectTowns.val('').change();
                    selectTaxOffices.val('').change();
                    selectDistricts.val('').change();
                    selectStreets.val('').change();
                    selectTowns.parent('div').show();
                    inputTowns.parent('div').show();

                    if ($('input[name=company_type]:checked').val() === 'company') {
                        selectTaxOffices.parent('div').show();
                    }
                } else {
                    inputTowns.val('').parent('div').hide();
                    selectTowns.val('').parent('div').hide();
                    selectTaxOffices.val('').parent('div').hide();
                }
                inputTowns.data('init', 0);
                selectTowns.data('init', 0);
                selectTaxOffices.data('init', 0);
            } else {
                inputTowns.data('init', 0);
                selectTowns.data('init', 0);
                selectTaxOffices.data('init', 0);
            }
        });
    },

    _changeTown: function (ev) {
        if (!$('select[name="town_id"]').val()) {
            return;
        }
        this._rpc({
            route: "/shop/town_infos/" + $('select[name="town_id"]').val(),
            params: {},
        }).then(function (data) {
            const inputDistricts = $("input[name='street']");
            const selectDistricts = $("select[name='district_id']");
            const selectStreets = $("select[name='street_id']");
            if (selectDistricts.data('init')===1 || selectDistricts.data('init')===0 || selectDistricts.find('option').length===1) {
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
                selectDistricts.data('init', 0);
                inputDistricts.data('init', 0);
            } else {
                selectDistricts.data('init', 0);
                inputDistricts.data('init', 0);
            }
        });
    },

    _changeDistrict: function (ev) {
        if (!$('select[name="district_id"]').val()) {
            return;
        }
        this._rpc({
            route: "/shop/district_infos/" + $('select[name="district_id"]').val(),
            params: {},
        }).then(function (data) {
            const selectStreets = $("select[name='street_id']");
            const inputStreets = $("input[name='street2']");
            const inputStreet = $("input[name='street3']");
            const inputZip = $("input[name='zip']");
            if (selectStreets.data('init')===1 || selectStreets.data('init')===0 || selectStreets.find('option').length===1) {
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
                selectStreets.data('init', 0);
                inputStreets.data('init', 0);
            } else {
                selectStreets.data('init', 0);
                inputStreets.data('init', 0);
            }
        });
    },

    _changeCompanyType: function (ev) {
        if (ev.target.value === 'company') {
            this.$('label[for="company_name"]').parent().show('show');
            this.$('label[for="tax_office_id"]').parent().show('show');
            this.$('label[for="vat"]').text(_t('Tax Number')).parent().removeClass('col-md-6').addClass('col-md-3');
        }else{
            this.$('label[for="company_name"]').parent().hide(300);
            this.$('label[for="tax_office_id"]').parent().hide(300);
            this.$('label[for="vat"]').text(_t('VAT Number')).parent().removeClass('col-md-3').addClass('col-md-6');
        }
    },
});
