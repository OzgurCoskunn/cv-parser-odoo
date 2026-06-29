/** @odoo-module **/

import { session } from "@web/session";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Mutex } from "@web/core/utils/concurrency";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { append, createElement } from "@web/core/utils/xml";
import { rpc } from "@web/core/network/rpc";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { Field } from "@web/views/fields/field";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormCompiler } from "@web/views/form/form_compiler";
import { Thread } from "@mail/core/common/thread_model";
import { Component, onWillStart, onMounted, onWillUnmount, useRef, xml } from "@odoo/owl";
// Ported Chatter customization to Odoo 19 Thread model
patch(Thread.prototype, {
    setup() {
        super.setup();
        this.fsmHasMessageAccess = true;
        this.fsmHasNoteAccess = true;
        this.fsmHasActivityAccess = true;
        this.fsmHasAttachmentAccess = true;
        this.fsmHasFollowerAccess = true;
        this.fsmHasLogAccess = true;
    },

    async fetchMessages() {
        const res = await super.fetchMessages(...arguments);
        if (this.model && this.model.startsWith('fsm.')) {
             this.fetchFsmPermissions();
        }
        return res;
    },

    async fetchFsmPermissions() {
        try {
            const perms = await rpc('/fsm/access/chatter', {
                id: this.id,
                model: this.model,
            }, { silent: true });
            
            if (perms) {
                this.fsmHasMessageAccess = perms.hasMessageAccess;
                this.fsmHasNoteAccess = perms.hasNoteAccess;
                this.fsmHasActivityAccess = perms.hasActivityAccess;
                this.fsmHasAttachmentAccess = perms.hasAttachmentAccess;
                this.fsmHasFollowerAccess = perms.hasFollowerAccess;
                this.fsmHasLogAccess = perms.hasLogAccess;
            }
        } catch (e) {
            console.error("Failed to fetch FSM permissions", e);
        }
    }
});

/*patch(ActionMenus.prototype, "fsm_access_action", {
    get printItems() {
        const hasGroup = await session.user_has_group('fsm.group_action_print');
        if (!hasGroup) return [];
        return this._super(this, arguments);
    },

    async setActionItems(props) {
        const _super = this._super;
        const hasGroup = await session.user_has_group('fsm.group_action_button');
        if (!hasGroup) return [];
        return _super(props);
    }
});*/

patch(Field.prototype, {
    get fieldComponentProps() {
        const props = super.fieldComponentProps;
        const record = this.props.record;
        if (record.resModel && record.resModel.startsWith('fsm.')) {
            const fieldInfo = this.props.fieldInfo;
            const evalContext = record.evalContext;
            const modifiers = fieldInfo.modifiers || {};
            if (modifiers.textonly && props.canOpen) {
                props.canOpen = !evalDomain(modifiers.textonly, evalContext);
            }
        }
        return props;
    }
});

// FilePond is loaded as a global library in assets
const FilePond = window.FilePond;
const FilePondPluginImagePreview = window.FilePondPluginImagePreview;
const FilePondPluginFileValidateSize = window.FilePondPluginFileValidateSize;
const FilePondPluginFileValidateType = window.FilePondPluginFileValidateType;

if (FilePond) {
    FilePond.registerPlugin(FilePondPluginImagePreview);
    FilePond.registerPlugin(FilePondPluginFileValidateSize);
    FilePond.registerPlugin(FilePondPluginFileValidateType);
}

async function reload () {
    await this.model.load();
    this.model.notify();
}

export class FsmFile extends Component {
    setup() {
        super.setup(...arguments);
        this.file = useRef("file");
        this.orm = useService("orm");
        this.http = useService("http");
        this.resID = this.props.action.context.active_id;
        this.resModel = this.props.action.context.active_model;
        this.type = undefined;
        this.size = undefined;

        useHotkey("escape", () => {
            this.props.close();
        });

        onWillStart(async () => {
            const { type, size } = await this.orm.call(this.resModel, "get_metadata", [this.resID]);
            this.type = type || undefined;
            this.size = size || undefined;
        });

        onMounted(() => {
            const file = this.file.el;
            const props = {
                credits: false,
                allowMultiple: true,
                captureMethod: 'environment',
                allowFileSizeValidation: false,
            }
            if (this.size) {
                Object.assign(props, {
                    maxFileSize: this.size,
                    allowFileSizeValidation: true,
                    labelMaxFileSizeExceeded: _t('File is too large'),
                    labelMaxFileSize: _t('Maximum file size is {filesize}'),
                    labelMaxTotalFileSizeExceeded: _t('Maximum total size exceeded'),
                    labelMaxTotalFileSize: _t('Maximum total file size is {filesize}'),
                })
            }
            this.images = FilePond.create(file, props);
            setTimeout(() => this.images.browse(), 100);
        });
    }

