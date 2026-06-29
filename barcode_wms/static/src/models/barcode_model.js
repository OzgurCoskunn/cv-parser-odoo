/** @odoo-module **/

import { EventBus } from "@odoo/owl";
import { LazyBarcodeCache } from "./lazy_barcode_cache";
import { _t } from "@web/core/l10n/translation";
import { BarcodeParser } from "@barcodes/js/barcode_parser";
import { Mutex } from "@web/core/utils/concurrency";
import { formatFloat } from "@web/core/utils/numbers";
import { appTranslateFn } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc"
import { useService } from "@web/core/utils/hooks"
import { FNC1_CHAR } from "@barcodes_gs1_nomenclature/js/barcode_parser"
import { BarcodeObject } from "./barcode_object";

// Simplified BarcodeModel
export class BarcodeModel extends EventBus {
    constructor(resModel, resId, services) {
        super();
        this.dialogService = useService("dialog");
        this.orm = services.orm;
        this.notificationService = services.notification;
        this.action = services.action;
        this.resId = resId;
        this.resModel = resModel;
        this.unfoldLineKey = false;
        this.currentSortIndex = 0;
        this.validateContext = {};
        this.scanHistory = [];
        this.lastScanned = {
            packageId: false,
            product: false,
            sourceLocation: false
        };
        this._currentLocation = false;
        this.needSourceConfirmation = false;
        this.useTrackingNumber = true;
        this.uriCache = new Set();
        this.notificationCache = new Set();
    }

    setData(data) {
        this.actionId = data.actionId;
        this.cache = new LazyBarcodeCache(data.data.records);
        const nomenclature = this.cache.getRecord("barcode.nomenclature", data.data.nomenclature_id);
        nomenclature.rules = [];
        for (const ruleId of nomenclature.rule_ids) {
            nomenclature.rules.push(this.cache.getRecord("barcode.rule", ruleId));
        }
        this.parser = new BarcodeParser({
            nomenclature
        });
        BarcodeObject.setEnv(this.cache, this.parser);
        this.scannedLinesVirtualId = [];
        this.actionMutex = new Mutex();
        this.config = data.data.config || {};
        this.groups = data.groups;
        this.groupingLinesEnabled = this.groups.group_production_lot;
        this.packageTypes = [];
        if (this.groups.group_tracking_lot) {
            const packageTypes = this.cache.dbBarcodeCache["stock.package.type"] || {};
            for (const [barcode,ids] of Object.entries(packageTypes)) {
                this.packageTypes.push([barcode, ids[0]]);
            }
        }
        this._createState();
        this.linesToSave = [];
        this.selectedLineVirtualId = false;
        this.name = this._getName();
        this.commands = this._getCommands();
    }

    getQtyDone(line) {
        throw new Error("Not Implemented");
    }

    getQtyDemand(line) {
        throw new Error("Not Implemented");
    }

    getDisplayCompletePackageBtn(line) {
        return false;
    }

    getDisplayIncrementBtn(line) {
        return true;
    }

    getActionRefresh(newId) {
        return {
            route: "/barcode_wms/get_barcode_data",
            params: {
                model: this.resModel,
                res_id: this.resId || false
            },
        };
    }

    getIncrementQuantity(line) {
        const remainingQty = this.getLineRemainingQuantity(line);
        const params = {
            digits: [false, this.precision],
            thousandsSep: "",
            decimalPoint: "."
        };
        return parseFloat(formatFloat(remainingQty, params));
    }

    getLineRemainingQuantity(line) {
        return this.getQtyDemand(line) ? this.getQtyDemand(line) - this.getQtyDone(line) : 0;
    }

    getlotName(line) {
        return (line.lot_id && line.lot_id.name) || line.lot_name || false;
    }

    getEditedLineParams(line) {
        return {
            currentId: line.id
        };
    }

    async apply() {
        throw new Error("Not Implemented");
    }

    getDisplayIncrementBtnForSerial(line) {
        return !(line.lot_id || line.lot_name) || this.getQtyDone(line) === 0;
    }

    _getName() {
        return this.cache.getRecord(this.resModel, this.resId).name;
    }

     get barcodeInfo() {
        throw new Error("Not Implemented");
    }

    get canCreateNewLot() {
        return true;
    }

    get canBeProcessed() {
        return true;
    }

    get canBeValidate() {
        return this.pageLines.length + this.packageLines.length;
    }

    get canSelectLocation() {
        return true;
    }

    get cancelLabel() {
        return _t("Cancel");
    }

    get groupedLinesByLocation() {
        const lines = [].concat(this.groupedLines, this.packageLines);
        const linesByLocations = [];
        const linesByLocation = {};
        for (const line of lines) {
            const lineLoc = this.getLineLocation(line);
            if (!linesByLocation[lineLoc.id]) {
                linesByLocation[lineLoc.id] = {
                    location: lineLoc,
                    lines: [],
                };
            }
            if (!linesByLocations.includes(linesByLocation[lineLoc.id])) {
                linesByLocations.push(linesByLocation[lineLoc.id]);
            }
            linesByLocation[lineLoc.id].lines.push(line);
        }
        linesByLocations.sort( (lblA, lblB) => {
            const [locNameA,locNameB] = [lblA.location.display_name, lblB.location.display_name];
            return locNameA < locNameB ? -1 : locNameA > locNameB ? 1 : 0;
        }
        );
        return linesByLocations;
    }

    // === Line Data Management ===

    _createState() {
        this.record = this._getModelRecord();
        const lines = this._createLinesState();
        lines.sort(this._sortingMethod.bind(this));
        for (const line of lines) {
            line.sortIndex = this._getLineIndex();
        }
        this.initialState = {
            lines
        };
        this.currentState = JSON.parse(JSON.stringify(this.initialState));
        this.groupLines();
    }
    
    groupLines() {
        this._groupedLines = [...this.pageLines];
        if (this.groupingLinesEnabled) {
            this._groupedLines = this._groupLines(this._groupedLines, "parentLine", this.groupKey);
        }
        return this._groupedLines;
    }

    lineCannotBeGrouped(line) {
        return line.product_id.tracking === "none" || line.lines;
    }

    get groupedLines() {
        this.groupLines();
        return this._sortLine(this._groupedLines);
    }

