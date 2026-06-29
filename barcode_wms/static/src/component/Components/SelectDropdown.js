/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Component, useRef, useState, useExternalListener, onWillStart, useEffect } from "@odoo/owl";

export class SelectDropdown extends Component {
    setup() {
        super.setup();
        this.ui = useService("ui");
        this.orm = useService("orm");
        this.rootRef = useRef("root");
        this.state = useState({ visible: false });

        useExternalListener(window, "click", this.onWindowClicked);
        useEffect(
            () => {
                Promise.resolve().then(() => {
                    this.myActiveEl = this.ui.activeElement;
                });
            },
            () => []
        );
    }

    onClickDropdownList(selected) {
        this.state.visible = false;
        this.env.bus.trigger(this.props.trigger, selected);
    }

    clickDropDown() {
        this.state.visible = !this.state.visible;
    }

    onWindowClicked(ev) {
        if (!this.state.visible) {
            return;
        }

        if (this.ui.activeElement !== this.myActiveEl) {
            return;
        }

        const rootEl = this.rootRef.el;
        const gotClickedInside = rootEl.contains(ev.target);
        if (!gotClickedInside) {
            this.state.visible = false;
        }
    }
}

export class SelectDropdownSort extends SelectDropdown {}
export class SelectDropdownOperation extends SelectDropdown {
    setup() {
        super.setup();
        this.operations = this.props.data || [];
        this.state = useState({
            ...this.state,
            operations: [ ...this.operations ],
        });
    }

    async setQuery(ev) {
        clearTimeout(this.debounce);
        this.debounce = setTimeout(() => {
            const query = ev.target.value.toLowerCase();
            const operations = [ ...this.operations ];
            if (!query) {
                this.state.operations = operations;
            } else {
                this.state.operations = operations.filter(o => o.display_name.toLowerCase().includes(query));
            }
        }, 300);
    }
}

export class SelectDropdownLocation extends SelectDropdown {
    setup() {
        super.setup();
        this.warehouses = this.props.data || [];
        this.state = useState({
            ...this.state,
            warehouses: [ ...this.warehouses ],
        });
    }

    async setQuery(ev) {
        clearTimeout(this.debounce);
        this.debounce = setTimeout(() => {
            const query = ev.target.value.toLowerCase();
            if (!query) {
                this.state.warehouses = [ ...this.warehouses ];
            } else {
                const warehouses = [];
                for (const warehouse of this.warehouses) {
                    const locations = warehouse.locations.filter((location) => location[1].toLowerCase().includes(query));
                    if (locations.length) {
                        warehouses.push({
                            warehouse: warehouse.warehouse,
                            locations: locations,
                        });
                    }
                }
                this.state.warehouses = warehouses;
            }
        }, 300);
    }
}

export class SelectDropdownLocationSrc extends SelectDropdownLocation {
    setup() {
        super.setup();
        this.locations = this.props.data || [];
        this.state = useState({
            ...this.state,
            locations: [ ...this.locations ],
        });
    }

    async setQuery(ev) {
        clearTimeout(this.debounce);
        this.debounce = setTimeout(() => {
            const query = ev.target.value.toLowerCase();
            const locations = [ ...this.locations ];
            if (!query) {
                this.state.locations = locations;
            } else {
                this.state.locations = locations.filter(l => l[1].toLowerCase().includes(query));
            }
        }, 300);
    }
}

export class SelectDropdownLocationDest extends SelectDropdownLocation {
    setup() {
        super.setup();
        this.locations = this.props.data || [];
        this.state = useState({
            ...this.state,
            locations: [ ...this.locations ],
        });
    }

    async setQuery(ev) {
        clearTimeout(this.debounce);
        this.debounce = setTimeout(() => {
            const query = ev.target.value.toLowerCase();
            const locations = [ ...this.locations ];
            if (!query) {
                this.state.locations = locations;
            } else {
                this.state.locations = locations.filter(l => l[1].toLowerCase().includes(query));
            }
        }, 300);
    }
}

export class SelectDropdownLocationAdd extends SelectDropdownLocation {
    setup() {
        super.setup();
        onWillStart(async () => {
            this.props.data = await this.orm.searchRead('stock.location', [], ['id', 'name', 'display_name', 'warehouse_id'], { limit: 100 });
        });
    }
}

SelectDropdown.template = "barcode_wms.SelectDropdown";
SelectDropdownSort.template = "barcode_wms.SelectDropdownSort";
SelectDropdownOperation.template = "barcode_wms.SelectDropdownOperation";
SelectDropdownLocation.template="barcode_wms.SelectDropdownLocation";
SelectDropdownLocationAdd.template="barcode_wms.SelectDropdownLocationAdd";
SelectDropdownLocationSrc.template = "barcode_wms.SelectDropdownLocationSrc";
SelectDropdownLocationDest.template = "barcode_wms.SelectDropdownLocationDest";