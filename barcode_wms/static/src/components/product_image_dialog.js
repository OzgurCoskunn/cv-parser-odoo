/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class ProductImageDialog extends Component {
    static components = { Dialog };
    
    static props = {
        record: Object,
        close: Function,
    };
    
    static template = "barcode_wms.ProductImageDialog";
    
    get source() {
        return `/web/image/product.product/${this.props.record.id}/image_1024`;
    }
    
    get title() {
        return this.props.record.display_name;
    }
}