    _groupLines(lines, parentKeyString, groupKeyMethod, conditionalGrouping=true) {
        const groupedLinesByKey = {};
        for (let index = lines.length - 1; index >= 0; index--) {
            const line = lines[index];
            if (line[parentKeyString]) {
                delete line[parentKeyString];
            }
            if (conditionalGrouping && this.lineCannotBeGrouped(line)) {
                continue;
            }
            const key = groupKeyMethod.call(this, line);
            if (!groupedLinesByKey[key]) {
                groupedLinesByKey[key] = [];
            }
            groupedLinesByKey[key].push(...lines.splice(index, 1));
        }
        for (const sublines of Object.values(groupedLinesByKey)) {
            if (sublines.length === 1) {
                lines.push(...sublines);
                continue;
            }
            const groupedLine = this._groupSublines(sublines, parentKeyString);
            lines.push(groupedLine);
        }
        return lines;
    }

    getLineLocation(line) {
        return line.location_id;
    }

    groupKey(line) {
        return `${line.product_id.id}_${line.location_id.id}`;
    }

    _getPrintOptions() {
        return {};
    }

    _getCompanyId() {
        throw new Error("Not Implemented");
    }

    zeroQtyClass(_line) {
        return "text-muted";
    }
    
    _onExit() {
        return;
    }

    get pageLines() {
        return this.currentState.lines;
    }

    get packageLines() {
        return [];
    }
    
    get displaySourceLocation() {
        return this.groups.group_stock_multi_locations;
    }

    get previousScannedLines() {
        const lines = [];
        const alreadyDone = [];
        for (const virtualId of this.scannedLinesVirtualId) {
            if (alreadyDone.includes(virtualId)) {
                continue;
            }
            alreadyDone.push(virtualId);
            const foundLine = this.currentState.lines.find( (l) => l.virtual_id === virtualId);
            if (foundLine) {
                lines.push(foundLine);
            }
        }
        if (this.groups.group_stock_packaging) {
            lines.push(...this.previousScannedLinesByPackage);
        }
        return lines;
    }

    get previousScannedLinesByPackage() {
        if (this.lastScanned.packageId) {
            return this.currentState.lines.filter( (l) => l.package_id && l.package_id.id === this.lastScanned.packageId);
        }
        return [];
    }
    
    get displayAddProductButton() {
        return true;
    }

    get useScanSourceLocation() {
        return this.displaySourceLocation;
    }

    get displayValidateButton() {
        return true;
    }
    
    get validateButtonLabel() {
        return _t("Validate");
    }

    async displayBarcodeLines(lineId) {
        if (lineId) {
            const res = await this.orm.search(this.lineModel, [["id", "=", lineId]]);
            if (!res.length) {
                const lineIndex = this.currentState.lines.findIndex( (l) => l.id == lineId);
                this.currentState.lines.splice(lineIndex, 1);
            } else {
                const line = this.currentState.lines.find( (line) => line.id === lineId);
                this.selectLine(line);
            }
        }
    }

    completePackage(line) {
        throw new Error("Not Implemented");
    }

    findLineForCurrentLocation() {
        if (!this.lastScanned.sourceLocation) {
            return false;
        }
        let foundLine = false;
        for (const line of this.pageLines) {
            if (line.location_id.id != this.lastScanned.sourceLocation.id) {
                continue;
            }
            const [qtyDone,qtyDemand] = [this.getQtyDone(line), this.getQtyDemand(line)];
            if (qtyDone == 0 || (qtyDemand && qtyDone < qtyDemand)) {
                return line.lot_id ? this._getParentLine(line) : line;
            }
            foundLine = !foundLine || qtyDone < this.getQtyDone(foundLine) ? line : foundLine;
        }
        return foundLine.lot_id ? this._getParentLine(foundLine) : foundLine;
    }

    notification(message, options={}) {
        if (this.notificationCache.has(message)) {
            return;
        }
        this.notificationCache.add(message);
        if (options.type === "danger") {
            this.trigger("playSound", "error");
        }
        return this.notificationService.add(message, options);
    }

    async refreshCache(records) {
        this.cache.setCache(records);
        this._createState();
    }

    get canPutInPack() {
        return true;
    }
    
    get displayApplyButton() {
        return false;
    }

    get applyOn() {
        return 0;
    }

    get displayReturnButton() {
        return false;
    }

    get useScanDestinationLocation() {
        return this.displayDestinationLocation;
    }

    get displayPutInPackButton() {
        return true;
    }

    get displaySignatureButton() {
        return false;
    }

    get canScrap() {
        return false;
    }
    
    get displayCancelButton() {
        return true;
    }

    openSignatureDialog() {
        console.log("Open Signature");
    }
    
    async print(action, method) {
        await this.save();
        const options = this._getPrintOptions();
        if (options.warning) {
            return this.notification(options.warning, {
                type: "warning"
            });
        }
        if (!action && method) {
            action = await this.orm.call(this.resModel, method, [[this.resId]]);
        }
        this.action.doAction(action, options);
    }

    async _processGs1Data(data, filters) {
        const result = {};
        const {rule, type, value} = data;
        if (["location", "location_dest"].includes(type)) {
            const location = await this.cache.getRecordByBarcode(value, "stock.location");
            if (!location) {
                return;
            } else {
                result.location = location;
                result.match = true;
            }
        } else if (type === "lot") {
            if (this.useExistingLots) {
                result.lot = await this.cache.getRecordByBarcode(value, "stock.lot", {
                    filters
                });
            }
            if (!result.lot) {
                result.lotName = value;
            }
            if (result.lot || result.lotName) {
                result.match = true;
            }
        } else if (type === "package") {
            const stockPackage = await this.cache.getRecordByBarcode(value, "stock.package");
            if (stockPackage) {
                result.package = stockPackage;
            } else {
                result.packageName = value;
            }
            result.match = true;
        } else if (type === "package_type") {
            const packageType = await this.cache.getRecordByBarcode(value, "stock.package.type");
            if (packageType) {
                result.packageType = packageType;
                result.match = true;
            } else {
                const message = _t("An unexisting package type was scanned. This part of the barcode can't be processed.");
                this.notification(message, {
                    type: "warning"
                });
            }
        } else if (type === "product") {
            const product = await this.cache.getRecordByBarcode(value, "product.product");
            if (product) {
                result.product = product;
                result.match = true;
            } else if (this.groups.group_uom) {
                const packaging = await this.cache.getRecordByBarcode(value, "product.uom");
                if (packaging) {
                    result.packaging = packaging;
                    result.match = true;
                }
            }
        } else if (type === "quantity") {
            result.quantity = value;
            if (this.groups.group_uom && rule?.associated_uom_id) {
                result.uom = await this.cache.getRecord("uom.uom", rule.associated_uom_id);
            }
            result.match = result.quantity ? true : false;
        }
        return result;
    }

