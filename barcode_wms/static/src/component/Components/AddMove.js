/** @odoo-module **/

import { SearchBar } from './SearchBar';
import { WarehouseDetails } from './WarehouseDetails';
import { useService, useBus } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

export class AddMove extends Component {

    setup() {
        super.setup();
        this.state = useState({
            available: false,
            product: {},
            quantity: "1",
            details: {},
        });
        this.orm = useService("orm");
        useBus(this.env.bus, 'select-product', this.selectProduct);
    }

    async selectProduct({ detail: product }) {
        this.state.product = product;
        await this.getData(product);
    }

    selectDot() {
        let quantity = this.state.quantity.toString();
        if (quantity[quantity.length - 1] !== '.') {
            quantity = quantity + '.';
        }
        this.state.quantity = quantity;
    }

    digitValue(ev) {
        let value = ev.target.value;
        let quantity = this.state.quantity;

        if (quantity === '0') {
            if (value === '0') {
                quantity = '0';
            } else {
                quantity = value;
            }
        } else {
            quantity = quantity + value;
        }
        this.state.quantity = quantity;
    }

    imageSrc(id) {
        return `/web/image?model=product.product&field=image_512&id=${id}&unique=1`;
    }

    clearLastDigit() {
        let quantity = '0';
        if (this.state.quantity.length <= 1) {
            quantity = '0';
        } else {
            quantity = this.state.quantity.substring(0, this.state.quantity.length - 1);
        }
        this.state.quantity = quantity
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

    async getData(product) {
        let data = await this.orm.call('product.product', 'get_barcode_data', [product.id, 1]);
        this.state.details = {
            user: data.user,
            company: data.company,
            product: data.product,
            variants: data.variants,
            currency: data.currency,
            suppliers: data.suppliers,
            pricelists: data.pricelists,
            warehouses: data.warehouses,
            warehouses_ready: data.warehouses_ready,
        };
        this.state.available = true;
    }

    back() {
        this.env.bus.trigger('close-popup');
    }

    confirm() {
        this.env.bus.trigger('create-move', {
            product: this.state.product,
            qty: parseFloat(this.state.quantity),
        });
    }
}

AddMove.template = "barcode_wms.AddMove"
AddMove.components = { SearchBar, WarehouseDetails };