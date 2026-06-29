/** @odoo-module **/

import { Mutex } from "@web/core/utils/concurrency";
import { useService, useBus } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { AddMove } from "@barcode_wms/component/Components/AddMove";
import { EditMove } from "@barcode_wms/component/Components/EditMove";
import { EditLine } from "@barcode_wms/component/Components/EditLine";
import { StockMove } from "@barcode_wms/component/Components/StockMove";
import { Pagination } from "@barcode_wms/component/Components/Pagination";
import { NotificationSound } from "@barcode_wms/component/Components/NotificationSound";
import { Component, useEffect, useState, onMounted, onWillUnmount } from "@odoo/owl";

export class Components extends Component {

    setup() {
        super.setup();
        this.orm = useService("orm");

        this.actionService = useService("action");
        this.notificationService = useService("notification");
        this.state = useState({
            popup: {
                error: false,
                confirm: false,
                validate: false,
                addMove: false,
                editMove: false,
                editLine: false,
                addLocation: false,
                printReport: false,
                changeOperation: false,
            },

            move: {
                id: 0,
                filter: '',
                all: [],
            },

            line: {
                id: 0,
                filter: '',
                show: false,
            },

            page: {
                id: 0,
                all: [],
            },

            groups: {},
            operation: {},
            location: {
                src: [],
                dest: [],
                add: {},
                type: 'dest',
            },

            reports: [],
            scanning: true,
            sort: 'sequence',
            sound: {'src': null},
        });

        this.mutex = new Mutex();
        this.sequence = 1;
        this.settings = {};
        this.location = [];
        this.locations = {
            src: [[0, '-']],
            dest: [[0, '-']],
            all: [[0, '-']],
        };

        useBus(this.env.bus, 'edit-move', this.editMove);
        useBus(this.env.bus, 'remove-move', this.removeMove);
        useBus(this.env.bus, 'select-move', this.selectMove);
        useBus(this.env.bus, 'update-move', this.updateMove);
        useBus(this.env.bus, 'create-move', this.createMove);

        useBus(this.env.bus, 'print-line', this.onPrintLine);
        useBus(this.env.bus, 'edit-line', this.editLine);
        useBus(this.env.bus, 'remove-line', this.removeLine);
        useBus(this.env.bus, 'update-line', this.updateLine);
        useBus(this.env.bus, 'select-line', this.selectLine);

        useBus(this.env.bus, 'select-sort', this.selectSort);
        useBus(this.env.bus, 'select-location', this.selectLocation);
        useBus(this.env.bus, 'select-add-location', this.selectAddLocation);
        useBus(this.env.bus, 'select-source-location', this.selectSrcLocation);
        useBus(this.env.bus, 'select-destination-location', this.selectDestLocation);
        useBus(this.env.bus, 'go-previous-page', this.goPreviousPage);
        useBus(this.env.bus, 'go-next-page', this.goNextPage);
        useBus(this.env.bus, 'close-popup', this.closePopup);

        this.barcodeService = useService("barcode");
        onMounted(() => {
            this.barcodeService.bus.addEventListener('barcode_scanned', this.onScan.bind(this));
        });
        onWillUnmount(() => {
            this.barcodeService.bus.removeEventListener('barcode_scanned', this.onScan.bind(this));
        });

        useEffect(
            () => {
                this.scrollTo('move', this.state.move.id);
            },
            () => [this.state.move.id]
        );

        useEffect(
            () => {
                this.scrollTo('line', this.state.line.id);
            },
            () => [this.state.line.id]
        );
    }

    scrollTo(type, id) {
        setTimeout(() => {
            const element = document.getElementById(`barcode_${type}_${id}`);
            const container = document.getElementById(`barcode_move`);
    
            if (element && container) {
                const { top: containerTop, bottom: containerBottom } = container.getBoundingClientRect();
                const { top: elementTop, bottom: elementBottom, height: elementHeight } = element.getBoundingClientRect();
                if (elementBottom > containerBottom) {
                    container.scrollTo({
                        top: elementBottom - elementHeight,
                    });
                } else if (elementTop < containerTop) {
                    container.scrollTo({
                        top: elementTop - elementHeight + 250,
                    });
                }
            }
        }, 100);
    }