    async _processBarcode(barcode) {
        let barcodeData = {};
        let currentLine = false;
        const filters = {};
        if (this.selectedLine && this.selectedLine.product_id.tracking !== "none") {
            filters["stock.lot"] = {
                product_id: this.selectedLine.product_id.id,
            };
        }
        filters["all"] = {
            company_id: [false].concat(this._getCompanyId() || []),
        };
        try {
            barcodeData = await this._parseBarcode(barcode, filters);
            if (this._shouldSearchForAnotherLot(barcodeData, filters)) {
                const lot = await this.cache.getRecordByBarcode(barcode, "stock.lot");
                if (lot) {
                    Object.assign(barcodeData, {
                        lot,
                        match: true
                    });
                }
            }
        } catch (parseErrorMessage) {
            barcodeData.error = parseErrorMessage;
        }
        this.scanHistory.unshift(barcodeData);
        if (barcodeData.match) {
            this.trigger("flash");
        }
        if (barcodeData.action) {
            return await barcodeData.action();
        }
        if (barcodeData.packaging) {
            Object.assign(barcodeData, this._retrievePackagingData(barcodeData));
        }
        const check = this._checkBarcode(barcodeData);
        if (check.error) {
            return this.notification(check.message, {
                title: check.title,
                type: "danger"
            });
        }
        if (barcodeData.product) {
            this.lastScanned.product = barcodeData.product;
        }
        if (barcodeData.lot && !barcodeData.product) {
            Object.assign(barcodeData, this._retrieveTrackingNumberInfo(barcodeData.lot));
        }
        await this._processLocation(barcodeData);
        await this._processPackage(barcodeData);
        if (barcodeData.stopped) {
            return;
        }
        if (barcodeData.weight) {
            barcodeData.quantity = barcodeData.weight.value;
        }
        if (!barcodeData.product) {
            if (barcodeData.quantity) {
                currentLine = this.selectedLine || this.lastScannedLine;
            } else if (this.selectedLine && this.selectedLine.product_id.tracking !== "none") {
                currentLine = this.selectedLine;
            } else if (this.lastScannedLine && this.lastScannedLine.product_id.tracking !== "none") {
                currentLine = this.lastScannedLine;
            }
            if (currentLine) {
                const previousProduct = currentLine.product_id;
                if (previousProduct.tracking !== "none" && !barcodeData.match && this.canCreateNewLot) {
                    this.trigger("flash");
                    barcodeData.lotName = barcode;
                    barcodeData.product = previousProduct;
                }
                if (barcodeData.lot || barcodeData.lotName || barcodeData.quantity) {
                    barcodeData.product = previousProduct;
                }
            }
        }
        let {product} = barcodeData;
        if (!product && barcodeData.match && this.parser.nomenclature.is_gs1_nomenclature) {
            barcodeData = await this._fetchRecordFromTheCache(barcode, filters);
            if (barcodeData.packaging) {
                Object.assign(barcodeData, this._retrievePackagingData(barcodeData));
            } else if (barcodeData.lot) {
                Object.assign(barcodeData, this._retrieveTrackingNumberInfo(barcodeData.lot));
            }
            if (barcodeData.product) {
                product = barcodeData.product;
            } else if (barcodeData.match) {
                await this._processPackage(barcodeData);
                if (barcodeData.stopped) {
                    return;
                }
            }
        }
        if (!product) {
            return this.noProductToast(barcodeData);
        } else if (barcodeData.lot && barcodeData.lot.product_id !== product.id) {
            delete barcodeData.lot;
        }
        if (barcodeData.weight) {
            barcodeData.uom = this.cache.getRecord("uom.uom", product.uom_id);
        }
        if (!currentLine || this._shouldSearchForAnotherLine(currentLine, barcodeData)) {
            currentLine = this._findLine(barcodeData);
        }
        if (product.tracking === "none" || barcodeData.lot || barcodeData.lotName || this._incrementTrackedLine()) {
            const hasUnassignedQty = currentLine && currentLine.qty_done && !currentLine.lot_id && !currentLine.lot_name;
            const isTrackingNumber = barcodeData.lot || barcodeData.lotName;
            const defaultQuantity = isTrackingNumber && hasUnassignedQty ? 0 : 1;
            barcodeData.quantity = barcodeData.quantity || defaultQuantity;
            if (product.tracking === "serial" && barcodeData.quantity > 1 && (barcodeData.lot || barcodeData.lotName)) {
                barcodeData.quantity = 1;
                this.notification(_t(`A product tracked by serial numbers can't have multiple quantities for the same serial number.`), {
                    type: "danger"
                });
            }
        }
        if ((barcodeData.lotName || barcodeData.lot) && product) {
            const lotName = barcodeData.lotName || barcodeData.lot.name;
            for (const line of this.currentState.lines) {
                if (line.product_id.id !== product.id) {
                    continue;
                }
                if (line.product_id.tracking === "serial" && this.getQtyDone(line) !== 0 && this.getlotName(line) === lotName) {
                    return this.notification(_t("The scanned serial number %s is already used.", lotName), {
                        type: "danger"
                    });
                }
            }
            const prefilledOwner = (!currentLine || (currentLine && !currentLine.owner_id)) && this.groups.group_tracking_owner && !barcodeData.owner;
            const prefilledPackage = (!currentLine || (currentLine && !currentLine.package_id)) && this.groups.group_tracking_lot && !barcodeData.package;
            if (this.useExistingLots && (prefilledOwner || prefilledPackage)) {
                const lotId = (barcodeData.lot && barcodeData.lot.id) || (currentLine && currentLine.lot_id && currentLine.lot_id.id) || false;
                const locationId = (currentLine && currentLine.location_id && currentLine.location_id.id) || false;
                const params = {
                    lot_id: lotId,
                    lot_name: (!lotId && barcodeData.lotName) || false,
                };
                let quants = await this.cache.getQuants(product, locationId, params);
                if (quants.length && quants.length > 1 && (prefilledPackage || prefilledOwner)) {
                    const filteredQuants = quants.filter( (quant) => quant.package_id || quant.owner_id);
                    quants = filteredQuants.length ? filteredQuants : quants;
                }
                if (quants && quants.length === 1) {
                    const quant = quants[0];
                    if (prefilledPackage && quant.package_id) {
                        barcodeData.package = this.cache.getRecord("stock.package", quant.package_id);
                    }
                    if (prefilledOwner && quant.owner_id) {
                        barcodeData.owner = this.cache.getRecord("res.partner", quant.owner_id);
                    }
                }
            }
        }
        const barcodeDataUom = this.cache.getRecord("uom.uom", barcodeData.uom ? barcodeData.uom.id : barcodeData.product?.uom_id);
        const expressedInPackagingUom = currentLine && barcodeDataUom && barcodeDataUom.id !== currentLine.product_uom_id.id;
        if (expressedInPackagingUom) {
            if (!this._lineIsNotComplete(currentLine)) {
                currentLine = false;
            } else {
                barcodeData.quantity = (barcodeData.quantity * barcodeDataUom.factor) / currentLine.product_uom_id.factor;
                barcodeData.uom = currentLine.product_uom_id;
            }
        }
        if (currentLine) {
            let exceedingQuantity = 0;
            if (currentLine.reserved_uom_qty && product.tracking === "none") {
                const remainingQty = currentLine.reserved_uom_qty - currentLine.qty_done;
                if (barcodeData.quantity > remainingQty && this._shouldCreateLineOnExceed(currentLine)) {
                    exceedingQuantity = parseFloat(formatFloat(barcodeData.quantity - remainingQty, {
                        digits: [false, this.precision],
                    }));
                    barcodeData.quantity = remainingQty;
                }
            }
            if (barcodeData.quantity > 0 || barcodeData.lot || barcodeData.lotName) {
                const fieldsParams = this._convertDataToFieldsParams(barcodeData);
                if (barcodeData.uom) {
                    fieldsParams.uom = barcodeData.uom;
                }
                await this.updateLine(currentLine, fieldsParams);
                this.trigger("playSound", "success");
            }
            if (exceedingQuantity) {
                barcodeData.quantity = exceedingQuantity;
                const fieldsParams = this._convertDataToFieldsParams(barcodeData);
                if (barcodeData.uom) {
                    fieldsParams.uom = barcodeData.uom;
                }
                currentLine = await this._createNewLine({
                    copyOf: currentLine,
                    fieldsParams,
                });
                if (expressedInPackagingUom) {
                    currentLine.packaging_uom_id = undefined;
                    currentLine.packaging_uom_qty = 0;
                }
            }
        } else {
            const fieldsParams = this._convertDataToFieldsParams(barcodeData);
            if (barcodeData.uom) {
                fieldsParams.uom = barcodeData.uom;
            }
            if (this.createSingleLinesForPackaging(barcodeData)) {
                const productUoM = await this.cache.getRecord("uom.uom", barcodeData.product.uom_id);
                const qtyUoM = barcodeData.uom;
                let {quantity} = barcodeData;
                if (productUoM.factor !== qtyUoM.factor) {
                    quantity *= qtyUoM.factor / productUoM.factor;
                    fieldsParams.uom = productUoM;
                }
                for (let lineCount = 0; lineCount < quantity; lineCount++) {
                    currentLine = await this.createNewLine({
                        fieldsParams
                    });
                }
            } else {
                currentLine = await this.createNewLine({
                    fieldsParams
                });
            }
            if (currentLine) {
                this.trigger("playSound", "success");
            }
        }
        if (currentLine) {
            this._selectLine(currentLine);
        }
        const matchedURI = barcode.match(/^urn:.*$/);
        if (matchedURI) {
            this.uriCache.add(barcode);
        }
        this.trigger("update");
    }

