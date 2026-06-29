/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

export class BackorderDialog extends Component {
    static components = { Dialog };
    static template = "barcode_wms.BackorderDialog";
    static props = {
        displayUoM: { type: Boolean, optional: true },
        uncompletedLines: Array,
        onApply: Function,
        close: Function,
    };

    async _onApply() {
        await this.props.onApply();
        this.props.close();
    }
}