    selectScannedLocation(location) {
        if (this.state.operation.id) {
            if (this.state.operation.src && this.state.operation.dest) {
                if (this.getMoves().length) {
                    this.selectDestLocation({ detail: location }, true);
                } else {
                    this.selectSrcLocation({ detail: location }, true);
                }
            } else if (this.state.operation.src) {
                this.selectSrcLocation({ detail: location }, true);
            } else if (this.state.operation.dest) {
                this.selectDestLocation({ detail: location }, true);
            }
        }
    }

    selectAddLocation({ detail: location }) {
        this.selectScannedLocation([location.id, location.display_name]);
        this.state.location.add = location;
        this.closePopup({ detail: 'addLocation' });
    }

    selectLocation({ detail: location }, scanned=false) {
        if (location.length) {
            location.push(scanned);
        }

        this.state.location.src = location;
        this.state.location.dest = location;
        this.updatePage();
        this.selectMove();
    }

    selectSrcLocation({ detail: location }, scanned=false) {
        if (location.length) {
            location.push(scanned);
        }

        this.state.location.src = location;
        if (location[0]) {
            if (!this.state.location.dest?.[0]) {
                this.state.location.dest = this.locations.dest[0][0] ? this.locations.dest[0] : this.locations.dest[1];
            }
        } else {
            this.state.location.dest = location;
        }

        this.updatePage();
        this.selectMove();
    }

    selectDestLocation({ detail: location }, scanned=false) {
        if (location.length) {
            location.push(scanned);
        }

        this.state.location.dest = location;
        if (location[0]) {
            if (!this.state.location.src?.[0]) {
                this.state.location.src = this.locations.src[0][0] ? this.locations.src[0] : this.locations.src[1];
            }
        } else {
            this.state.location.src = location;
        }

        this.updatePage();
        this.selectMove();
    }

    setLocationType(operation) {
        if (operation.src && operation.dest) {
            return 'int';
        } else if (operation.src) {
            return 'src';
        } else if (operation.dest) {
            return 'dest';
        } else {
            return '';
        }
    }

    getLocationPage() {
        let src = this.state.location.src?.[0] || 0;
        let dest = this.state.location.dest?.[0] || 0;
        if (src && dest) {
            return `${src}/${dest}`;
        } else {
            return 0;
        }
    }

    getLocationField() {
        const type = this.state.location.type;
        if (type === 'src') {
            return 'location_id';
        } else if (type === 'dest') {
            return 'location_dest_id';
        } else {
            return type;
        }
    }

    getPackageField() {
        if (this.state.location.type === 'src') {
            return 'package_id';
        } else {
            return 'result_package_id';
        }
    }

    getLotField() {
        if (this.state.operation.lot) {
            return 'lot_id';
        } else {
            return 'lot_name';
        }
    }

    getFields() {
        return {
            location: this.getLocationField(),
            package: this.getPackageField(),
            lot: this.getLotField(),
        }
    }

    getPages() {
        let pages = [];
        let moves = this.state.move.all;
        for (let move of moves) {
            let page = this.getMovePage(move);
            if (!pages.includes(page)) {
                pages.push(page);
            }
        }


        let total = pages.length;
        let current = total && this.state.page.id ? 1 : 0;
        let page = this.getLocationPage();
        if (page) {
            let index = pages.findIndex(p => p === page);
            if (index < 0) {
                current = ++total;
            } else {
                current = ++index;
            }


        }
        return { current, total, pages };
    }

    getPage(all) {
        let page = this.state.move.all;
        if (!all && this.state.page.id) {
            let [src, dest] = this.state.page.id.split('/');
            page = page.filter(move => move.location_id?.[0] == src && move.location_dest_id?.[0] == dest);
        }
        return page;
    }