    noProductToast(barcodeData) {
        if (!barcodeData.error) {
            if (this.groups.group_tracking_lot) {
                barcodeData.error = _t("You are expected to scan one or more products or a package available at the picking location");
            } else {
                barcodeData.error = _t("This product doesn't exist.");
            }
        }
        return this.notification(barcodeData.error, {
            type: "danger"
        });
    }

    async _processLocation(barcodeData) {
        if (barcodeData.location) {
            await this._processLocationSource(barcodeData);
            this.trigger("playSound", "success");
            this.trigger("update");
        }
    }

    async _processLocationSource(barcodeData) {
        this.location = barcodeData.location;
        barcodeData.stopped = true;
        this.selectedLineVirtualId = false;
        this.lastScanned.packageId = false;
    }

    async _processPackage(barcodeData) {
        throw new Error("Not Implemented");
    }

    cleanBarcode(barcode) {
        if (this.parser.nomenclature.is_gs1_nomenclature) {
            barcode = barcode.replace(/[( ]([0-9]+)[)]/g, `${FNC1_CHAR}$1`);
            if (barcode[0] === FNC1_CHAR) {
                barcode = barcode.slice(1, barcode.length);
            }
        }
        return barcode;
    }

    lineCanBeSelected() {
        return true;
    }
    
    get printButtons() {
        throw new Error("Not Implemented");
    }

    get recordIds() {
        return [this.resId];
    }

    async processBarcode(barcode, options={}) {
        if (!barcode) {
            return;
        }
        const {readingRFID} = options;
        const barcodes = this.splitBarcode(barcode);
        if (barcodes.length > 1 && barcode === this._currentBarcode) {
            return;
        }
        this._currentBarcode = barcode;
        const filteredBarcodes = [];
        for (const bc of barcodes) {
            const matchedURI = bc.match(/^urn:.*$/);
            if (matchedURI && this.uriInCache(matchedURI[0])) {
                continue;
            }
            filteredBarcodes.push(bc);
        }
        if (barcodes.length > 1 && !readingRFID) {
            this.trigger("addBarcodesCountToProcess", filteredBarcodes.length);
        }
        const parsedBarcodes = [];
        for (const bc of filteredBarcodes) {
            const barcodeObject = BarcodeObject.forBarcode(bc);
            await barcodeObject.setRecords();
            parsedBarcodes.push(barcodeObject);
        }
        await this._getMissingRecords();
        const validBarcodes = [];
        for (const barcodeObject of parsedBarcodes) {
            if (barcodeObject.hasMissingRecords) {
                await barcodeObject.setRecords();
                if (barcodeObject.isURN && barcodeObject.hasMissingRecords && barcodeObject.missingRecords.find( (mr) => mr.type === "product")) {
                    this.trigger("updateBarcodesCountProcessed");
                    continue;
                }
            }
            validBarcodes.push(barcodeObject);
        }
        this.actionMutex.exec(async () => {
            for (const barcodeObject of validBarcodes) {
                await this._processBarcode(barcodeObject.rawValue);
                this.trigger("updateBarcodesCountProcessed");
            }
        }
        );
        this.postProcessBarcode();
    }

    _getMissingRecordsParams() {
        return {
            context: {
                allowed_company_ids: [this._getCompanyId()]
            },
            forceUnrestrictedSearch: !this.parser.nomenclature.is_gs1_nomenclature,
        };
    }

