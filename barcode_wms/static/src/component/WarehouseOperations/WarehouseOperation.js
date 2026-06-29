/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Components } from "@barcode_wms/component/Components/Components";
import { SearchBar } from "@barcode_wms/component/Components/SearchBar";
import {
    SelectDropdownLocationAdd,
    SelectDropdownLocationSrc,
    SelectDropdownLocationDest
} from "@barcode_wms/component/Components/SelectDropdown";
import { _t } from "@web/core/l10n/translation";
import { onWillStart, onWillUnmount, useExternalListener } from "@odoo/owl";


export class WarehouseOperation extends Components {

    setup() {
        super.setup();
        this.buffer = [];
        this.picking = {};
        this.numbers = [];
        this.packages = [];

        useExternalListener(window, "beforeunload", (ev) => {
            ev.preventDefault();
            localStorage.setItem('picking', JSON.stringify(this.props.action.params));
            localStorage.setItem('reload', true);
            if (this.settings.save_before_closing) {
                this.validateTransfer();
            }
        });
        onWillStart(() => this.load());
        onWillUnmount(() => {
            localStorage.removeItem('picking');
            localStorage.removeItem('reload');
        });
    }

    async load(options={}) {
        const picking = localStorage.getItem('picking');
        const reload = localStorage.getItem('reload');

        if (picking !== null && reload === 'true') {
            this.props.action.params = JSON.parse(picking);
        }

        if (this.props.action.params.picking_id) {
            let data = await this.orm.call('barcode.warehouse.operation', 'get_pickings', [this.props.action.params.picking_id], {});

            this.state.groups = data.groups;
            this.state.reports = data.reports;
            this.state.operation = data.operation;
            this.state.location.src = this.locations.src[0];
            this.state.location.dest = this.locations.dest[0];
            this.state.location.type = this.setLocationType(data.operation);
            //this.state.location.src = data.location_id;
            //this.state.location.dest = data.location_dest_id;

            this.picking = data.picking;
            this.settings = data.settings;
            this.packages = data.packages;
            for (const location of data.location_ids) {
                if (!this.locations.src.find((l) => l[0] === location[0])) {
                    this.locations.src.push(location);
                }
            }
            for (const location of data.location_dest_ids) {
                if (!this.locations.dest.find((l) => l[0] === location[0])) {
                    this.locations.dest.push(location);
                }
            }

            let moves = [];
            for (let move of data.moves) {
                move.lines = [];
                move.sequence = this.sequence++;
                if (move.product_id.tracking === 'serial' && this.settings.lot_create_method === 'block') {
                    move.qty = 1;
                }
                moves.push(move);
            }
            this.state.move.all = moves;

            if (options.print === 'pack' && this.packages) {
                const pack = this.packages.sort((a,b) => b[0] - a[0])[0];
                const print = await this.orm.call('barcode.quant.operation', 'print_barcode_line', [pack[1]], {});
                if (print) {
                    this.actionService.doAction(print);
                }
            }
        }
    }

