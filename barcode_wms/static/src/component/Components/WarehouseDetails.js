/** @odoo-module **/

import { CollapsableRow } from './CollapsableRow';
import { Component, useState } from "@odoo/owl";
import { user } from "@web/core/user";
import { formatFloat, formatMonetary } from "@web/views/fields/formatters";

export class WarehouseDetails extends Component {
    setup() {
        super.setup();
        this.formatFloat = formatFloat;
        this.formatMonetary = formatMonetary;
        this.state = useState({
            expanded: false,
            hideEmpty: true,
            showPrice: false,
        });

        user.hasGroup("barcode_wms.group_product_price").then((result) => {
            this.state.showPrice = result;
        });
    }

    selectExpandAll(ev) {
        this.state.expanded = ev.target.checked;
    }

    selectHideEmpty(ev) {
        this.state.hideEmpty = ev.target.checked;
    }

}

WarehouseDetails.components = { CollapsableRow }
WarehouseDetails.template = "barcode_wms.WarehouseDetails"