    goToPage(diff=0) {
        let { current, total, pages } = this.getPages();
        if (pages.length) {
            current = --current + diff;
            if (current < 0 || current > total) {
                return;
            }

            let page = pages[current];
            if (!page) {
                return;
            }

            let [src_id, dest_id] = page.split('/');
            let src = this.locations.src.find(i => i[0] == src_id);
            let dest = this.locations.dest.find(i => i[0] == dest_id);
            this.selectSrcLocation({ detail: src });
            this.selectDestLocation({ detail: dest });
        }
    }

    goPreviousPage() {
        this.goToPage(-1);
    }

    goNextPage() {
        this.goToPage(1);
    }

    resetPage() {
        this.state.move.all = [];
    }

    updatePage() {
        this.state.page.id = this.getLocationPage();
    }

    getProducts(all) {
        let products = {};
        let productList = this.getPage(all).map(m => m.product_id);
        for (let product of productList) {
            products[product.id] = product;
        }
        return products;
    }

    getMoves(all) {
        let moves = {};
        let page = all ? this.state.move.all : this.getPage();
        for (let p of page) {
            let id;
            if (['lot', 'serial'].includes(p.product_id.tracking)) {
                id = `0/${p.product_id.id}/${p.location_id?.[0] || '-'}/${p.location_dest_id?.[0] || '-'}`;
                if (id in moves) {
                    moves[id]['qty'] += p.qty;
                    moves[id]['qty_done'] += p.qty_done;
                    moves[id]['lines'].push({ ...p, move: moves[id] });
                } else {
                    moves[id] = {...p, lines: [{ ...p, move: p }]};
                }
            } else {
                id = `${p.id}/${p.product_id.id}/${p.location_id?.[0] || '-'}/${p.location_dest_id?.[0] || '-'}`;
                moves[id] = { move: false, ...p };
            }
        }
        return Object.values(moves);
    }

    getMove(move = {}) {
        let moves = this.getMoves();
        if (!move.id) {
            move = this.state.move;
        }
        return moves.find(l => l.id === move.id);
    }

    getMovePage(move) {
        let id = 0;
        let location_id = move.location_id?.[0] || 0;
        let location_dest_id = move.location_dest_id?.[0] || 0;
        if (location_id && location_dest_id) {
            id = `${location_id}/${location_dest_id}`
        }
        return id;
    }

    createMove({ detail: move }, options={}) {
        let src_id = this.state.location.src[0] || this.state.operation.src || this.locations.src.find(l => l[0])?.[0] || 0;
        let dest_id = this.state.location.dest[0] || this.state.operation.dest || this.locations.dest.find(l => l[0])?.[0] || 0;
        let location_id = this.locations.src.find(l => l[0] == src_id);
        let location_dest_id = this.locations.dest.find(l => l[0] == dest_id);

        let value = {
            id: this.sequence,
            sequence: this.sequence,
            location_id: location_id,
            location_dest_id: location_dest_id,
            package_id: move.package_id || false,
            result_package_id: move.result_package_id || false,
            number: move.number || false,
            product_id: move.product || false,
            qty_done: move.qty_done ?? move.qty,
            qty: move.qty,
            new: move.new,
            checked: true,
            move: false,
            lines: [],
        }

        this.state.move.all.push(value);
        this.sequence++;

        if (!options.noSelect) {
            this.selectMove({ detail: value });
        }

        this.closePopup();
        return value;
    }

