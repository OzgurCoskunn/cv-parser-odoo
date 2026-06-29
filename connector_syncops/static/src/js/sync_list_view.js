/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { SyncListController } from "./sync_list_controller";

export const syncListView = {
    ...listView,
    Controller: SyncListController,
    buttonTemplate: "connector_syncops.SyncListButtons",
};

registry.category("views").add("syncops_sync", syncListView);