    async _getMissingRecords() {
        const params = this._getMissingRecordsParams();
        await this.cache.getMissingRecords(params);
    }

    async getGs1Filters(gs1RulesData) {
        const gs1Filters = {};
        const productRule = gs1RulesData.find( (bc) => bc.type === "product");
        if (productRule) {
            let product = await this.cache.getRecordByBarcode(productRule.value, "product.product");
            if (!product) {
                const packaging = await this.cache.getRecordByBarcode(productRule.value, "product.uom");
                if (packaging) {
                    product = this.cache.getRecord("product.product", packaging.product_id);
                }
            }
            if (product) {
                gs1Filters["stock.lot"] = {
                    product_id: product.id
                };
            }
        }
        return gs1Filters;
    }

    _canOverrideTrackingNumber(line, newLotName) {
        const lineLotName = line.lot_name || line.lot_id?.name;
        return !newLotName || !lineLotName || newLotName === lineLotName;
    }

    _checkBarcode(barcodeData) {
        return true;
    }

    async _closeValidate(ev) {
        if (ev === undefined) {
            this.notification(this.validateMessage, {
                type: "success"
            });
            this.trigger("history-back");
        }
    }

    _convertDataToFieldsParams(args) {
        throw new Error("Not Implemented");
    }

    createNewLine(params) {
        return this._createNewLine(params);
    }

    async _createNewLine(params) {
        const newLine = Object.assign({}, params.copyOf, this._getNewLineDefaultValues(params.fieldsParams));
        const previousIndex = (params.copyOf || this.selectedLine || {}).sortIndex;
        if (previousIndex !== undefined) {
            const newIndex = previousIndex + 1;
            for (const line of this.currentState.lines) {
                if (line.sortIndex >= newIndex) {
                    line.sortIndex += 1;
                }
            }
            this.currentSortIndex += 1;
            newLine.sortIndex = newIndex;
        } else {
            newLine.sortIndex = this._getLineIndex();
        }
        await this.updateLine(newLine, params.fieldsParams);
        this.currentState.lines.push(newLine);
        return newLine;
    }

    postProcessBarcode() {
        this.trigger("clearBarcodesCountProcessed");
        this.notificationCache.clear();
        delete this._currentBarcode;
    }

    async validate() {
        await this.save();
        const context = this.validateContext;
        context["barcode_trigger"] = true;
        const action = await this.orm.call(this.resModel, this.validateMethod, [this.recordIds], {
            context,
        });
        const options = {
            onClose: (ev) => this._closeValidate(ev),
        };
        if (action && (action.res_model || action.type == "ir.actions.client")) {
            if (action.type == "ir.actions.client") {
                action.params = Object.assign(action.params || {}, options);
            }
            this.trigger("playSound");
            return this.action.doAction(action, options);
        }
        return options.onClose();
    }

    uriInCache(uri) {
        return this.uriCache.has(uri);
    }

    splitBarcode(barcode) {
        const matchedURI = [...barcode.matchAll(/urn:(?:[a-z0-9 -]+:){3} ?[0-9.]+/g)];
        if (matchedURI.length > 1) {
            return matchedURI.map( (uri) => uri[0]);
        }
        return barcode.split(RegExp(this.config.barcode_separator_regex)).filter( (bc) => bc);
    }
    
    cancel() {
        console.log("Cancelling...");
    }

    lineIsSelected(line) {
        return (line.dummy_id || line.virtual_id) == this.selectedLineVirtualId;
    }

    _shouldSearchForAnotherLot(barcodeData, filters) {
        return (!barcodeData.match && filters["stock.lot"] && !this.canCreateNewLot && this.useExistingLots);
    }

    _shouldSearchForAnotherLine(line, barcodeData) {
        if (line.product_id.id !== barcodeData.product.id) {
            return true;
        }
        if (barcodeData.product.tracking === "serial" && this.getQtyDone(line) > 0) {
            return true;
        }
        const {lot, lotName} = barcodeData;
        const dataLotName = lotName || (lot && lot.name) || false;
        const lineLotName = this.getlotName(line);
        if (dataLotName && lineLotName && dataLotName !== lineLotName) {
            return true;
        }
        const parentLine = this._getParentLine(line);
        const currentLine = parentLine || line;
        return this.getQtyDone(currentLine) >= this.getQtyDemand(currentLine);
    }
    
    get _uniqueVirtualId() {
        this._lastVirtualId = this._lastVirtualId || 0;
        return ++this._lastVirtualId;
    }

    _updateLineQty(line, qty) {
        throw new Error("Not Implemented");
    }

    _updateLotName(line, lotName) {
        throw new Error("Not Implemented");
    }

    lineIsTracked(line) {
        return line.product_id && line.product_id.tracking !== "none";
    }

    lineIsFaulty(line) {
        throw new Error("Not Implemented");
    }

    lineCanBeDeleted(line) {
        return !this.getQtyDemand(line);
    }

    lineCanBeEdited() {
        return true;
    }

    lineCanBeTakenFromTheCurrentLocation(line) {
        return this.lineIsInTheCurrentLocation(line);
    }

    lineIsInTheCurrentLocation(line) {
        return Boolean(!this.groups.group_stock_multi_locations || !this.lastScanned.sourceLocation || this.lastScanned.sourceLocation.id == line.location_id.id);
    }

    _retrievePackagingData(barcodeData) {
        const {packaging} = barcodeData;
        const product = this.cache.getRecord("product.product", packaging.product_id);
        const packagingUom = this.cache.getRecord("uom.uom", packaging.uom_id);
        const uom = this._shouldBeExpressedInPackagingUom() ? packagingUom : this.cache.getRecord("uom.uom", product.uom_id);
        let quantity = "quantity"in barcodeData ? barcodeData.quantity : 1;
        if (!this._shouldBeExpressedInPackagingUom() && packagingUom !== uom) {
            const factor = packagingUom.factor / uom.factor;
            quantity *= factor;
        }
        return {
            product,
            quantity,
            uom
        };
    }

    _retrieveTrackingNumberInfo(lot) {
        return {
            product: this.cache.getRecord("product.product", lot.product_id)
        };
    }

    lineCanBeSelected(line) {
        return true;
    }

