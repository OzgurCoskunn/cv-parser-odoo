/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SelectionField } from "@web/views/fields/selection/selection_field";

export class ResponseTypeSelection extends SelectionField {
    get hierarchyOptions() {
        const opts = this.options;
        return [
            { name: this.env._t('Information'), children: opts.filter(x => x[0] && x[0].startsWith('1')) },
            { name: this.env._t('Success'), children: opts.filter(x => x[0] && x[0].startsWith('2')) },
            { name: this.env._t('Redirection'), children: opts.filter(x => x[0] && x[0].startsWith('3')) },
            { name: this.env._t('Client Error'), children: opts.filter(x => x[0] && x[0].startsWith('4')) },
            { name: this.env._t('Server Error'), children: opts.filter(x => x[0] && x[0].startsWith('5')) },
        ];
    }
}
ResponseTypeSelection.template = "fsm_api.ResponseTypeSelection";

registry.category("fields").add("fsm_api_response_type_selection", { component: ResponseTypeSelection });
