/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";

export class SyncListController extends ListController {
    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    async onSync() {
        this.model.action.doAction('connector_syncops.action_sync', {
            onClose: () => {
                this.model.load();
            },
            additionalContext: {
                active_model: this.props.resModel,
            }
        });
    }

    async onClose() {
         this.actionService.doAction({type: 'ir.actions.act_window_close'});
    }
}
