/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class BarcodeWmsUnlinkButton extends Component {
    static template = "barcode_wms.UnlinkButton";
    static props = {
        ...standardWidgetProps
    };

    setup() {
        this.orm = useService("orm");
    }

    async onClick() {
        const { resModel, resId, context } = this.props.record;
        await this.orm.unlink(resModel, [resId], { context });
        // Trigger refresh - you may need to adapt this based on your refresh mechanism
        this.env.model.root.load();
    }
}

registry.category("view_widgets").add("barcode_wms_unlink_button", {
    component: BarcodeWmsUnlinkButton,
});
