/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import * as BarcodeCameraScanner from '@barcode_wms/component/BarcodeCamera/BarcodeCamera';
import { Component, useRef, useState, useExternalListener, useEffect } from "@odoo/owl";

export class SearchBar extends Component {
    setup() {
        super.setup();
        this.state = useState({
            visible: !this.props.filter && this.props.visible,
            products: [],
        });
        this.query = useState({
            value: '',
        })
        this.ui = useService("ui");
        this.orm = useService("orm");
        this.rootRef = useRef("root");
        this.notificationService = useService("notification");

        useExternalListener(window, "click", this.onWindowClicked);
        useEffect(
            () => {
                Promise.resolve().then(() => {
                    this.myActiveEl = this.ui.activeElement;
                });
            },
            () => []
        );
        useEffect(
            () => {
                if (this.props.filter) {
                    this.props.filter(this.query.value);
                } else {
                    this.sendRequest(this.query.value);
                }
            },
            () => [this.query.value]
        );
    }

    async onClickCamera() {
        const barcode = await BarcodeCameraScanner.scanBarcode();
        if (barcode) {
            this.env.bus.trigger('barcode_scanned', barcode);
        } else {
            this.notificationService.add("Barcode not found", {
                title: "Error",
                type: "danger",
            })
        }
    }

    async setQuery(ev) {
        clearTimeout(this.debounce);
        this.debounce = setTimeout(() => {
            this.query.value = ev.target.value;
        }, 300);
    }

    async sendRequest(value) {
        this.state.products = await this.orm.call('barcode.operation', 'get_barcode_product', [value]);
    }

    imageSrc(id) {
        return `/web/image?model=product.product&field=image_128&id=${id}&unique=1`;
    }

    onFocus() {
        if(!this.props.filter) {
            this.state.visible = true;
        }
    }

    async selectProduct(product) {
        this.env.bus.trigger('select-product', product);
        this.state.visible = false;
    }

    onWindowClicked(ev) {
        if (this.props.visible || !this.state.visible || this.ui.activeElement !== this.myActiveEl) {
            return;
        }

        const rootEl = this.rootRef.el;
        const gotClickedInside = rootEl.contains(ev.target);
        if (!gotClickedInside) {
            this.state.visible = false;
        }
    }
}

SearchBar.template = "barcode_wms.SearchBar";