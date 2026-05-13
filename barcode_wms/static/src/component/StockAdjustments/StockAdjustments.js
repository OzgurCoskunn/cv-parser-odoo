/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Components } from "@barcode_wms/component/Components/Components";
import { SearchBar } from "@barcode_wms/component/Components/SearchBar";
import { SelectDropdownSort, SelectDropdownLocation } from "@barcode_wms/component/Components/SelectDropdown";
import { _t } from "@web/core/l10n/translation";
import { onWillStart, onWillUnmount, useExternalListener } from "@odoo/owl";

export class StockAdjustments extends Components {

    setup() {
        super.setup();
        this.warehouses = [];
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

        for (let line of data.lines) {
            this.state.location.src = line.location_id;
            this.state.location.dest = line.location_id;
            this.createMove({
                detail: {
                    product: line.product_id,
                    number: line.number,
                    qty_done: line.qty_done,
                    qty: line.product_id.qty_available,
                }
            });
        }

        if (this.state.location.src) {
            this.selectLocation({ detail: this.state.location.src });
        } else if (this.state.location.dest) {
            this.selectLocation({ detail: this.state.location.dest });
        }
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
            let line = this.getLine();
            let move = this.getMove();
            if (line && ['lot', 'serial'].includes(line.move.product_id.tracking)) {
                move = line.move;
                if (!line.number) {
                    this.updateLine({
                        detail: {
                            move: line,
                            number: text,
                        }
                    });
                } else {
                    line = this.getPage().find(l => l.product_id.id === move.product_id.id && l.number === text);
                    if (line) {
                        this.updateLine({
                            detail: {
                                move: line,
                                qty: ++line.qty_done,
                            }
                        });
                    } else {
                        this.createLine({
                            detail: {
                                product: move.product_id,
                                number: text,
                                qty: 0,
                                qty_done: 1,
                            }
                        });
                    }
                }
            } else if (move && ['lot', 'serial'].includes(move.product_id.tracking)) {
                line = this.getPage().find(l => l.product_id.id === move.product_id.id && !l.number);
                if (line) {
                    this.updateLine({
                        detail: {
                            move: line,
                            number: text,
                        }
                    });
                } else {
                    line = this.getPage().find(l => l.product_id.id === move.product_id.id && l.number === text);
                    if (line) {
                        this.updateLine({
                            detail: {
                                move: line,
                                qty: ++line.qty_done,
                            }
                        });
                    } else {
                        this.createLine({
                            detail: {
                                product: move.product_id,
                                number: text,
                                qty: 0,
                                qty_done: 1,
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

            // Bottom attitude has been altered, but code has been kept for further development
            /*if (line && ['lot', 'serial'].includes(line.move.product_id.tracking)) {
                this.updateLine({
                    detail: {
                        move: line,
                        number: text,
                    }
                });
            } else if (move && ['lot', 'serial'].includes(move.product_id.tracking)) {
                line = this.getPage().find(l => l.product_id.id === move.product_id.id && !l.number);
                if (line) {
                    this.updateLine({
                        detail: {
                            move: line,
                            number: text,
                        }
                    });
                } else {
                    this.createLine({
                        detail: {
                            product: move.product_id,
                            number: text,
                            qty: 0,
                            qty_done: 1,
                        }
                    });
                }
            } else {
                this.notificationService.add(_t("Barcode cannot be found."), {
                    title: "Error",
                    type: "danger",
                });
                this.onPlaySound("error");
            }*/
        }
    }

    createMove({ detail: move }) {
        if (!this.state.location.src.length) {
            this.state.popup.error = {
                message: _t('Please select a source location'),
            }
            return;
        }
        if (!('qty_done' in move)) {
            move.qty_done = move.qty ?? 1;
        }
        move.qty = move.product.qty_available;
        if (!('qty' in move)) {
            if (['lot', 'serial'].includes(move.product_id.tracking)) {
                move.qty = 0;
            } else {
                move.qty = move.product.qty_available;
            }
        }
        return super.createMove({ detail: move });
    }
    
    updateLine({ detail: line }) {
        if (line.move.product_id.tracking === 'serial' && line.qty > 1 ) {
            line.qty = 1;
        }
        return super.updateLine({ detail: line });
    }

    async applyValidateTransfer() {
        let result = await super.applyValidateTransfer();
        if (result && this.state.groups.group_stock_manager) {
            await this.applyInventory(result);
        }
    }

    async applyInventory(ids) {
        return await this.orm.call('stock.quant', 'action_apply_inventory', [ids], {});
    }

    async saveBarcodeData(lines) {
        return await this.orm.call('stock.quant', 'save_barcode_data', [lines], {});
    }

    async validateTransfer() {
        let lines = this.prepareLines();
        return await this.saveBarcodeData(lines);
    }
}

StockAdjustments.components = {
    ...Components.components,
    SearchBar,
    SelectDropdownSort,
    SelectDropdownLocation,
};
StockAdjustments.template = "barcode_wms.StockAdjustments"
registry.category("actions").add('barcode_stock_adjustments', StockAdjustments);