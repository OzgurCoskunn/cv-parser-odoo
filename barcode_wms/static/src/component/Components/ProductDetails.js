/** @odoo-module **/


import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { useService, useBus } from "@web/core/utils/hooks";
import { SearchBar } from "@barcode_wms/component/Components/SearchBar";
import { NotificationSound } from "@barcode_wms/component/Components/NotificationSound";
import { WarehouseDetails } from "@barcode_wms/component/Components/WarehouseDetails";
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";

export class ProductDetails extends Component {

    setup() {
        super.setup();
        this.mutex = new Mutex();
        this.orm = useService("orm");

        this.actionService = useService("action");
        this.notificationService = useService("notification");
        this.state = useState({
            details: {},
            visible: false,
            available: false,
            sound: { src: null },
        });
        useBus(this.env.bus, 'barcode_scanned', this.onBarcodeScanned);
        useBus(this.env.bus, 'select-product', this.selectProduct);
        onWillStart(async () => {
            if (this.props.action.params) {
                let product = await this.getProduct(this.props.action.params);
                await this.getData(product[0]);
            }
        });
    }

    onBarcodeScanned(barcode) {
        if (!barcode) {
            return;
        }
        this.mutex.exec(async () => {
            const product = await this.getProduct({ barcode });
            if (product.length === 1) {
                await this.getData(product[0])
            } else {
                this.notificationService.add("Barcode not found", {
                    title: "Error",
                    type: "danger",
                })
                this.onPlaySound('error');
            }
        });
    }

    async getProduct(values = {}) {
        const domain = [];
        for (const [key, value] of Object.entries(values)) {
            if (!value) {
                continue;
            }

            let operator;
            if (typeof value === 'string') {
                if (value.indexOf('%') < 0) {
                    operator = '=';
                } else {
                    operator = 'like';
                }
            } else {
                operator = '=';
            }
            domain.push([key, operator, value]);
        }

        if (!domain.length) {
            return [];
        }

        return await this.orm.searchRead("product.product", domain, [
            "id",
            "type",
            "default_code",
            "categ_id",
            "weight",
            "list_price",
            "display_name"
        ], {
            limit: 100
        });
    }

    EditMove() {
        this.state.visible = true;
    }

    closePopup() {
        this.state.visible = false;
    }

    async selectProduct(payload) {
        // Handle both direct payload and CustomEvent wrapper
        const product = payload.detail ?? payload;
        await this.getData(product);
    }

    async back() {
        if (this.env.config.breadcrumbs.length) {
            try {
                await this.actionService.restore();
            } catch {
                await this.actionService.doAction('barcode_wms.action_barcode');
            }
        }
    }

    imageSrc(id) {
        return `/web/image?model=product.product&field=image_512&id=${id}&unique=1`;
    }

    async getData(product) {
        if (!product || !product.id) {
            console.warn("ProductDetails: received invalid product data", product);
            this.notificationService.add("Error: Invalid product data received", {
                type: "danger",
            });
            return;
        }

        try {
            const data = await this.orm.call('product.product', 'get_barcode_data', [product.id, 1]);
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
        } catch (error) {
            console.error("ProductDetails: Error fetching string data", error);
            this.notificationService.add("Error loading product details", {
                type: "danger",
            });
        }
    }

    onPlaySound(name) {
        if (name === 'error') {
            this.state.sound.src = "/barcode_wms/static/src/sounds/error.wav";
        } else if (name === 'bell') {
            this.state.sound.src = "/barcode_wms/static/src/sounds/bell.wav";
        }
    }
}

ProductDetails.template = "barcode_wms.ProductDetails";
ProductDetails.components = { SearchBar, WarehouseDetails, NotificationSound };
registry.category("actions").add('barcode_product', ProductDetails);