    _findLine(barcodeData) {
        let foundLine = false;
        const {lot, lotName, product} = barcodeData;
        const quantPackage = barcodeData.quantPackage || barcodeData.package;
        const uomId = barcodeData.uom ? barcodeData.uom.id : barcodeData.product?.uom_id;
        const dataLotName = lotName || (lot && lot.name) || false;
        const pageLines = [...this.pageLines];
        if (this.selectedLineVirtualId) {
            const selectedLineIndex = pageLines.findIndex( (line) => line.virtual_id == this.selectedLineVirtualId);
            if (selectedLineIndex > -1) {
                pageLines.splice(selectedLineIndex, 1);
                pageLines.unshift(this.pageLines[selectedLineIndex]);
            }
        }
        for (const line of pageLines) {
            const lineLotName = this.getlotName(line);
            if (line.product_id.id !== product.id) {
                continue;
            }
            if (line.packaging_uom_id && line.packaging_uom_id.id !== line.product_uom_id.id && line.packaging_uom_id.id !== uomId && line.product_uom_id.id !== uomId) {
                continue;
            }
            if (quantPackage && (!line.package_id || line.package_id.id !== quantPackage.id)) {
                continue;
            }
            if (line.product_id.tracking !== "none" && !this._canOverrideTrackingNumber(line, dataLotName)) {
                continue;
            }
            if (line.product_id.tracking === "serial") {
                if (this.getQtyDone(line) >= 1 && lineLotName) {
                    continue;
                } else if (dataLotName && this.getQtyDone(line) > 1) {
                    continue;
                }
            }
            if ((!dataLotName || !lineLotName || dataLotName !== lineLotName) && line.qty_done && line.qty_done >= line.reserved_uom_qty && (line.product_id.tracking === "none" || lineLotName) && line.id && (!this.selectedLine || line.virtual_id != this.selectedLine.virtual_id)) {
                continue;
            }
            if (this._lineCannotBeTaken(line)) {
                continue;
            }
            if (this._lineIsNotComplete(line)) {
                if (this.lineCanBeTakenFromTheCurrentLocation(line)) {
                    foundLine = line;
                    if (this.lineIsInTheCurrentLocation(line) && (line.product_id.tracking === "none" || !dataLotName || dataLotName === lineLotName) && line.product_uom_id.id === uomId) {
                        break;
                    }
                } else if (this.needSourceConfirmation && foundLine && !this._lineIsNotComplete(foundLine)) {
                    foundLine = false;
                    continue;
                }
            }
            if (!foundLine) {
                const currentLocationId = this.lastScanned.sourceLocation && this.lastScanned.sourceLocation.id;
                if (this.selectedLine && this.selectedLine.virtual_id === line.virtual_id && (!currentLocationId || !foundLine || foundLine.location_id.id != currentLocationId)) {
                    foundLine = this.lineCanBeTakenFromTheCurrentLocation(line) ? line : foundLine;
                } else if (!foundLine || (currentLocationId && foundLine.location_id.id != currentLocationId && line.location_id.id == currentLocationId)) {
                    foundLine = this.lineCanBeTakenFromTheCurrentLocation(line) ? line : foundLine;
                }
            } else if (this._lineIsNotComplete(foundLine)) {
                continue;
            } else if (this._lineIsNotComplete(line)) {
                foundLine = line;
            } else if (foundLine.product_uom_id.id !== uomId && line.product_uom_id.id === uomId) {
                foundLine = line;
            } else if (this.lineIsSelected(line) || (!this.lineIsSelected(foundLine) && this.lineBelongsToSelectedLine(line))) {
                foundLine = line;
            }
        }
        return foundLine;
    }

    lineBelongsToSelectedLine(line) {
        if (!this.selectedLine) {
            return false;
        }
        const selectedGroupedLine = this._getParentLine(this.selectedLine);
        return selectedGroupedLine && selectedGroupedLine.virtual_ids.includes(line.virtual_id);
    }

    _lineCannotBeTaken(line) {
        return !this.lineCanBeTakenFromTheCurrentLocation(line);
    }

    get showReservedSns() {
        return true;
    }

    _getParentLine(line) {
        return line && line.parentLine;
    }

    _getFieldToWrite() {
        throw new Error("Not Implemented");
    }

    _getSaveLineCommand() {
        const commands = [];
        const fields = this._getFieldToWrite();
        for (const virtualId of this.linesToSave) {
            const line = this.currentState.lines.find( (l) => l.virtual_id === virtualId);
            if (line.id) {
                const initialLine = this.initialState.lines.find( (l) => l.virtual_id === line.virtual_id);
                const changedValues = {};
                let somethingToSave = false;
                for (const field of fields) {
                    const fieldValue = line[field];
                    const initialValue = initialLine[field];
                    if (fieldValue !== undefined && ((["boolean", "number", "string"].includes(typeof fieldValue) && fieldValue !== initialValue) || (typeof fieldValue === "object" && fieldValue.id !== initialValue.id))) {
                        changedValues[field] = this._fieldToValue(fieldValue);
                        somethingToSave = true;
                    }
                }
                if (somethingToSave) {
                    commands.push([1, line.id, changedValues]);
                }
            } else {
                commands.push([0, 0, this._createCommandVals(line)]);
            }
        }
        return commands;
    }

    _groupSublines(sublines, parentKey="parentLine") {
        const [ids,virtual_ids] = [[], []];
        let[totalQtyDemand,totalQtyDone] = [0, 0];
        const sortedSublines = this._sortLine(sublines);
        const referenceLine = sortedSublines.reduce( (result, line) => line.id && (!result.id || result.id > line.id) ? line : result);
        for (const subline of sublines) {
            ids.push(subline.id);
            virtual_ids.push(subline.virtual_id);
            totalQtyDemand += this.getQtyDemand(subline);
            totalQtyDone += this.getQtyDone(subline);
        }
        const groupedLine = Object.assign({}, referenceLine, {
            ids,
            lines: sortedSublines,
            opened: false,
            virtual_ids,
            totalQtyDemand,
            totalQtyDone,
        });
        for (const subline of sublines) {
            subline[parentKey] = groupedLine;
        }
        return groupedLine;
    }

    async _goToMainMenu() {
        await this.save();
        this.action.doAction("barcode_wms.barcode_wms_action_main_menu", {
            clearBreadcrumbs: true,
        });
    }

    _createLinesState() {
        throw new Error("Not Implemented");
    }

    _incrementTrackedLine() {
        return false;
    }

    _lineIsNotComplete(line) {
        throw new Error("Not Implemented");
    }

    _getSaveCommand() {
        throw new Error("Not Implemented");
    }

    _fieldToValue(fieldValue) {
        return typeof fieldValue === "object" ? fieldValue.id : fieldValue;
    }

    displayLineQtyDemand(line) {
        return this.getQtyDemand(line);
    }

    IsNotSet(line) {
        return false;
    }

