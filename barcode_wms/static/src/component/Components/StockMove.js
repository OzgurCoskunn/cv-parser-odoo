/** @odoo-module **/

import { Component, useState, onWillUpdateProps } from "@odoo/owl";

export class StockMove extends Component {

    setup() {
        super.setup();
        this.state = useState({
            moves: this.props.moves || [],
            groups: this.props.groups || {},
        });
        onWillUpdateProps(nextProps => {
            if (nextProps.move.filter) {
                this.state.moves = nextProps.moves.filter(v => v.product_id.display_name.toLowerCase().includes(this.props.move.filter));
            } else {
                this.state.moves = nextProps.moves;
            }
        });
    }

    onDone(move) {
        move.qty_done = move.qty;
        this.env.bus.trigger('update-move', {
            move: move,
            qty: move.qty_done,
        });
    }

    onReset(move) {
        move.qty_done = 0;
        this.env.bus.trigger('update-move', {
            move: move,
            qty: move.qty_done,
        });
    }

    onCheck(move) {
        move.checked = !move.checked;
        this.env.bus.trigger('update-move', {
            move: move,
            checked: move.checked,
        });
    }

    onPlus(move) {
        move.qty_done++;
        this.env.bus.trigger('update-move', {
            move: move,
            qty: move.qty_done,
        });
    }

    onMinus(move) {
        move.qty_done--;
        if (move.qty_done < 0) {
            move.qty_done = 0;
        }
        this.env.bus.trigger('update-move', {
            move: move,
            qty: move.qty_done,
        });
    }

    onEdit(move) {
        this.env.bus.trigger('edit-move', move);
    }

    onRemove(move) {
        this.env.bus.trigger('remove-move', move);
    }

    onSelect(move) {
        this.env.bus.trigger('select-move', move);
    }

    onPrintLine(line) {
        this.env.bus.trigger('print-line', line);
    }

    onPlusLine(line) {
        line.qty_done++;
        //if (line.qty_done > line.qty) {
        //    line.qty_done = line.qty;
        //}
        this.env.bus.trigger('update-line', {
            move: line,
            qty: line.qty_done,
        });
    }

    onMinusLine(line) {
        line.qty_done--;
        if (line.qty_done < 0) {
            line.qty_done = 0;
        }
        this.env.bus.trigger('update-line', {
            move: line,
            qty: line.qty_done,
        });
    }

    onDoneLine(line) {
        line.qty_done = line.qty;
        this.env.bus.trigger('update-line', {
            move: line,
            qty: line.qty_done,
        });
    }

    onEditLine(line) {
        this.env.bus.trigger('edit-line', line);
    }

    onRemoveLine(line) {
        this.env.bus.trigger('remove-line', line);
    }

    onSelectLine(line) {
        this.env.bus.trigger('select-line', line);
    }

    imageSrc(id) {
        return `/web/image?model=product.product&field=image_128&id=${id}&unique=1`;
    }
}

StockMove.template = "barcode_wms.StockMove";
