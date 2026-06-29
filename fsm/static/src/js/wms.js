/** @odoo-module **/

import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { BarcodeScreen } from "@barcode_wms/component/BarcodeScreen/BarcodeScreen";

patch(BarcodeScreen.prototype, {

    startProductDetails() {
        user.hasGroup('fsm.group_administrator').then(async (hasGroup) => {
            if (!hasGroup) {
                let action = await this.orm.call("stock.quant", "get_user_action", [], {});
                if (action) {
                    this.actionService.doAction(action);
                }
            } else {
                super.startProductDetails();
            }
        });
    }

});