    zeroQtyClass(line) {
        return "text-muted";
    }

    get displayDestinationLocation() {
        return false;
    }

    get displayResultPackage() {
        return false;
    }

    selectLine(line) {
        if (this.lineCanBeSelected(line) && (!line.virtual_ids || !line.virtual_ids.includes(this.selectedLineVirtualId))) {
            this._selectLine(line);
        }
    }

    selectPackageLine(packageLine) {
        if (this.lineCanBeSelected(packageLine)) {
            this.lastScanned.packageId = packageLine.package_id.id;
        }
    }

    toggleSublines(line) {
        const lineKey = this.groupKey(line);
        this.unfoldLineKey = this.unfoldLineKey === lineKey ? false : lineKey;
        if (this.unfoldLineKey === lineKey && (!this.selectedLine || this.unfoldLineKey != this.groupKey(this.selectedLine))) {
            this.selectLine(line);
        }
        this.trigger("update");
    }

    async updateLine(line, args) {
        let {location_id, lot_id, owner_id, package_id} = args;
        if (!line) {
            throw new Error("No line found");
        }
        if (!line.product_id && args.product_id) {
            line.product_id = args.product_id;
            line.product_uom_id = this.cache.getRecord("uom.uom", args.uom?.id || args.product_id.uom_id);
        }
        if (location_id) {
            if (typeof location_id === "number") {
                location_id = this.cache.getRecord("stock.location", args.location_id);
            }
            line.location_id = location_id;
        }
        if (lot_id) {
            if (typeof lot_id === "number") {
                lot_id = this.cache.getRecord("stock.lot", args.lot_id);
            }
            line.lot_id = lot_id;
        }
        if (owner_id) {
            if (typeof owner_id === "number") {
                owner_id = this.cache.getRecord("res.partner", args.owner_id);
            }
            line.owner_id = owner_id;
        }
        if (package_id) {
            if (typeof package_id === "number") {
                package_id = this.cache.getRecord("stock.package", args.package_id);
            }
            const parentPackId = package_id.parent_package_id;
            if (parentPackId && typeof parentPackId === "number") {
                package_id.parent_package_id = this.cache.getRecord("stock.package", parentPackId);
            }
            line.package_id = package_id;
        }
        if (args.lot_name && line.product_id.tracking !== "none") {
            await this.updateLotName(line, args.lot_name);
        }
        this._updateLineQty(line, args);
        this._markLineAsDirty(line);
    }

    createSingleLinesForPackaging(barcodeData) {
        return (barcodeData.product.tracking === "serial" && barcodeData.packaging && (this.useExistingLots || this.canCreateNewLot));
    }

    beforeQuit() {
        return this.save();
    }

    async save() {
        const {route, params} = this._getSaveCommand();
        if (route) {
            const res = await rpc(route, params);
            await this.refreshCache(res.records);
        }
        this.linesToSave = [];
    }

    _selectLine(line) {
        const virtualId = line.virtual_id;
        if (this.selectedLineVirtualId === virtualId) {
            return;
        }
        this.selectedLineVirtualId = virtualId;
        this.lastScanned.destLocation = false;
    }

    _setLocationFromBarcode(result, location) {
        result.location = location;
        return result;
    }

    _sortingMethod(l1, l2) {
        const sourceLocation1 = l1.location_id.display_name;
        const sourceLocation2 = l2.location_id.display_name;
        if (sourceLocation1 < sourceLocation2) {
            return -1;
        } else if (sourceLocation1 > sourceLocation2) {
            return 1;
        }
        const package1 = l1.package_id.name;
        const package2 = l2.package_id.name;
        if (package1 < package2) {
            return -1;
        } else if (package1 > package2) {
            return 1;
        }
        if (l1.location_dest_id && l2.location_dest_id) {
            const destinationLocation1 = l1.location_dest_id.display_name;
            const destinationLocation2 = l2.location_dest_id.display_name;
            if (destinationLocation1 < destinationLocation2) {
                return -1;
            } else if (destinationLocation1 > destinationLocation2) {
                return 1;
            }
        }
        if (l1.result_package_id && l2.result_package_id) {
            const resultPackage1 = l1.result_package_id.name;
            const resultPackage2 = l2.result_package_id.name;
            if (resultPackage1 < resultPackage2) {
                return -1;
            } else if (resultPackage1 > resultPackage2) {
                return 1;
            }
        }
        const categ1 = l1.product_category_name;
        const categ2 = l2.product_category_name;
        if (categ1 < categ2) {
            return -1;
        } else if (categ1 > categ2) {
            return 1;
        }
        const product1 = l1.product_id.display_name;
        const product2 = l2.product_id.display_name;
        if (product1 < product2) {
            return -1;
        } else if (product1 > product2) {
            return 1;
        }
        return 0;
    }

    _sortLine(lines) {
        return lines.sort( (l1, l2) => (l1.sortIndex > l2.sortIndex ? 1 : -1));
    }

    _isPackageInPackage(pack, containerPack) {
        const parentNames = pack.dest_complete_name.split(" > ");
        return parentNames.some( (name) => name === containerPack.name);
    }

    updateLineQty(virtualId, qty=1) {
        throw new Error("Not Implemented");
    }

    async updateLotName(line, lotName) {
        for (const l of this.pageLines) {
            if (line.virtual_id === l.virtual_id || line.product_id.tracking !== "serial" || line.product_id.id !== l.product_id.id) {
                continue;
            }
            if (lotName === l.lot_name || (l.lot_id && lotName === l.lot_id.name)) {
                this.notification(_t("This serial number is already used."), {
                    type: "warning"
                });
                return;
            }
        }
        await this._updateLotName(line, lotName);
    }

    _markLineAsDirty(line) {
        if (!this.linesToSave) this.linesToSave = [];
        if (!this.linesToSave.includes(line.virtual_id)) {
            this.linesToSave.push(line.virtual_id);
        }
    }

