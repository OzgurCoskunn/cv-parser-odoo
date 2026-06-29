/** @odoo-module **/
import { registry } from "@web/core/registry";
import ListController from 'web.ListController';
import ListView from 'web.ListView';
import viewRegistry from 'web.view_registry';
import core from 'web.core';

const qweb = core.qweb;

const actionHandlersRegistry = registry.category('action_handlers');
actionHandlersRegistry.add('stock.barcode.inventory.line.reload', ({ options }) => {
    options.onClose();
});

const InventoryLineController = ListController.extend({
    events: _.extend({}, ListController.prototype.events, {
        'click .o_button_close': '_onClose',
    }),

    renderButtons: function ($node) {
        if ($node && $node[0] && $node[0]['nodeName'] === 'FOOTER') {
            const $buttons = $(qweb.render('barcode_wms.inventory_line_footer_buttons', {widget: this}));
            $buttons.on('click', '.o_button_close', this._onClose.bind(this));
            $buttons.appendTo($node);
            return;
        }
        return this._super.apply(this, arguments);
    },

    _onClose: function () {
        this.do_action({'type': 'ir.actions.act_window_close'});
    },
});

const InventoryLineView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: InventoryLineController,
    }),
});

viewRegistry.add('inventory_line', InventoryLineView);