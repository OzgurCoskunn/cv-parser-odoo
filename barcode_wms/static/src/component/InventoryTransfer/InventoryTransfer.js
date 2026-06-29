/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { Components } from "@barcode_wms/component/Components/Components";
import {
    SelectDropdownSort,
    SelectDropdownOperation,
    SelectDropdownLocationAdd,
    SelectDropdownLocationSrc,
    SelectDropdownLocationDest,
} from "@barcode_wms/component/Components/SelectDropdown";
import { onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";


export class InventoryTransfer extends Components {

    setup() {
        super.setup();
        this.picking = {};
        this.operation = [];
        this.operations = [];
        useBus(this.env.bus, 'change-operation-type', this.changeOperationType);
        onWillStart(() => this.load());
    }

    async load() {
        let type = this.props.action.params.picking_type_id;
        let data = await this.orm.call('barcode.transfer.operation', 'get_data', [type]);

        this.picking = data.picking;
        this.operations = data.operations;

        if (type) {
            await this.selectOperationType({ detail: this.operations[0] });
            let location = this.props.action.params.selected_location;
            if (location) {
                await this.selectScannedLocation(location);
            }
        } else if (this.picking.id) {
            let operation = this.operations.find(o => o.id === this.picking.type)
            if (operation) {
                await this.changeOperationType(operation);
            }

            let moves = [];
            let sequence = 1;
            for (let move of this.picking.moves) {
                move.lines = [];
                if (move.id >= sequence) {
                    sequence = move.id + 1;
                }
                moves.push(move);
            }
            this.state.move.all = moves;
            this.sequence = sequence;

            this.state.location.src.push(true);
            //this.state.location.dest.push(true);
        }
    }

    async scan(barcode) {
        let data = await this.orm.call('barcode.transfer.operation', 'get_barcode_data', [barcode]);
        let { product, number, location, packaging, operation } = data;

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
                move.qty_done++;
                this.env.bus.trigger('update-move', {
                    move: move,
                    qty: move.qty_done,
                });
            } else {
                this.createMove({
                    detail: {
                        product,
                        number,
                        qty: 0,
                        qty_done: 1,
                    }
                });
            }
        } else if (packaging) {
            let field = this.getPackageField();
            for (let pack of packaging) {
                let move = this.state.move.all.find(m => m.product_id.id === pack.product.id && m[field][0] === pack.id);
                if (move) {
                    move.qty_done = pack.qty;
                    this.updateMove({
                        detail: {
                            move: move,
                            qty: move.qty_done,
                        }
                    });

                    if (['lot', 'serial'].includes(move.product_id.tracking)) {
                        let moves = this.getMoves(true).find(m => m.product_id.id === move.product_id.id);
                        let line = { ...moves, move: moves }
                        this.selectLine({ detail: line });
                    } else {
                        this.selectMove({ detail: move });
                    }
                } else {
                    this.createMove({
                        detail: {
                            product: pack.product,
                            qty: 0,
                            qty_done: pack.qty,
                            number: pack.number,
                            [field]: [pack.id, pack.name, pack.number, pack.qty],
                        }
                    });
                }
            }
        } else if (location) {
            this.selectScannedLocation(location);
        } else if (operation) {
            await this.selectOperationType({ detail: operation });
        } else {
            this.notificationService.add(_t("Barcode cannot be found."), {
                title: "Error",
                type: "danger",
            });
            this.onPlaySound('error');
        }
    }

    async changeOperationType({ detail: operation }) {
        if (this.state.operation.id) {
            this.openPopup('changeOperation');
        } else {
            await this.selectOperationType({ detail: operation });
        }
        this.operation = operation;
    }

    applyOperationType() {
        this.selectOperationType({ detail: this.operation });
        this.closePopup({ detail: 'changeOperation' });
    }

    async selectOperationType({ detail: operation }) {
        if (operation) {
            let data = await this.orm.call('barcode.transfer.operation', 'get_operation_data', [operation.id]);
            if (!data) {
                this.notificationService.add(_t("An error occured. Please try again."), {
                    title: "Error",
                    type: "danger",
                });
                return;
            }

            operation.src = operation.default_location_src_id;
            operation.dest = operation.default_location_dest_id;

            this.state.move.all = [];
            this.state.operation = operation;
            this.state.groups = data.groups;
            this.state.location.src = data.location_id;
            this.state.location.dest = data.location_dest_id;
            this.state.location.type = this.setLocationType(operation);

            this.settings = data.settings;
            this.locations.src = data.location_ids;
            this.locations.dest = data.location_dest_ids;
        } else {
            this.notificationService.add(_t("Please scan or select operation type."), {
                title: "Error",
                type: "danger",
            });
        }
    }

    selectSrcLocation({ detail: location }, scanned=false) {
        if (location.length) {
            location.push(scanned);
        }

        if (this.state.operation.dest) {
            this.state.location.src = location;
            this.selectMove();

            let move = this.getMove();
            if (move) {
                if (['lot', 'serial'].includes(move.product_id.tracking)) {
                    this.selectLine();
                    let line = this.getLine();
                    this.updateLine({
                        detail: {
                            move: line,
                            location: { src: location },
                        }
                    });
                } else {
                    this.selectMove();
                    this.updateMove({
                        detail: {
                            move: move,
                            location: { src: location },
                        }
                    });
                }
            }
        } else {
            return super.selectSrcLocation({ detail: location }, scanned);
        }
    }

    selectDestLocation({ detail: location }, scanned=false) {
        if (location.length) {
            location.push(scanned);
        }

        if (this.state.operation.src) {
            this.state.location.dest = location;
            this.selectMove();

            let move = this.getMove();
            if (move) {
                if (['lot', 'serial'].includes(move.product_id.tracking)) {
                    this.selectLine();
                    let line = this.getLine();
                    this.updateLine({
                        detail: {
                            move: line,
                            location: { dest: location },
                        }
                    });
                } else {
                    this.selectMove();
                    this.updateMove({
                        detail: {
                            move: move,
                            location: { dest: location },
                        }
                    });
                }
            }
        } else {
            return super.selectDestLocation({ detail: location }, scanned);
        }
    }

    getPages() {
        return {
            current: 0,
            total: 0,
            pages: [],
        };
    }

    createMove() {
        let move = super.createMove(...arguments);
        move.qty = 0;
        return move;
    }

    updateLine({ detail: line }) {
        if (line.move.product_id.tracking === 'serial' && line.qty > 1 ) {
            line.qty = 1;
        }
        return super.updateLine({ detail: line });
    }

    async validateTransfer(validate=false) {
        let lines = this.prepareLines();
        let type = this.state.operation.id;
        let src = this.state.location.src[0];
        let dest = this.state.location.dest[0];

        let values = { src, dest, type, lines, validate }
        let result = await this.orm.call('stock.picking', 'save_barcode_data', [this.picking.id, values], {});

        if (validate) {
            if (result instanceof Object) {
                await this.actionService.doAction(result, {
                    onClose: () => {
                        this.load();
                        this.closePopup({ detail: 'validate' });
                    }
                });
                return false;
            }
        }
        return true;
    }
}

InventoryTransfer.components = {
    ...Components.components,
    SelectDropdownSort,
    SelectDropdownOperation,
    SelectDropdownLocationAdd,
    SelectDropdownLocationSrc,
    SelectDropdownLocationDest,
};

InventoryTransfer.template = "barcode_wms.InventoryTransfer";
registry.category("actions").add('barcode_transfer', InventoryTransfer);