    updateMove({ detail: { move, qty, location, packaging, number, checked } }) {
        move = this.state.move.all.find(l => l.id === move.id);
        if (move) {
            if (qty !== undefined) {
                if (move.product_id.tracking == 'serial' && qty > 1) {
                    qty = 1;
                } 
                move.qty_done = parseFloat(qty);
            }
            if (location !== undefined) {
                let id;
                if (location instanceof Object) {
                    if (location.src) {
                        if (!location.src[0]) {
                            id = this.state.operation.src || this.locations.src.find(l => l[0])?.[0] || 0;
                            location.src = this.locations.src.find(l => l[0] == id);
                        }
                        move.location_id = location.src;
                    }
                    if (location.dest) {
                        if (!location.dest[0]) {
                            id = this.state.operation.dest || this.locations.dest.find(l => l[0])?.[0] || 0;
                            location.dest = this.locations.dest.find(l => l[0] == id);
                        }
                        move.location_dest_id = location.dest;
                    }
                } else {
                    if (location && !location[0]) {
                        if (this.state.location.type === 'src') {
                            id = this.state.operation.src || this.locations.src.find(l => l[0])?.[0] || 0;
                            location = this.locations.src.find(l => l[0] == id);
                        } else if (this.state.location.type === 'dest') {
                            id = this.state.operation.dest || this.locations.dest.find(l => l[0])?.[0] || 0;
                            location = this.locations.dest.find(l => l[0] == id);
                        }
                    }

                    let field = this.getLocationField();
                    move[field] = location;
                }
            }
            if (packaging !== undefined) {
                let field = this.getPackageField();
                move[field] = packaging;
            }
            if (number !== undefined) {
                move.number = number;
            }
            if (checked !== undefined) {
                move.checked = checked;
            }
        }
        this.closePopup();
        return move;
    }

    async onPrintLine({ detail: line } = {}) {
        const print = await this.orm.call('barcode.quant.operation', 'print_barcode_line', [line], {});
        if (print) {
            this.actionService.doAction(print);
        }
    }

    editMove({ detail: move }) {
        this.selectMove({ detail: move });
        this.openPopup('editMove');
    }

    deleteMove({ detail: move }) {
        let moves = this.state.move.all;
        let index = moves.findIndex(l => l.id === move.id);
        if (index >= 0) {
            moves.splice(index, 1);
        }
        this.closePopup();
    }

    removeMove({ detail: move }) {
        this.selectMove({ detail: move });
        this.openPopup('confirm', {
            message: _t("Are you sure you want to remove this line?"),
            method: () => this.deleteMove({ detail: move }),
            type: 'danger',
        });
    }

    filterMove(value) {
        this.state.move.filter = value;
    }

    selectMove({ detail: move }={}) {
        if (move) {
            if (this.state.move.id !== move.id) {
                this.state.move.id = move.id;
                if (move.lines?.length) {
                    this.selectLine({ detail: move.lines[0] });
                }
            } else {
                this.state.line.show = !this.state.line.show;
            }
        } else {
            let moves = this.getMoves();
            if (moves.length) {
                this.state.move.id = moves[0].id;
                if (moves[0].lines?.length) {
                    this.selectLine({ detail: moves[0].lines[0] });
                }
            }
        }
        this.scrollTo('move', this.state.move.id);
    }

    selectLine({ detail: line } = {}) {
        if (line.id) {
            this.state.move.id = line.move.id;
            this.state.line.id = line.id;
            this.state.line.show = true;
        } else {
            let moves = this.getMoves();
            if (moves.length && moves[0].lines.length) {
                this.state.line.id = moves[0].lines[0].id;
                this.state.line.show = true;
            }
        }
        this.scrollTo('line', this.state.line.id);
    }

    prepareLines() {
        let lines = [ ...this.state.move.all ];
        for(let line of lines) {
            delete line.move;
            delete line.lines;
            delete line.sequence;
        }
        return lines;
    }

    getLine(line = {}) {
        if (!line.id) {
            line = this.state.line;
        }
        let move = this.getMove() || { lines: [] };
        return move.lines.find(l => l.id === line.id);
    }

    nextLine(barcode=false) {
        let move = this.getMove() || { lines: [] };
        let line;
        if (barcode) {
            line = move.lines.find(l => l.number === barcode);
        }
        if (!line) {
            line = move.lines.find(l => !l.number);
        }
        if (line) {
            return line;
        }

        let moves = this.getMoves();
        for (let m of moves) {
            if (m.product_id.id === move.product_id.id) {
                if (barcode) {
                    line = m.lines.find(l => l.number === barcode);
                }
                if (!line) {
                    line = m.lines.find(l => !l.number);
                }
                if (line) {
                    return line;
                }
            }
        }
    }