    async save() {
        const files = this.images.getFiles().map(f => f.file);
        const result = await this.http.post("/web/binary/upload_attachment", {
            csrf_token: odoo.csrf_token,
            model: this.resModel,
            id: this.resID,
            ufile: files,
        });
        await this.env.bus.trigger('FSM:RELOAD');
        await this.props.options.onClose();
        this.props.close();
    }

    close() {
        this.props.close();
    }
};
FsmFile.template = 'Fsm.File';

export class FsmReasonError extends Component {
    setup() {
        super.setup(...arguments);
        this.action = useService('action');
        const value = this.props.data.arguments?.[1];
        if (!value) {
            console.error('ReasonError has no action. Nothing to do...');
        }
        this.action.doAction(value);
        this.props.close();
    }
}
FsmReasonError.template = xml``;
registry.category('error_dialogs').add('odoo.addons.fsm.ReasonError', FsmReasonError);

export class FsmAppointmentError extends Component {
    setup() {
        super.setup(...arguments);
        this.action = useService('action');
        const value = this.props.data.arguments?.[1];
        if (!value) {
            console.error('AppointmentError has no action. Nothing to do...');
        }
        this.action.doAction(value);
        this.props.close();
    }
}
FsmAppointmentError.template = xml``;
registry.category('error_dialogs').add('odoo.addons.fsm.AppointmentError', FsmAppointmentError);

export class FsmTaskButton extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.buttonsAll = [];
        this.buttonsReady = false;
        this.isForm = this.env.config.viewType == "form";
        onWillStart(async () => {
            if (!this.buttonsReady) {
                let projectID = 0, taskID = 0;
                if (this.isForm) {
                    taskID = this.env.model.root.resId || 0;
                } else {
                    const controller = this.action.currentController;
                    if (controller) {
                        projectID = controller.action.context.default_project_id;
                    }
                }
                this.buttonsAll = await this.orm.call("fsm.task", "get_buttons", [projectID, taskID]);
                this.buttonsReady = true;
            }
        });
    }

    get buttons() {
        let records;
        if (this.isForm) {
            records = [this.env.model.root];
        } else {
            records = this.env.model.root.selection || [];
        }

        const pairs = new Set();
        for (const record of records) {
            pairs.add(`${record.data.type_id?.id || 0},${record.data.flow_stage_id?.id || 0}`);
        }
        return this.buttonsAll.filter(b => pairs.has(`${b.type},${b.stage}`));
    }

    async onClick(type, stage, button) {
        let records;
        if (this.isForm) {
            records = [this.env.model.root.resId];
        } else {
            records = this.env.model.root.selection.filter(r => r.data.type_id?.id === type && r.data.flow_stage_id?.id === stage).map(r => r.resId);
        }

        document.querySelectorAll('button.btn-fsm-task').forEach(b => b.setAttribute('disabled', 'disabled'));

        const result = await this.orm.call("fsm.task", "run_button", [button, records]);
        if ('action' in result) {
            await this.action.doAction(result.action);
        }

        this.env.bus.trigger('FSM:RELOAD');
    }
}
FsmTaskButton.template = "Fsm.Task.Buttons";

export class FsmTaskImport extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        onWillStart(async () => {
            this.enabled = await user.hasGroup('fsm.group_action_import');
        });
    }

    async onClick() {
        await this.action.doAction('fsm.action_task_import');
        this.env.bus.trigger('FSM:RELOAD');
    }
}
FsmTaskImport.template = "Fsm.Task.Import";

function getFsmTaskController() {
    return {
        setup() {
            super.setup();
            this.orm = useService("orm");
            this.action = useService("action");
            this.notification = useService("notification");
            this.mutex = new Mutex();
            this.barcode = useService("barcode");
            onMounted(() => {
                this.barcode.bus.addEventListener('barcode_scanned', this.onScan.bind(this));
            });
            onWillUnmount(() => {
                this.barcode.bus.removeEventListener('barcode_scanned', this.onScan.bind(this));
            });
        },

        async onScan(payload) {
            // Odoo 19 barcode service emits { barcode, target } in detail or directly
            const barcode = payload.detail?.barcode ?? payload.barcode ?? payload;
            this.mutex.exec(async () => {
                let action = await this.orm.call('fsm.task', 'scan_barcode', [barcode]);
                if (action) {
                    this.action.doAction(action);
                } else {
                    this.notification.add(_t(`No product found with serial ${barcode}`), {
                        title: _t('Error'),
                        type: 'danger',
                        sticky: false,
                    });
                }
            });
        }
    };
}