    async listInventory() {
        const viewID = await this.orm.searchRead('ir.model.data', [['module', '=', 'stock'], ['name', '=', 'view_picking_move_tree']], ['res_id'], { limit: 1 });
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: _t('Detail Lines'),
            res_model: 'stock.move',
            context: {
                'default_picking_id': this.picking.id,
                'dialog_size': 'extra-large',
            },
            domain: [
                ['picking_id', '=', this.picking.id],
                ['create_uid', '=', this.env.services.user.userId],
            ],
            views: [[viewID.length && viewID[0]['res_id'], 'list']],
            view_mode: 'list',
            target: 'new',
        });
    }

    async scan(barcode) {
        console.log(barcode)
        let data = await this.orm.call('barcode.warehouse.operation', 'get_barcode_data', [barcode]);
        let { product, number, location, packaging, packing } = data;

        // If there is a product which is not retrieved from a serial/lot number
        if (product && !number) {

            // Find a move with the same product in all locations and not marked as new
            let move = this.getMoves(true).find(m => m.product_id.id === product.id && !m.new);

            // If there is a move
            if (move) {

                // If product tracking is lot or serial, select move and stop
                if (['lot', 'serial'].includes(move.product_id.tracking)) {
                    this.selectMove({ detail: move });
                    return;
                }

                // If product done quantity is fewer than quantity, increase done quantity by one, select move and stop
                if (move.qty_done < move.qty) {
                    move.qty_done++;
                    this.updateMove({
                        detail: {
                            move: move,
                            qty: move.qty_done,
                        }
                    });
                    this.selectMove({ detail: move });
                    return;
                }

                // Find a move with the same product in all locations and marked as new
                move = this.getMoves(true).find(m => m.product_id.id === product.id && m.new);

                // If there is a move and product done quantity is fewer than quantity, increase done quantity by one, select move and stop
                if (move) {
                    move.qty_done++;
                    this.updateMove({
                        detail: {
                            move: move,
                            qty: move.qty_done,
                        }
                    });
                    this.selectMove({ detail: move });
                    return;
                }
            }

            // Else, create move with given product
            this.createMove({
                detail: {
                    product,
                    qty: 1,
                }
            });
            return;
        }

        // If there is a location matched with given barcode, select the location
        if (location) {
            this.selectScannedLocation(location);
            return;
        }

        // If there is a packing information
        if (packing) {

            // Find a move of which product is the same as the packing product
            let move = this.getMoves().find(m => m.product_id.id === packing.pid);

            // If there is such a move
            if (move) {

                // If product tracking is lot or serial and selected move is not the move, select move and stop
                // Else, increase move quantity with packing quantity, select move and stop
                if (['lot', 'serial'].includes(move.product_id.tracking)) {
                    if (this.state.move.id !== move.id) {
                        this.selectMove({ detail: move });
                        return;
                    }
                } else {
                    move.qty_done += packing.qty;
                    this.updateLine({
                        detail: {
                            move: move,
                            qty: move.qty_done,
                        }
                    });
                    this.selectMove({ detail: move });
                    return;
                }
            }
        }

        // If there is a packaging information
        if (packaging) {
            let field = this.getPackageField();
            for (let pack of packaging) {
                // Find a move with the same product in all locations and (!not) marked as new
                let move = this.state.move.all.find(m => m.product_id.id === pack.product.id && m[field][4] === pack.line); // && !m.new);

                // If there is a move
                if (move) {

                    // If product done quantity is fewer than quantity, increase done quantity by package quantity, select move and stop
                    move.qty_done = pack.qty;
                    this.updateMove({
                        detail: {
                            move: move,
                            qty: move.qty_done,
                        }
                    });

                    // If product tracking is lot or serial
                    if (['lot', 'serial'].includes(move.product_id.tracking)) {
                        let moves = this.getMoves(true).find(m => m.product_id.id === move.product_id.id);
                        let line = { ...moves, move: moves }
                        this.selectLine({ detail: line });
                    } else {
                        this.selectMove({ detail: move });
                    }
                } else {
                    // Else, create move with given product
                    this.buffer.push({
                        product: pack.product,
                        qty: 0,
                        qty_done: pack.qty,
                        number: pack.number,
                        [field]: [pack.id, pack.name, pack.number, pack.qty, pack.line],
                    });
                    this.createMove({
                        detail: {
                            product: pack.product,
                            qty: 0,
                            qty_done: pack.qty,
                            number: pack.number,
                            [field]: [pack.id, pack.name, pack.number, pack.qty, pack.line],
                        }
                    });
                }
            }
            return;
        }

        // Search for lines of which lot/serial number is matched with given barcode
        let lines = this.getPage(true).filter(l => l.number === barcode);

        // If such lines
        if (lines.length) {

            // Define a done flag and iterate through the lines
            let done = false;
            for (let line of lines) {
                
                // If current location type is source but line location is different from current source location,
                // Update source location of the line and mark the flag as done
                if (this.state.location.type === 'src' && !(!this.state.location.src[0] || line.location_id[0] === this.state.location.src[0])) {
                    line.location_id = this.state.location.src;
                    this.updateLine({
                        detail: {
                            move: line,
                            location: line.location_id,
                        }
                    });
                    done = true;
                }
                
                // Else, current location type is destination but line location is different from current destination location,
                // Update destination location of the line and mark the flag as done
                else if (this.state.location.type === 'dest' && !(!this.state.location.dest[0] || line.location_dest_id[0] === this.state.location.dest[0])) {
                    line.location_dest_id = this.state.location.dest;
                    this.updateLine({
                        detail: {
                            move: line,
                            location: line.location_dest_id,
                        }
                    });
                    done = true;
                }

                // Else, update quantity
                else {
                    line.qty_done++;
                    this.updateLine({
                        detail: {
                            move: line,
                            qty: line.qty_done,
                        }
                    });
                    done = true;
                }
            }

            // If flag marked as done, stop
            if (done) {
                return;
            }
        }

        // If no such lines
        else {

            // If a serial/lot number exists matched with given barcode, do things and stop
            if (number) {

                // Find a line of which product is the same as the product related to lot/serial number,
                // and its lot/serial number is blank or equals to given barcode
                let line = this.getPage().find(l => l.product_id.id === product.id && (!l.number || l.number === number));

                // If such line, update lot/serial information of that line and increase quantity by one
                if (line) {
                    line.qty_done++;
                    this.updateLine({
                        detail: {
                            move: line,
                            number: barcode,
                            qty: line.qty_done,
                        }
                    });
                }

                // If no such line, create a new line with the product related to that lot/serial number
                else {
                    this.createLine({
                        detail: {
                            product: product,
                            number,
                            qty_done: 1,
                            qty: 0,
                        }
                    });
                }
                return;
            }
        }

        // If there is no information after scanning process, get selected move.
        // If there is no any selected move, stop.
        let move = this.getMove();
        if(!move) {
            return;
        }

        // If product tracking method of selected move is lot
        if (move.product_id.tracking === 'lot') {
            let line;

            // If there is a packing information, get selected line.
            if (packing) {
                line = this.getLine();

                // If such line, update done quantity of that line.
                // Sum current quantity and packing quantity, but aware of initial 1 value.
                if (line) {
                    if (line.qty_done === 1) {
                        line.qty_done += packing.qty - 1;
                    } else {
                        line.qty_done += packing.qty;
                    }
                    this.updateLine({
                        detail: {
                            move: line,
                            qty: line.qty_done,
                        }
                    });
                }
            }

            // Else, get next line of which lot number is equal with given barcode.
            else {
                line = this.nextLine(barcode);

                // If such line, update quantity and lot number information.
                // Else, create a new lot line with given values.
                if (line) {
                    line.qty_done++;
                    this.updateLine({
                        detail: {
                            move: line,
                            number: barcode,
                            qty: line.qty_done,
                        }
                    });
                } else {
                    this.createLine({
                        detail: {
                            product: move.product_id,
                            number: barcode,
                            qty_done: 1,
                            qty: 0,
                        }
                    });
                }
            }
            return;
        }

        // If product tracking method of selected move is serial
        if (move.product_id.tracking === 'serial') {
            let line;

            // Operation type is outgoing, get line with given barcode.
            // Else, select line of which serial number is empty.
            if (!this.state.operation.dest) {
                line = this.nextLine(barcode);
            } else {
                line = this.nextLine();
            }

            // If such line, update quantity and serial number information.
            // Else, create a new serial line with given values.
            if (line) {
                this.updateLine({
                    detail: {
                        move: line,
                        number: barcode,
                        qty: 1,
                    }
                });
            } else {
                this.createLine({
                    detail: {
                        product: move.product_id,
                        number: barcode,
                        qty_done: 1,
                        qty: 0,
                    }
                });
            }
            return;
        }

        // If there is not any case occured above, give an error.
        this.notificationService.add(_t("Barcode cannot be found."), {
            title: "Error",
            type: "danger",
        });
        this.onPlaySound("error");
    }

    selectScannedLocation(location) {
        if (this.state.operation.id) {
            if (this.state.operation.src && this.state.operation.dest) {
                if (this.getMoves().length) {
                    return this.selectDestLocation({ detail: location }, true);
                } else {
                    return this.selectSrcLocation({ detail: location }, true);
                }
            } else if (this.state.operation.src) {
                return this.selectSrcLocation({ detail: location }, true);
            } else if (this.state.operation.dest) {
                let move = this.getMove();
                if(!move) {
                    return this.selectDestLocation({ detail: location }, true);
                }

                if (['lot', 'serial'].includes(move.product_id.tracking)) {
                    let lines = move.lines.filter(l => this.numbers.includes(l.number));
                    for (let line of lines) {
                        this.updateLine({
                            detail: {
                                move: line,
                                location,
                            }
                        });
                        this.numbers = [];
                    }
                } else {
                    this.updateMove({
                        detail: {
                            move,
                            location,
                        }
                    });
                }
            }
        }
    }

    getMoves() {
        let moves = super.getMoves(...arguments);
        for (let i in moves) {
            if (moves[i].qty <= moves[i].qty_done) {
                moves[i].sequence = ++this.sequence;
            }
        }
        return moves.sort((a, b) => a.sequence - b.sequence);
    }

    async onPack() {
        try {
            await this.validateTransfer();
            const result = await this.orm.call('stock.picking', 'action_put_in_pack', [this.picking.id]);
            if (result instanceof Object) {
                await this.actionService.doAction(result, {
                    onClose: () => {
                        this.load({ print: 'pack' });
                    }
                });
                return;
            }
        } catch (e) {
            this.notificationService.add(e.data && e.data.message || e.message, {
                title: "Error",
                type: "danger",
            })
        }
        this.load({ print: 'pack' });
    }

    createMove({ detail: move }, options={}) {
        let products = this.getProducts(true);
        if (!(move.product.id in products)) {
            if (!move.force) {
                if (this.settings.line_create_method === 'warning') {
                    this.onPlaySound("bell");
                    this.openPopup('confirm', {
                        message: _t("Are you sure you want to add a new line?"),
                        method: () => {
                            if (this.buffer.length) {
                                for (const m of this.buffer) {
                                    this.createMove({ detail: { force: true, ...m } }, options);
                                }
                                this.buffer = [];
                            } else {
                                this.createMove({ detail: { force: true, ...move } }, options);
                            }
                        },
                        type: 'warning',
                    });
                    return;
                } else if (this.settings.line_create_method === 'block') {
                    this.onPlaySound("error");
                    this.openPopup('error', {
                        message: _t("You cannot add a new line for this operation."),
                    });
                    return;
                }
            }
        }

        move.new = true;
        return super.createMove({ detail: move }, options);
    }

    async clickReportLine(report_id) {
        let report = await this.orm.call('stock.picking', 'print_barcode_report', [this.picking.id, report_id], {});
        if (report) {
            this.actionService.doAction(report);
        }
    }

    createLine({ detail: line }, options={}) {
        if (!line.force) {
            if (this.settings.lot_create_method === 'warning') {
                this.onPlaySound('bell');
                this.openPopup('confirm', {
                    message: _t('Are you sure you want to add a new serial/lot line?'),
                    method: () => {
                        this.createLine({ detail: { force: true, ...line } }, options);
                    },
                    type: 'warning',
                });
                return;
            } else if (this.settings.lot_create_method === 'block') {
                this.onPlaySound('error');
                this.openPopup('error', {
                    message: _t('You cannot add a new serial/lot line for this operation.'),
                });
                return;
            }
        }

        if (line.number) {
            this.numbers.push(line.number);
        }

        line.new = true;
        return super.createLine({ detail: line }, options);
    }

    //TODO Bottom block will be revised
    updateLineRevise({ detail: line }) {
        if (line.number && !line.move.number && !line.force) {
            if (this.settings.lot_create_method === 'warning') {
                this.onPlaySound('bell');
                this.openPopup('confirm', {
                    message: _t('Are you sure you want to add a new serial/lot line?'),
                    method: () => {
                        this.updateLine({ detail: { force: true, ...line } });
                    },
                    type: 'warning',
                });
                return;
            } else if (this.settings.lot_create_method === 'block') {
                this.onPlaySound('error');
                this.openPopup('error', {
                    message: _t('You cannot add a new serial/lot line for this operation.'),
                });
                return;
            }
        }

        if (line.number) {
            this.numbers.push(line.number);
        }

        return super.updateLine({ detail: line });
    }

    async validateTransfer(validate=false) {
        let lines = this.prepareLines();
        let values = { lines, validate }
        let result = await this.orm.call('stock.picking', 'save_barcode_data', [this.picking.id, values], {});

        if (validate) {
            if (result instanceof Object) {
                await this.actionService.doAction(result, {
                    onClose: () => {
                        this.load();
                        this.closePopup({ detail: 'validate' });
                    }
                });
            } else {
                this.load();
                this.closePopup({ detail: 'validate' });
            }
            return false;
        }
        return true;
    }
}

WarehouseOperation.template = "barcode_wms.WarehouseOperation";
WarehouseOperation.components = {
    ...Components.components,
    SearchBar,
    SelectDropdownLocationAdd,
    SelectDropdownLocationSrc,
    SelectDropdownLocationDest,
};
registry.category("actions").add('warehouse_picking_operations', WarehouseOperation);
