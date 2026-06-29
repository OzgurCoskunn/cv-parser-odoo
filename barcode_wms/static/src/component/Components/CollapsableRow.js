/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

export class CollapsableRow extends Component {
    setup() {
        super.setup();
        this.state = useState({
            visible: this.props.expanded,
            hideEmpty: this.props.hideEmpty,
        })
    }

    async willUpdateProps(nextProps) {
        this.state.visible = nextProps.expanded;
        this.state.hideEmpty = nextProps.hideEmpty;
    }

    clickExpand() {
        this.state.visible = !this.state.visible;
    }

}

CollapsableRow.template = "barcode_wms.CollapsableRow"