    editLine({ detail: line }) {
        this.selectLine({ detail: line });
        this.openPopup('editLine');
    }

    updateLine({ detail: line }) {
        line = this.updateMove({ detail: line });
        let moves = this.getMoves();
        for (let move of moves) {
            for (let l of move.lines) {
                if (l.id === line.id) {
                    line.move = move;
                    this.selectLine({ detail: line });
                    return line;
                }
            }
        }
    }

    deleteLine() {
        this.deleteMove(...arguments);
    }

    removeLine({ detail: line }) {
        this.selectLine({ detail: line });
        this.openPopup('confirm', {
            message: _t("Are you sure you want to remove this line?"),
            method: () => this.deleteLine({ detail: line }),
            type: 'danger',
        });
    }

    createLine({ detail: line }) {
        line = this.createMove({ detail: line }, { noSelect: true });
        if (!line) {
            return;
        }

        let moves = this.getMoves();
        for (let move of moves) {
            for (let l of move.lines) {
                if (l.id === line.id) {
                    line.move = move;
                    this.selectLine({ detail: line });
                    return line;
                }
            }
        }
        return line;
    }

    selectSort({ detail: key }) {
        let moves = this.state.move.all;
        if (key === 'name') {
            moves.sort((a, b) => {
                let x = a.product_id.name.toLowerCase();
                let y = b.product_id.name.toLowerCase();
                if (x < y) {
                    return -1;
                } else if (x > y) {
                    return 1;
                } else {
                    return 0;
                }
            });
        } else if (key === 'reference') {
            moves.sort((a, b) => {
                let x = a.product_id.default_code.toLowerCase();
                let y = b.product_id.default_code.toLowerCase();
                if (x < y) {
                    return -1;
                } else if (x > y) {
                    return 1;
                } else {
                    return 0;
                }
            });
        } else if (key === 'quantity') {
            moves.sort((a, b) => {
                return a.qty_done - b.qty_done;
            });
        } else if (key === 'weight') {
            moves.sort((a, b) => {
                return a.product_id.weight - b.product_id.weight;
            });
        } else if (key === 'sequence') {
            moves.sort((a, b) => {
                return a.sequence - b.sequence;
            });
        }

        let id = 1;
        for (let move of moves) {
            move.id = id++;
        }

        this.selectMove();
        this.state.sort = key;
    }

    openPopup(popup, options=true) {
        if (popup) {
            this.state.popup[popup] = options;
        }
    }

    closePopup({ detail: popup }={}) {
        if (popup) {
            this.state.popup[popup] = false;
        } else {
            for (let popup in this.state.popup) {
                this.state.popup[popup] = false;
            }
        }
    }

    async applyTransfer() {
        const result = await this.validateTransfer();
        if (!result) {
            return;
        }

        this.onBack();
        this.resetPage();
        return result;
    }

    async applyValidateTransfer() {
        const result = await this.validateTransfer(true);
        if (!result) {
            return;
        }

        this.onBack();
        this.resetPage();
        return result;
    }

    onScan(barcode) {
        this.mutex.exec(async () => {
            await this.scan(barcode.detail.barcode);
        });
    }

    onPlaySound(name) {
        if (name === 'error') {
            this.state.sound.src = "/barcode_wms/static/src/sounds/error.wav";
        } else if (name === 'bell') {
            this.state.sound.src = "/barcode_wms/static/src/sounds/bell.wav";
        }
    }

    async onBack() {
        this.closePopup();
        if (this.env.config.breadcrumbs.length) {
            try {
                await this.actionService.restore();
            } catch {
                await this.actionService.doAction('barcode_wms.action_barcode');
            }
        } else {
            await this.actionService.doAction('barcode_wms.action_barcode');
        }
    }
}

Components.components = {
    AddMove,
    EditMove,
    EditLine,
    StockMove,
    Pagination,
    NotificationSound,
};
Components.template = "barcode_wms.Components"