    async _parseBarcode(barcode, filters) {
        const result = {
            barcode,
            match: false,
        };
        if (this.commands[barcode]) {
            result.action = this.commands[barcode];
            result.match = true;
            return result;
        }
        let parsedBarcode;
        try {
            parsedBarcode = this.parser.parse_barcode(barcode);
        } catch (err) {
            console.log(`%cWarning: error about ${barcode}`, "text-weight: bold;");
            console.log(err.message);
        }
        if (parsedBarcode) {
            if (parsedBarcode.length) {
                const gs1Filters = await this.getGs1Filters(parsedBarcode);
                for (const data of parsedBarcode) {
                    if (data.type === "lot" && result.product?.tracking === "none") {
                        continue;
                    }
                    const parsedData = await this._processGs1Data(data, gs1Filters);
                    Object.assign(result, parsedData);
                }
                if (result.match) {
                    return result;
                }
            } else if (parsedBarcode.type === "weight") {
                result.weight = parsedBarcode;
                result.match = true;
                barcode = parsedBarcode.base_code;
            } else if (parsedBarcode.type === "product" && parsedBarcode.code !== barcode) {
                barcode = parsedBarcode.code;
                if (this.commands[barcode]) {
                    result.action = this.commands[barcode];
                    result.match = true;
                    return result;
                }
            }
        }
        const fetchedRecord = await this._fetchRecordFromTheCache(barcode, filters, result);
        return Object.assign(result, fetchedRecord);
    }

    async _fetchRecordFromTheCache(barcode, filters, data) {
        const result = data || {
            barcode,
            match: false
        };
        const recordByData = await this.cache.getRecordByBarcode(barcode, false, {
            filters
        });
        if (recordByData.size > 1) {
            const message = _t("Barcode scan is ambiguous with several model: %s. Use the most likely.", Array.from(recordByData.keys()));
            this.notification(message, {
                type: "warning"
            });
        }
        if (this.groups.group_stock_multi_locations) {
            const location = recordByData.get("stock.location");
            if (location) {
                this._setLocationFromBarcode(result, location);
                result.match = true;
            }
        }
        if (this.groups.group_tracking_lot) {
            const packageType = recordByData.get("stock.package.type");
            const stockPackage = recordByData.get("stock.package");
            if (stockPackage) {
                if (stockPackage && stockPackage.package_type_id) {
                    stockPackage.package_type_id = await this.cache.getRecord("stock.package.type", stockPackage.package_type_id);
                }
                result.package = stockPackage;
                result.match = true;
            }
            if (packageType) {
                result.packageType = packageType;
                result.match = true;
            }
        }
        const product = recordByData.get("product.product");
        if (product) {
            result.product = product;
            result.match = true;
        }
        if (this.groups.group_uom) {
            const packaging = recordByData.get("product.uom");
            if (packaging) {
                result.match = true;
                result.packaging = packaging;
            }
        }
        if (this.useExistingLots) {
            const lot = recordByData.get("stock.lot");
            if (lot) {
                result.lot = lot;
                result.match = true;
            }
        }
        if (!result.match && this.packageTypes.length) {
            for (const [packageTypeBarcode,packageTypeId] of this.packageTypes) {
                if (barcode.indexOf(packageTypeBarcode) === 0) {
                    result.packageType = await this.cache.getRecord("stock.package.type", packageTypeId);
                    result.packageName = barcode;
                    result.match = true;
                    break;
                }
            }
        }
        return result;
    }

    _moveEntirePackage() {
        return false;
    }

    async deleteLine(line) {
        if (!line.id) {
            const index = this.currentState.lines.findIndex( (l) => l.virtual_id === line.virtual_id);
            this.currentState.lines.splice(index, 1);
            this.linesToSave = this.linesToSave.filter( (vId) => vId !== line.virtual_id);
        } else {
            await this.save();
            await this.orm.call(this.lineModel, this.deleteLineMethod, [line.id]);
            this.trigger("refresh");
        }
    }

    async deleteLines(lines) {
        const lineIds = [];
        for (const line of lines) {
            if (!line.id) {
                const index = this.currentState.lines.findIndex( (l) => l.virtual_id === line.virtual_id);
                this.currentState.lines.splice(index, 1);
                this.linesToSave = this.linesToSave.filter( (vId) => vId !== line.virtual_id);
            } else {
                lineIds.push(line.id);
            }
        }
        if (lineIds.length) {
            await this.save();
            await this.orm.call(this.lineModel, this.deleteLineMethod, [lineIds]);
            this.trigger("refresh");
        }
    }
    _shouldCreateLineOnExceed(line) {
        return true;
    }

    _shouldBeExpressedInPackagingUom() {
        return true;
    }

    _defaultLocation() {
        const lastScannedLocation = this.lastScanned.sourceLocation;
        return lastScannedLocation || Object.values(this.cache.dbIdCache["stock.location"])[0];
    }

    _defaultDestLocation() {
        return undefined;
    }
    
    _getCommands() {
        const commands = {
            OCDMENU: this._goToMainMenu.bind(this)
        };
        if (!this.isDone) {
            commands["OBTVALI"] = () => {
                if (this.canBeValidate) {
                    this.validate();
                } else {
                    this.trigger("playSound", "error");
                }
            }
            ;
        }
        return commands;
    }

    _getModelRecord() {
        return false;
    }

    _getNewLineDefaultValues(fieldsParams) {
        return {
            id: (fieldsParams && fieldsParams.id) || false,
            virtual_id: this._uniqueVirtualId,
            location_id: this._defaultLocation(),
            package_id: false,
        };
    }

    _getNewLineDefaultContext() {
        throw new Error("Not Implemented");
    }

    _getLineIndex() {
        const sortIndex = this.currentSortIndex;
        this.currentSortIndex++;
        return sortIndex;
    }

    completePackage(virtualId) {
        console.log("Complete package", virtualId);
        this.trigger("update");
    }

    get selectedLine() {
        return (this.selectedLineVirtualId && this.currentState.lines.find( (l) => (l.dummy_id || l.virtual_id) === this.selectedLineVirtualId));
    }

    get useExistingLots() {
        return true;
    }

    get highlightValidateButton() {
        return false;
    }

    get isDone() {
        return false;
    }

    get isCancelled() {
        return false;
    }

    get location() {
        if (this.lastScanned.sourceLocation) {
            return this.cache.getRecord("stock.location", this.lastScanned.sourceLocation.id);
        }
        return this._currentLocation || this._defaultLocation();
    }

    set location(location) {
        this._currentLocation = location;
        this.lastScanned.sourceLocation = location;
    }

    displaySetButton(_line) {
        return false;
    }

    get lastScannedLine() {
        if (this.scannedLinesVirtualId && this.scannedLinesVirtualId.length) {
            const virtualId = this.scannedLinesVirtualId[this.scannedLinesVirtualId.length - 1];
            return this.currentState.lines.find(l => l.virtual_id === virtualId);
        }
        return false;
    }

    _defaultDestLocation() {
        // Override in subclasses
        return {};
    }

    _isSublocation(location, parentLocation) {
        if (!location || !parentLocation) return false;
        return location.display_name && parentLocation.display_name &&
               location.display_name.startsWith(parentLocation.display_name);
    }


}
