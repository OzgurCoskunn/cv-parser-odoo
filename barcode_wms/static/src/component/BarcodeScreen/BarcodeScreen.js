/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { NotificationSound } from "@barcode_wms/component/Components/NotificationSound";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";

export class BarcodeScreen extends Component {

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notificationService = useService("notification");
        this.state = useState({
            sound: { src: null },
        });

        this.mutex = new Mutex();
        this.barcodeService = useService("barcode");
        onMounted(() => {
            this.barcodeService.bus.addEventListener('barcode_scanned', this.onScan.bind(this));
        });
        onWillUnmount(() => {
            this.barcodeService.bus.removeEventListener('barcode_scanned', this.onScan.bind(this));
        });
    }

    onScan(payload) {
        // Odoo 19 barcode service emits { barcode, target } in detail or directly
        const barcode = payload.detail?.barcode ?? payload.barcode ?? payload;
        this.mutex.exec(async () => {
            await this.scan(barcode);
        });
    }

    async scan(barcode) {
        let data = await this.orm.call("barcode.operation", "get_barcode_data", [barcode], {});
        let { product, picking, location, operation } = data;

        if (product) {
            this.actionService.doAction({
                name: 'Product Information',
                type: 'ir.actions.client',
                target: 'fullscreen',
                tag: 'barcode_product',
                params: {
                    barcode: product,
                },
            });
        } else if (operation) {
            this.actionService.doAction({
                name: 'Create Transfer',
                type: 'ir.actions.client',
                target: 'fullscreen',
                tag: 'barcode_transfer',
                params: {
                    picking_type_id: operation.id,
                    selected_location: false,
                }
            });
        } else if (picking) {
            this.actionService.doAction({
                name: 'Warehouse Picking Operations',
                type: 'ir.actions.client',
                target: 'fullscreen',
                tag: 'warehouse_picking_operations',
                params: {
                    picking_id: picking.id,
                }
            });
        } else if (location) {
            this.actionService.doAction({
                name: 'Create Transfer',
                type: 'ir.actions.client',
                target: 'fullscreen',
                tag: 'barcode_transfer',
                params: {
                    picking_type_id: location.type,
                    selected_location: location.value,
                },
            });
        } else {
            this.notificationService.add("Error,Barcode not found", {
                title: "Error",
                type: "danger",
            });
            this.onPlaySound('error');
        }
    }

    startCreateTransfer() {
        this.actionService.doAction({
            name: 'Create Transfer',
            type: 'ir.actions.client',
            target: 'fullscreen',
            tag: 'barcode_transfer',
            params: {
                picking_type_id: false,
                selected_location: false,
            }
        });
    }

    startProductDetails() {
        this.actionService.doAction({
            name: 'Product Information',
            type: 'ir.actions.client',
            target: 'fullscreen',
            tag: 'barcode_product',
            params: {
                barcode: false,
            }
        });
    }

    startWarehouseOperation() {
        this.actionService.doAction({
            name: 'Warehouse Operations',
            type: 'ir.actions.client',
            target: 'fullscreen',
            tag: 'barcode_warehouse_operation',
        });
    }

    stockAdjustment() {
        this.actionService.doAction({
            name: 'Stock Adjustments',
            type: 'ir.actions.client',
            target: 'fullscreen',
            tag: 'barcode_stock_adjustments',
        });
    }

    inventoryAdjustment() {
        this.actionService.doAction({
            name: 'Inventory Adjustments',
            type: 'ir.actions.client',
            target: 'fullscreen',
            tag: 'barcode_inventory_adjustments',
        });
    }

    onPlaySound(name) {
        if (name === 'error') {
            this.state.sound.src = "/barcode_wms/static/src/sounds/error.wav";
        } else if (name === 'bell') {
            this.state.sound.src = "/barcode_wms/static/src/sounds/bell.wav";
        }
    }
}

BarcodeScreen.components = { NotificationSound };
BarcodeScreen.template = "barcode_wms.BarcodeScreen"
registry.category("actions").add('barcode_screen', BarcodeScreen);