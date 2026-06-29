/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onWillUnmount, useEffect } from "@odoo/owl";
import { SelectDropdown } from '../Components/SelectDropdown';

export class WarehouseOperations extends Component {

    setup() {
        this.state = useState({
            filtered: [],
            selected: {},
            state: 'assigned',
        });

        this.orm = useService("orm");

        this.actionService = useService("action");
        this.notificationService = useService("notification");
        this.operations = [];
        onWillUnmount(() => {
            // Barcode handling removed - not needed in this component
        });
        onWillStart(async () => {
            this.operations = await this.orm.call('barcode.warehouse.operation', 'get_operations', [], {});
        });
    }

    async selectType(type) {
        this.state.selected = type;
        this.state.filtered = await this.orm.searchRead("stock.picking", [
            ["picking_type_id", "=", type.id],
            ["state", "=", this.state.state],
        ], [], { limit: 100 });
        this.actionService.doAction({
            target: 'fullscreen',
            type: 'ir.actions.client',
            tag: 'barcode_warehouse_picking',
            name: 'Warehouse Picking Type Operations',
            params: {
                picking_type_id: this.state.selected.id,
            }
        });
    }

    async onBack() {
        if (this.env.config.breadcrumbs.length) {
            try {
                await this.actionService.restore();
            } catch {
                await this.actionService.doAction('barcode_wms.action_barcode');
            }
        }
    }
}

export class WarehousePickings extends Component {

    setup() {
        this.state = useState({
            filtered: [],
            selected: {},
            visible: false,
            state: 'assigned',

        });
        this.query = useState({ value: '' });
        this.orm = useService("orm");

        this.actionService = useService("action");
        this.notificationService = useService("notification");

        useBus(this.env.bus, 'select-state', this.selectState);
        useEffect(
            () => {
                this.sendRequest(this.query.value);
            },
            () => [this.query.value]
        );
        onWillStart(() => this.load());
    }

    async load() {
        this.state.filtered = await this.orm.searchRead("stock.picking", [
            ["picking_type_id", "=", this.props.action.params.picking_type_id],
            ["state", "=", this.state.state]
        ], [], { limit: 100 });
    }

    async setQuery(ev) {
        clearTimeout(this.debounce);
        this.debounce = setTimeout(() => {
            this.query.value = ev.target.value;
        }, 300);
    }

    async sendRequest(value) {
        if (value) {
            this.state.filtered = await this.orm.searchRead("stock.picking", [
                ["picking_type_id", "=", this.props.action.params.picking_type_id],
                ["state", "=", this.state.state],
                "|", "|",
                ["origin", "ilike", value],
                ["partner_id", "ilike", value],
                ["name", "ilike", value],
            ], [], { limit: 100 });
        } else {
            await this.load();
        }
    }

    async selectState({ detail: state }) {
        this.state.state = state;
        this.state.filtered = await this.orm.searchRead("stock.picking", [
            ["picking_type_id", "=", this.props.action.params.picking_type_id],
            ["state", "=", this.state.state]
        ], [], { limit: 100 });
    }

    async selectOperation(picking) {
        this.state.visible = false;
        this.state.selected = picking;
        this.actionService.doAction({
            target: 'fullscreen',
            type: 'ir.actions.client',
            tag: 'warehouse_picking_operations',
            name: 'Warehouse Picking Operations',
            params: {
                picking_id: picking.id,
            },
        });
    }

    viewPicking(picking) {
        this.actionService.doAction({
            target: 'new',
            name: 'Example',
            res_model: 'stock.picking',
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
            res_id: picking.id,
        });
    }

    async onBack() {
        if (this.env.config.breadcrumbs.length) {
            try {
                await this.actionService.restore();
            } catch {
                await this.actionService.doAction('barcode_wms.action_barcode');
            }
        }
    }
}

export class WarehouseState extends SelectDropdown {}

WarehousePickings.components = { WarehouseState };
WarehouseState.template = "barcode_wms.WarehouseState";
WarehousePickings.template = "barcode_wms.WarehousePickings";
WarehouseOperations.template = "barcode_wms.WarehouseOperations";

registry.category("actions").add('barcode_warehouse_operation', WarehouseOperations);
registry.category("actions").add('barcode_warehouse_picking', WarehousePickings);