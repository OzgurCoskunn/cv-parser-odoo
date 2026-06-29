import { registry } from "@web/core/registry";
import { COMMANDS } from "@barcodes/barcode_handlers";
import { Component, useState, EventBus, onWillStart, useSubEnv, onWillUnmount, onPatched } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { url } from "@web/core/utils/urls";
import { View } from "@web/views/view";
import { utils as uiUtils, SIZES } from "@web/core/ui/ui_service";
import { Mutex } from "@web/core/utils/concurrency";
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { BarcodePickingModel } from "../models/barcode_picking_model";
import { BarcodeQuantModel } from "../models/barcode_quant_model";
import { LineComponent } from "../components/line_component";
import GroupedLineComponent from "../components/grouped_line";
import { BarcodeInput } from "@barcodes/components/manual_barcode";
import { BarcodeVideoScanner, isBarcodeScannerSupported, } from "@web/core/barcode/barcode_video_scanner";
// import { decode, isValidEpcFormat } from "@barcodes_gs1_nomenclature/js/epc_utils";
COMMANDS["OCDMENU"] = () => {}
;
COMMANDS["OCDCANC"] = () => {}
;

const bus = new EventBus();
export class MainComponent extends Component {
    static props = {
        ...standardActionServiceProps
    };
    static template = "barcode_wms.MainComponent";
    static components = {
        BarcodeInput,
        BarcodeVideoScanner,
        Chatter,
        LineComponent,
        GroupedLineComponent,
        View,
    };
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.action = useService("action");
        this.actionMutex = new Mutex();
        this.resModel = this.props.action.res_model;
        this.resId = this.props.action.context.active_id || false;
        const model = this._getModel();
        model.newScrapProduct = this.newScrapProduct.bind(this);
        useSubEnv({
            model,
            dialog: this.dialog,
        });
        this._scrollBehavior = "smooth";
        this.isMobile = uiUtils.isSmall();
        this.state = useState({
            cameraScannedEnabled: false,
            view: "barcodeLines",
            displayNote: false,
            displayCountRFID: false,
            uiBlocked: false,
            barcodesProcessed: 0,
            barcodesToProcess: 0,
            readyToToggleCamera: true,
        });
        this.bufferedBarcodes = [];
        this.receivedRFIDs = [];
        this.totalRFIDs = [];
        this.bufferingTimeout = null;
        this.barcodeService = useService("barcode");
        useBus(this.barcodeService.bus, "barcode_scanned", (ev) => this.onBarcodeScanned(ev.detail.barcode));
        //this.mobileService = useService("mobile");
        //useBus(this.mobileService.bus, "mobile_reader_scanned", (ev) => this.onMobileReaderScanned(ev.detail.data));
        useBus(this.env.model, "flash", this.flashScreen.bind(this));
        useBus(this.env.model, "playSound", this.playSound.bind(this));
        useBus(this.env.model, "blockUI", this.blockUI.bind(this));
        useBus(this.env.model, "unblockUI", this.unblockUI.bind(this));
        useBus(this.env.model, "addBarcodesCountToProcess", (ev) => this.addBarcodesCountToProcess(ev.detail));
        useBus(this.env.model, "updateBarcodesCountProcessed", this.updateBarcodesCountProcessed.bind(this));
        useBus(this.env.model, "clearBarcodesCountProcessed", this.clearBarcodesCountProcessed.bind(this));
        useBus(bus, "refresh", (ev) => this._onRefreshState(ev.detail));
        onWillStart( () => this.onWillStart());
        onWillUnmount( () => {
            clearTimeout(this.bufferingTimeout);
        }
        );
        onPatched( () => {
            this._scrollToSelectedLine();
        }
        );
        onWillUnmount( () => {
            this.env.model._onExit();
        }
        );
    }
    addBarcodesCountToProcess(count) {
        this.state.barcodesToProcess += count;
        if (this.state.barcodesToProcess > this.state.barcodesProcessed) {
            this.updateBarcodesCountMessage();
            this.blockUI();
        }
    }
    updateBarcodesCountProcessed() {
        this.state.barcodesProcessed++;
        this.updateBarcodesCountMessage();
        if (this.state.barcodesProcessed >= this.state.barcodesToProcess) {
            this.clearBarcodesCountProcessed();
        }
    }
    clearBarcodesCountProcessed() {
        this.state.barcodesProcessed = 0;
        this.state.barcodesToProcess = 0;
        this.unblockUI();
    }
    updateBarcodesCountMessage() {
        this.blockUIMessage = _t("Processing %(processed)s/%(toProcess)s barcodes", {
            processed: this.state.barcodesProcessed,
            toProcess: this.state.barcodesToProcess,
        });
    }
    blockUI(ev) {
        this.state.uiBlocked = true;
    }
    unblockUI() {
        this.state.uiBlocked = false;
        this.render(true);
    }
    playSound(ev) {
        if (!this.config.play_sound || this.state.uiBlocked) {
            return;
        }
        const type = ev.detail || "notify";
        this.sounds[type].currentTime = 0;
        this.sounds[type].play().catch( (error) => {
            this.config.play_sound = false;
            console.warn(error);
        }
        );
    }
    get highlightValidateButton() {
        return this.env.model.highlightValidateButton;
    }
    async onWillStart() {
        const barcodeData = await rpc("/barcode_wms/get_barcode_data", {
            model: this.resModel,
            res_id: this.resId,
        });
        barcodeData.actionId = this.props.action.context.active_id;
        this.config = {
            play_sound: true,
            ...barcodeData.data.config
        };
        if (this.config.play_sound) {
            const fileExtension = new Audio().canPlayType("audio/ogg; codecs=vorbis") ? "ogg" : "mp3";
            this.sounds = {
                error: new Audio(url(`/barcodes/static/src/audio/error.${fileExtension}`)),
                notify: new Audio(url(`/mail/static/src/audio/ting.${fileExtension}`)),
                success: new Audio(url(`/barcode_wms/static/src/audio/success.${fileExtension}`)),
            };
            this.sounds.error.load();
            this.sounds.notify.load();
            this.sounds.success.load();
        }
        this.setupCameraScanner();
        this.groups = barcodeData.groups;
        this.env.model.setData(barcodeData);
        this.state.displayNote = Boolean(this.env.model.record.note);
        this.env.model.addEventListener("process-action", this._onDoAction.bind(this));
        this.env.model.addEventListener("refresh", (ev) => this._onRefreshState(ev.detail));
        this.env.model.addEventListener("update", () => {
            if (!this.state.uiBlocked) {
                this.render(true);
            }
        }
        );
        this.env.model.addEventListener("history-back", () => this._exit());
    }
    get isTransfer() {
        return this.currentSourceLocation && this.currentDestinationLocation;
    }
    get lineFormViewProps() {
        return {
            resId: this._editedLineParams && this._editedLineParams.currentId,
            resModel: this.env.model.lineModel,
            context: this.env.model._getNewLineDefaultContext(),
            viewId: this.env.model.lineFormViewId,
            display: {
                controlPanel: false
            },
            type: "form",
            onSave: (record) => this.saveFormView(record),
            onDiscard: () => this.toggleBarcodeLines(),
        };
    }
    get lines() {
        return this.env.model.groupedLines;
    }
    get packageLines() {
        return this.env.model.packageLines;
    }
    get addLineBtnName() {
        return _t("Add Product");
    }
    get displayActionButtons() {
        return this.state.view === "barcodeLines" && this.env.model.canBeProcessed;
    }
    _getBarcodeModel() {
        if (this.resModel === "stock.picking") {
            return BarcodePickingModel;
        } else if (this.resModel === "stock.quant") {
            return BarcodeQuantModel;
        }
        // Fallback or explicit check
        return BarcodePickingModel;
    }
    _getModel() {
        const services = {
            rpc: rpc,
            orm: this.orm,
            notification: this.notification,
            action: this.action,
        };
        const BarcodeModel = this._getBarcodeModel();
        return new BarcodeModel(this.resModel,this.resId,services);
    }
    toggleCameraScanner() {
        if (!this.state.cameraScannedEnabled) {
            this.state.cameraScannedEnabled = true;
            this.state.readyToToggleCamera = false;
        } else if (this.state.readyToToggleCamera) {
            this.state.cameraScannedEnabled = false;
        }
    }
    setupCameraScanner() {
        this.cameraScannerSupported = isBarcodeScannerSupported();
        this.barcodeVideoScannerProps = {
            delayBetweenScan: this.config.delay_between_scan || 2000,
            facingMode: "environment",
            onResult: (barcode) => this.onBarcodeScanned(barcode),
            onError: (error) => {
                this.state.cameraScannedEnabled = false;
                const message = error.message;
                this.notification.add(message, {
                    type: "warning"
                });
            }
            ,
            onReady: () => {
                this.state.readyToToggleCamera = true;
            }
            ,
            cssClass: "o_barcode_wms_camera_video",
        };
    }
    get cameraScannerClassState() {
        if (!this.state.readyToToggleCamera) {
            return "bg-secondary";
        }
        return this.state.cameraScannedEnabled ? "bg-success text-white" : "text-primary";
    }
    async cancel() {
        await this.env.model.save();
        const action = await this.orm.call(this.resModel, "action_cancel_from_barcode", [[this.resId], ]);
        const onClose = (res) => {
            if (res && res.cancelled) {
                this.env.model._cancelNotification();
                this._exit();
            }
        }
        ;
        this.action.doAction(action, {
            onClose: onClose.bind(this),
        });
    }
    onBarcodeScanned(barcode) {
        if (this.state.view !== "barcodeLines") {
            return;
        }
        if (barcode) {
            this.actionMutex.exec(async () => this.env.model.processBarcode(barcode));
            if ("vibrate"in window.navigator) {
                window.navigator.vibrate(100);
            }
        } else {
            const message = _t("Please, Scan again!");
            this.env.services.notification.add(message, {
                type: "warning"
            });
        }
    }
    onMobileReaderScanned(data) {
        this.receivedRFIDs.push(...data);
        this.totalRFIDs.push(...data);
        this.state.displayCountRFID = true;
        if (this.RFIDCountTimeout) {
            clearTimeout(this.RFIDCountTimeout);
        }
        this.RFIDCountTimeout = setTimeout( () => this.closeRFIDCount(), 5000);
        if (!this.bufferingTimeout) {
            this.bufferingTimeout = setTimeout(this._onMobileReaderScanned.bind(this), this.config.barcode_rfid_batch_time);
        }
        this.bufferedBarcodes = this.bufferedBarcodes.concat(data);
    }
    async _onMobileReaderScanned(ev) {
        await this.env.model.processBarcode(this.bufferedBarcodes.join(","), {
            readingRFID: true
        });
        this.bufferedBarcodes = [];
        clearTimeout(this.bufferingTimeout);
        this.bufferingTimeout = null;
    }
    closeRFIDCount() {
        if (this.RFIDCountTimeout) {
            clearTimeout(this.RFIDCountTimeout);
        }
        this.state.displayCountRFID = false;
        this.receivedRFIDs = [];
    }
    onBarcodeSubmitted(barcode) {
        this.changeView("barcodeLines");
        barcode = this.env.model.cleanBarcode(barcode);
        this.onBarcodeScanned(barcode);
    }
    async exit(ev) {
        this.state.cameraScannedEnabled = false;
        if (this.state.view === "barcodeLines") {
            await this.env.model.beforeQuit();
            this._exit();
        } else {
            this.toggleBarcodeLines();
        }
    }
    _exit() {
        const {breadcrumbs} = this.env.config;
        if (breadcrumbs.length === 1) {
            this.action.doAction("barcode_wms.barcode_wms_action_main_menu");
        } else {
            const previousPath = breadcrumbs[breadcrumbs.length - 2].url.split("/");
            if (isNaN(previousPath[previousPath.length - 1])) {
                this.env.config.historyBack();
            } else {
                history.back();
            }
        }
    }
    flashScreen() {
        if (this.state.uiBlocked) {
            return;
        }
        const clientAction = document.querySelector(".o_barcode_client_action");
        clientAction.style.animation = "none";
        clientAction.offsetHeight;
        clientAction.style.animation = null;
        clientAction.classList.add("o_white_flash");
    }
    putInPack(ev) {
        ev.stopPropagation();
        this.env.model._putInPack();
    }
    returnProducts(ev) {
        ev.stopPropagation();
        this.env.model._returnProducts();
    }
    saveFormView(lineRecord) {
        const lineId = (lineRecord && lineRecord.resId) || (this._editedLineParams && this._editedLineParams.currentId);
        const recordId = lineRecord.resModel === this.resModel ? lineId : undefined;
        this._onRefreshState({
            recordId,
            lineId
        });
    }
    changeView(view) {
        this.state.cameraScannedEnabled = false;
        this.state.view = view;
    }
    async toggleBarcodeLines(lineId) {
        await this.env.model.displayBarcodeLines(lineId);
        this._editedLineParams = undefined;
        this.changeView("barcodeLines");
    }
    async toggleInformation() {
        if (this.env.model.formViewId) {
            if (this.state.view === "infoFormView") {
                this.changeView("barcodeLines");
            } else {
                await this.env.model.save();
                this.changeView("infoFormView");
            }
        }
    }
    async validate(ev) {
        ev.stopPropagation();
        await this.env.model.validate();
    }
    _getHeaderHeight() {
        const header = document.querySelector(".o_barcode_header");
        const navbar = document.querySelector(".o_main_navbar");
        return navbar ? navbar.offsetHeight + header.offsetHeight : header.offsetHeight;
    }
    _scrollToSelectedLine() {
        if (!this.state.view === "barcodeLines" && this.env.model.canBeProcessed) {
            this._scrollBehavior = "auto";
            return;
        }
        let targetElement = false;
        let selectedLine = document.querySelector(".o_sublines .o_barcode_line.o_highlight");
        const isSubline = Boolean(selectedLine);
        if (!selectedLine) {
            selectedLine = document.querySelector(".o_barcode_line.o_highlight");
        }
        let locationLine = false;
        if (this.env.model.lastScanned.sourceLocation) {
            const locId = this.env.model.lastScanned.sourceLocation.id;
            locationLine = document.querySelector(`.o_barcode_location_line[data-location-id="${locId}"]`);
        } else if (selectedLine) {
            locationLine = selectedLine.closest(".o_barcode_location_group").querySelector(".o_barcode_location_line");
        }
        targetElement = selectedLine || (locationLine && locationLine.parentElement);
        if (targetElement) {
            const elRect = targetElement.getBoundingClientRect();
            const page = document.querySelector(".o_barcode_lines");
            const headerHeight = this._getHeaderHeight();
            if (elRect.top < headerHeight || elRect.bottom > headerHeight + elRect.height) {
                let top = elRect.top - headerHeight + page.scrollTop;
                if (isSubline) {
                    const parentLine = targetElement.closest(".o_sublines").closest(".o_barcode_line");
                    const parentSummary = parentLine.querySelector(".o_barcode_line_summary");
                    top -= parentSummary.getBoundingClientRect().height;
                } else if (selectedLine && locationLine) {
                    top -= locationLine.getBoundingClientRect().height;
                }
                page.scroll({
                    left: 0,
                    top,
                    behavior: this._scrollBehavior
                });
                this._scrollBehavior = "smooth";
            }
        }
    }
    async _onDoAction(ev) {
        this.action.doAction(ev.detail, {
            onClose: this._onRefreshState.bind(this),
        });
    }
    onOpenPackage(packageIds) {
        this._inspectedPackageIds = packageIds;
        this.changeView("packagePage");
    }
    async newScrapProduct() {
        await this.env.model.save();
        this.changeView("scrapProductPage");
    }
    get displayOperationButtons() {
        const {model} = this.env;
        return (model.canScrap || model.displayCancelButton || model.displaySignatureButton || model.displayReturnButton);
    }
    get scrapViewProps() {
        const context = this.env.model.scrapContext;
        return {
            resModel: "stock.scrap",
            context: context,
            viewId: this.env.model.scrapViewId,
            display: {
                controlPanel: false
            },
            type: "form",
            onSave: () => this.toggleBarcodeLines(),
            onDiscard: () => this.toggleBarcodeLines(),
        };
    }
    async onOpenProductPage(line) {
        await this.env.model.save();
        if (line) {
            const virtualId = line.virtual_id;
            if (!line.id && virtualId) {
                line = this.env.model.pageLines.find( (l) => l.dummy_id === virtualId);
            }
            this._editedLineParams = this.env.model.getEditedLineParams(line);
        }
        this.changeView("productPage");
    }
    async _onRefreshState(paramsRefresh) {
        const {recordId, lineId} = paramsRefresh || {};
        const {route, params} = this.env.model.getActionRefresh(recordId);
        await this.actionMutex.exec(async () => {
            const result = await rpc(route, params);
            await this.env.model.refreshCache(result.data.records);
            await this.toggleBarcodeLines(lineId);
            this.render();
        }
        );
    }
    _onWarning(ev) {
        const {title, message} = ev.detail;
        this.env.services.dialog.add(ConfirmationDialog, {
            title,
            body: message
        });
    }
}

registry.category("actions").add("barcode_wms_client_action", MainComponent);
