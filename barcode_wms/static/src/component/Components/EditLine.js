/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

export class EditLine extends Component {

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            details: {},
            number: this.props.line.number || '',
            quantity: this.props.line.qty_done || 0,
            packaging: this.props.line[this.props.fields.package] || [],
            location: {
                src: this.props.line.location_id,
                dest: this.props.line.location_dest_id,
            }
        });

        onWillStart(async () => {
            await this.getData(this.props.line.product_id);
        });
    }

    async showProduct() {
        await this.actionService.doAction({
            name: 'Product Information',
            type: 'ir.actions.client',
            target: 'fullscreen',
            tag: 'barcode_product',
            params: {
                id: this.props.line.product_id.id,
            },
        });
    }

    onClickQty() {
        this.state.quantity = this.props.line.qty;
    }

    onChangeQty(ev) {
        this.state.quantity = parseFloat(ev.target.value);
    }

    changeLocation(type, id) {
        this.state.location[type] = this.props.locations[type].find(l => l[0] === parseInt(id)) || [];
    }

    onChangePackage(ev) {
        let dataset = ev.target.selectedOptions[0]?.dataset;
        if (dataset) {
            let id = parseInt(dataset.id);
            let name = dataset.name;
            let number = dataset.number;
            let qty = parseInt(dataset.qty);
            this.state.packaging = id ? [id, name, number, qty] : [];
        }
    }

    onChangeNumber(ev) {
        this.state.number = ev.target.value;
    }
    async getData(product) {
        if (this.props.settings.edit_package) {
            let data = await this.orm.call('product.product', 'get_barcode_data', [product.id, 1, true]);
            this.state.details = {
                packages: data.packages,
            };
        }
    }

    back() {
        this.env.bus.trigger('close-popup');
    }

    confirm() {
        this.env.bus.trigger('update-line', {
            move: this.props.line,
            qty: this.state.quantity,
            number: this.state.number,
            location: this.state.location,
            packaging: this.state.packaging,
        });
    }
}

EditLine.template = "barcode_wms.EditLine";