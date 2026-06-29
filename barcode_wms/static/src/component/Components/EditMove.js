/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { WarehouseDetails } from "./WarehouseDetails";
import { Component, useState, onWillStart } from "@odoo/owl";

export class EditMove extends Component {

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({
            details: {},
            barcode: {
                value: this.props.move.product_id.barcode,
                disable: false,
                edit: false,
            },
            quantity: this.props.move.qty_done.toString(),
            packaging: this.props.move[this.props.fields.package] || [],
            location: {
                src: this.props.move.location_id,
                dest: this.props.move.location_dest_id,
            }
        });

        onWillStart(async () => {
            await this.getData(this.props.move.product_id);
        });
    }

    digitValue(ev) {
        let digit = ev.target.value;
        let quantity = this.state.quantity;
        if (quantity === '0') {
            if (digit === '0') {
                quantity = '0';
            } else {
                quantity = digit;
            }
        } else {
            quantity = quantity + digit;
        }
        this.state.quantity = quantity;
    }

    clearLastDigit() {
        let quantity = '0';
        if (this.state.quantity.length <= 1) {
            quantity = '0';
        } else {
            quantity = this.state.quantity.substring(0, this.state.quantity.length - 1);
        }
        this.state.quantity = quantity;
    }

    plusOne() {
        let quantity = parseFloat(this.state.quantity) + 1;
        this.state.quantity = quantity.toString();
    }

    minusOne() {
        if (parseFloat(this.state.quantity) > 0) {
            let quantity = parseFloat(this.state.quantity) - 1;
            this.state.quantity = quantity.toString();
        }
    }

    selectDot() {
        let quantity = this.state.quantity.toString();
        if (quantity[quantity.length - 1] !== '.') {
            quantity = quantity + '.';
        }
        this.state.quantity = quantity;
    }

    imageSrc(id) {
        return `/web/image?model=product.product&field=image_512&id=${id}&unique=1`;
    }

    changeLocation(type, id) {
        this.state.location[type] = this.props.locations[type].find(l => l[0] === parseInt(id)) || [];
    }

    changePackage(ev) {
        let dataset = ev.target.selectedOptions[0]?.dataset;
        if (dataset) {
            let id = parseInt(dataset.id);
            let name = dataset.name;
            let number = dataset.number;
            let qty = parseInt(dataset.qty);
            this.state.packaging = id ? [id, name, number, qty] : [];
        }
    }

    editBarcode() {
        this.state.barcode.edit = true;
    }

    readBarcode() {
        this.state.barcode.edit = false;
    }

    enableBarcode(){
        this.state.barcode.edit = true;
        this.state.barcode.disable = false;
    }

    disableBarcode() {
        this.state.barcode.disable = true;
    }

    async saveBarcode(){
        this.state.barcode.disable = true;

        try {
            await this.orm.call('product.product', 'write', [this.props.move.product_id.id, {'barcode': this.state.barcode.value}]);
            this.state.barcode.edit = false;
        } catch (error) {
            console.error(error);
            alert(_('An error occured. Please try again.'));
        }

        this.state.barcode.disable = false;
    }

    async getData(product) {
        let data = await this.orm.call('product.product', 'get_barcode_data', [product.id, 1, true]);
        this.state.details = {
            user: data.user,
            company: data.company,
            product: data.product,
            variants: data.variants,
            currency: data.currency,
            packages: data.packages,
            suppliers: data.suppliers,
            pricelists: data.pricelists,
            warehouses: data.warehouses,
            warehouses_ready: data.warehouses_ready,
        };
        this.state.barcode.value = this.state.details.product.barcode;
    }

    back() {
        this.env.bus.trigger('close-popup');
    }

    confirm() {
        this.env.bus.trigger('update-move', {
            move: this.props.move,
            qty: this.state.quantity,
            location: this.state.location,
            packaging: this.state.packaging,
        });
    }
}

EditMove.components = { WarehouseDetails };
EditMove.template = "barcode_wms.EditMove";