/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Components } from "@barcode_wms/component/Components/Components";
import { SearchBar } from "@barcode_wms/component/Components/SearchBar";
import { SelectDropdownSort, SelectDropdownLocation } from "@barcode_wms/component/Components/SelectDropdown";
import { _t } from "@web/core/l10n/translation";
import { onWillStart, onWillUnmount, useExternalListener, useState } from "@odoo/owl";

export class InventoryAdjustments extends Components {

    setup() {
        super.setup();
        this.state = useState({
            ...this.state,
            inventory: 0,
        });
        this.warehouses = [];
        this.inventories = [];
        useExternalListener(window, "beforeunload", (ev) => {
            ev.preventDefault();
            this.openPopup('confirm', {
                message: _t("Do you want to exit without saving?"),
                method: () => this.onBack(),
            });
            return ev.returnValue = _t("Are you sure you want to exit?");
        });
        onWillStart(() => this.load());
    }

    async load() {
        let data = await this.orm.call('barcode.quant.operation', 'get_data', [], {});
        this.warehouses = data.warehouses;
        this.locations.src = data.locations;
        this.locations.dest = data.locations;
        this.state.groups = data.groups;
    }

    async scan(text) {
        let [barcode, quantity] = text.split(" ");
        if (!quantity) {
            quantity = 1;
        } else {
            quantity = parseInt(quantity);
        }

        let data = await this.orm.call('barcode.inventory.operation', 'get_barcode_data', [barcode], {
            context:{
                location: this.state.location.src[0],
            }
        });
        let { product, number, location, packaging } = data;

        if (number) {
            let line = this.getPage().find(l => l.product_id.id === product.id && (!l.number || l.number === number));
            if (line) {
                this.updateLine({
                    detail: {
                        move: line,
                        number: barcode,
                        qty: ++line.qty_done,
                    }
                });
            } else {
                this.createLine({
                    detail: {
                        product,
                        number,
                        qty: 0,
                        qty_done: 1,
                    }
                });
            }
            return;
        } else if (product) {
            let move = this.getMoves().find(m => m.product_id.id === product.id);
            if (move) {
                this.updateMove({
                    detail: {
                        move,
                        qty: ++move.qty_done,
                    }
                });
            } else {
                this.createMove({
                    detail: {
                        product,
                        qty: 0,
                        qty_done: 1,
                    }
                });
            }
        } else if (location) {
            await this.selectLocation({ detail: location });
        } else if (packaging) {
            let move = this.getPage().find(m => m.product_id.id === packaging.pid);
            if (move) {
                if (this.state.move.id !== move.id) {
                    this.selectMove({ detail: move });
                }

                let line = this.getLine();
                if (line) {
                    if (line.qty_done === 1) {
                        line.qty_done += packaging.qty - 1;
                    } else {
                        line.qty_done += packaging.qty;
                    }
                    this.updateLine({
                        detail: {
                            move: line,
                            qty: line.qty_done,
                        }
                    });
                } else {
                    if (move.qty_done === 1) {
                        move.qty_done += packaging.qty - 1;
                    } else {
                        move.qty_done += packaging.qty;
                    }
                    this.updateMove({
                        detail: {
                            move: move,
                            qty: move.qty_done,
                        }
                    });
                }
            }
        } else {
            this.notificationService.add(_t("Barcode cannot be found."), {
                title: "Error",
                type: "danger",
            });
            this.onPlaySound("error");
        }
    }

    async createInventory() {
        if (!this.state.location.src.length) {
            this.state.popup.error = {
                message: _t('Please select a source location'),
            }
            return;
        }
        this.state.inventory = await this.orm.create('stock.barcode.inventory', [{
            location_id: this.state.location.src[0],
        }]);
    }

    async openInventory(id) {
        this.state.inventory = id;
    }

    async listInventory() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: _t('Inventory Lines'),
            res_model: 'stock.barcode.inventory.line',
            context: {
                'default_inventory_id': this.state.inventory,
                'dialog_size': 'extra-large',
            },
            domain: [
                ['inventory_id', '=', this.state.inventory],
                ['create_uid', '=', this.env.services.user.userId],
            ],
            views: [[false, 'list']],
            view_mode: 'list',
            target: 'new',
        });
    }

    async selectLocation({ detail: location }) {
        if (location) {
            this.inventories = await this.orm.searchRead('stock.barcode.inventory',
                [['done', '=', false], ['location_id', '=', location[0]]],
                ['id', 'create_date', 'create_uid'],
                { limit: 100 }
            );
        } else {
            this.inventories = [];
        }
        this.state.location.src = location;
        this.state.location.dest = location;
    }
    
    updateLine({ detail: line }) {
        if (line.move.product_id.tracking === 'serial' && line.qty > 1 ) {
            line.qty = 1;
        }
        return super.updateLine({ detail: line });
    }

    async validateTransfer(validate=false) {
        let values = [];
        let lines = this.prepareLines().filter(move => move.checked);
        for (let line of lines) {
            values.push({
                'inventory_id': this.state.inventory,
                'product_id': line.product_id.id,
                'quantity': line.qty_done,
            });
        }

        if (values.length) {
            this.state.inventory = await this.orm.call('stock.barcode.inventory.line', 'append', [values]);
        }

        if (validate) {
            await this.orm.call('stock.barcode.inventory', 'validate', [this.state.inventory]);
            this.state.inventory = 0;
            this.inventories = [];
        }
        return true;
    }

    onBack() {
        if (this.state.inventory) {
            this.selectLocation({ detail: this.state.location.src });
            this.state.inventory = 0;
            this.closePopup();
        } else {
            super.onBack();
        }
    }

    async getInventoryLocation(product_id, location_id, package_id) {
        return await this.orm.call('barcode.quant.operation', 'get_location_data', [product_id, location_id, package_id]);
    }

    async getPackageData(package_id, location_id) {
        return await this.orm.call('barcode.quant.operation', 'get_package_data', [package_id, location_id]);
    }
}

InventoryAdjustments.template = "barcode_wms.InventoryAdjustments"
InventoryAdjustments.components = {
    ...Components.components,
    SearchBar,
    SelectDropdownSort,
    SelectDropdownLocation,
};
registry.category("actions").add('barcode_inventory_adjustments', InventoryAdjustments);