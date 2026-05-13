/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { StockBarcodeKanbanController } from "./barcode_wms_kanban_controller";
import { StockBarcodeKanbanRenderer } from "./barcode_wms_kanban_renderer";

export const stockBarcodeKanbanView = {
    ...kanbanView,
    Controller: StockBarcodeKanbanController,
    Renderer: StockBarcodeKanbanRenderer,
};

registry.category("views").add("barcode_wms_list_kanban", stockBarcodeKanbanView);