export class FsmTaskListController extends ListController {
    setup() {
        super.setup();
        this.fsmReload = this.fsmReload.bind(this);
        onMounted(() => {
            this.env.bus.addEventListener("FSM:RELOAD", this.fsmReload);
        });
        onWillUnmount(() => {
            this.env.bus.removeEventListener("FSM:RELOAD", this.fsmReload);
        });
        onWillStart(async () => {
            this.fsmHasArchiveGroup = await user.hasGroup('fsm.group_action_archieve');
            this.isExportEnable = await user.hasGroup('fsm.group_action_export');
            this.archiveEnabled = this.archiveEnabled && this.fsmHasArchiveGroup;
        });
    }

    fsmReload() {
        reload.call(this);
    }
};
FsmTaskListController.components = { ...ListController.components, FsmTaskButton, FsmTaskImport };
patch(FsmTaskListController.prototype, getFsmTaskController());

export class FsmTaskTodoField extends X2ManyField {
    static props = {
        ...X2ManyField.props,
        context: { type: Object, optional: true },
    };
    setup() {
        super.setup();
    }
};

export class FsmTaskTodoListRenderer extends ListRenderer {
    async onCellClicked(record, column, ev) {
        if (column.name === 'done' && record.data.fulfilled) {
            return super.onCellClicked(record, column, ev);
        } else {
            this.props.openRecord(record);
        }
    }
};

FsmTaskTodoField.components = {
    ...X2ManyField.components,
    ListRenderer: FsmTaskTodoListRenderer,
};

export class FsmTaskListRenderer extends ListRenderer {
    setup() {
        super.setup();
    }
};

export const FsmTaskList = {
    ...listView,
    Controller: FsmTaskListController,
    Renderer: FsmTaskListRenderer,
    buttonTemplate: "Fsm.Task.ListView.Buttons",
};

export class FsmTaskKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.fsmReload = this.fsmReload.bind(this);
        onMounted(() => {
            this.env.bus.addEventListener("FSM:RELOAD", this.fsmReload);
        });
        onWillUnmount(() => {
            this.env.bus.removeEventListener("FSM:RELOAD", this.fsmReload);
        });
    }

    fsmReload() {
        reload.call(this);
    }
};
FsmTaskKanbanController.components = { ...KanbanController.components, FsmTaskImport };
patch(FsmTaskKanbanController.prototype, getFsmTaskController());

export class FsmTaskKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
    }
};

export const FsmTaskKanban = {
    ...kanbanView,
    Controller: FsmTaskKanbanController,
    Renderer: FsmTaskKanbanRenderer,
    buttonTemplate: "Fsm.Task.KanbanView.Buttons",
};

export class FsmTaskFormController extends FormController {
    setup() {
        super.setup();
        this.fsmReload = this.fsmReload.bind(this);
        onMounted(() => {
            this.env.bus.addEventListener("FSM:RELOAD", this.fsmReload);
        });
        onWillUnmount(() => {
            this.env.bus.removeEventListener("FSM:RELOAD", this.fsmReload);
        });
        onWillStart(async () => {
            this.fsmHasArchiveGroup = await user.hasGroup('fsm.group_action_archieve');
            this.isExportEnable = await user.hasGroup('fsm.group_action_export');
        });
    }

    get archiveEnabled() {
        return super.archiveEnabled && this.fsmHasArchiveGroup;
    }

    fsmReload() {
        reload.call(this);
    }
};
//FsmTaskFormController.components = { ...FormController.components, FsmTaskButton };


export class FsmTaskFormCompiler extends FormCompiler {
    compileHeader() {
        const res = super.compileHeader(...arguments);
        const buttons = res.querySelector('StatusBarButtons');
        const slot = createElement('t', { 't-set-slot': 'button_99', isVisible: true });
        const button = createElement('FsmTaskButton');
        append(slot, button);
        append(buttons, slot);
        return res;
    }
}
export class FsmTaskFormRenderer extends FormRenderer {
    setup() {
        super.setup();
    }
};
FsmTaskFormRenderer.components = { ...FormRenderer.components, FsmTaskButton };

export const FsmTaskForm = {
    ...formView,
    Controller: FsmTaskFormController,
    Renderer: FsmTaskFormRenderer,
    Compiler: FsmTaskFormCompiler,
    //buttonTemplate: "Fsm.Task.FormView.Buttons",
};

registry.category("fields").add("fsm_task_todo", { component: FsmTaskTodoField });
registry.category("views").add("fsm_task_list", FsmTaskList);
registry.category("views").add("fsm_task_kanban", FsmTaskKanban);
registry.category("views").add("fsm_task_form", FsmTaskForm);

registry.category('action_handlers').add('fsm.reload', ({ env, options }) => {
    env.bus.dispatchEvent(new Event('FSM:RELOAD'));
    env.services.action.doAction({type: 'ir.actions.act_window_close'}, options);
});
registry.category('action_handlers').add('fsm.file', ({ env, action, options }) => {
    env.services.dialog.add(FsmFile, { env, action, options });
});
