/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

export class LazyBarcodeCache {
    constructor(cacheData) {
        this.dbIdCache = {};
        this.dbBarcodeCache = {};
        this.dbQuantCache = {};
        this.missingBarcodesCache = new Set();
        this.missingBarcodeKeyCache = new Set();
        this.barcodeFieldByModel = {
            "stock.location": "barcode",
            "product.product": "barcode",
            "product.uom": "barcode",
            "stock.package.type": "barcode",
            "stock.picking": "name",
            "stock.package": "name",
            "stock.lot": "name",
        };
        this.gs1LengthsByModel = {
            "product.product": 14,
            "product.uom": 14,
            "stock.location": 13,
            "stock.package": 18,
        };
        if (cacheData && cacheData["barcode.nomenclature"] && cacheData["barcode.nomenclature"].length === 1) {
            this.nomenclature = cacheData["barcode.nomenclature"][0];
        }
        if (cacheData) {
            this.setCache(cacheData);
        }
        this.waitingFetch = [];
    }

    setCache(cacheData) {
        for (const model in cacheData) {
            const records = cacheData[model];
            if (this.dbIdCache[model] === undefined) {
                this.dbIdCache[model] = {};
            }
            if (this.dbBarcodeCache[model] === undefined) {
                this.dbBarcodeCache[model] = {};
            }
            const barcodeField = this._getBarcodeField(model);
            for (const record of records) {
                this.dbIdCache[model][record.id] = record;
                if (model === "stock.quant") {
                    const {product_id, location_id} = record;
                    // Handle m2o array -> id if needed, but assuming record has IDs
                    const prodId = Array.isArray(product_id) ? product_id[0] : product_id;
                    const locId = Array.isArray(location_id) ? location_id[0] : location_id;

                    if (!this.dbQuantCache[prodId]) {
                        this.dbQuantCache[prodId] = {};
                    }
                    if (!this.dbQuantCache[prodId][locId]) {
                        this.dbQuantCache[prodId][locId] = [];
                    }
                    const matchIndex = this.dbQuantCache[prodId][locId].findIndex(rec => rec.id === record.id);
                    if (matchIndex !== -1) {
                        this.dbQuantCache[prodId][locId][matchIndex] = record;
                    } else {
                        this.dbQuantCache[prodId][locId].push(record);
                    }
                } else if (model === "product.product" && cacheData["stock.quant"]) {
                    if (!this.dbQuantCache[record.id]) {
                        this.dbQuantCache[record.id] = {};
                    }
                }
                
                if (barcodeField) {
                    const barcode = record[barcodeField];
                    if (barcode) {
                        if (!this.dbBarcodeCache[model][barcode]) {
                            this.dbBarcodeCache[model][barcode] = [];
                        }
                        if (!this.dbBarcodeCache[model][barcode].includes(record.id)) {
                            this.dbBarcodeCache[model][barcode].push(record.id);
                            if (this.nomenclature && this.nomenclature.is_gs1_nomenclature && this.gs1LengthsByModel[model]) {
                                this._setBarcodeInCacheForGS1(barcode, model, record);
                            }
                        }
                    }
                }
            }
        }
    }

    getRecord(model, id, raiseErrorIfMissing=true) {
        if (this.dbIdCache[model] === undefined) {
            if (raiseErrorIfMissing) {
                throw new Error(`Model ${model} doesn't exist in the cache`);
            }
            return null;
        }
        if (this.dbIdCache[model][id] === undefined) {
            if (raiseErrorIfMissing) {
                throw new Error(`Record ${model} with id=${id} doesn't exist in the cache, it should return by the server`);
            }
            return null;
        }
        const record = this.dbIdCache[model][id];
        return JSON.parse(JSON.stringify(record));
    }
    
    async getQuants(product, location_id, params={}) {
        const lot_id = params.lot_id?.id || params.lot_id || false;
        const package_id = params.package_id?.id || params.package_id || false;
        const {lot_name, owner_id=false} = params;
        let quantsByProduct = this.dbQuantCache[product.id];
        if (!quantsByProduct) {
            const domain = [["product_id", "=", product.id], ["location_id.usage", "=", "internal"], ];
            const result = await rpc("/barcode_wms/get_quants", {
                domain
            });
            if (result) {
                this.setCache(result.records);
                quantsByProduct = this.dbQuantCache[product.id];
                if (!quantsByProduct) {
                    this.dbQuantCache[product.id] = [];
                    return [];
                }
            }
        }
        let quants = [];
        if (location_id) {
            const quantsByLocation = quantsByProduct[location_id];
            if (quantsByLocation) {
                quants.push(...quantsByLocation);
            } else {
                this.dbQuantCache[product.id][location_id] = [];
            }
        } else {
            for (const quantsByLocation of Object.values(quantsByProduct)) {
                quants.push(...quantsByLocation);
            }
        }
        if (!lot_id && !lot_name && !package_id && !owner_id) {
            return quants;
        }
        if (lot_id) {
            quants = quants.filter( (quant) => quant.lot_id === lot_id);
        } else if (lot_name) {
            const filters = {
                "stock.lot": {
                    product_id: product.id
                }
            };
            const lot = await this.getRecordByBarcode(lot_name, "stock.lot", filters);
            if (!lot) {
                return [];
            }
            quants = quants.filter( (quant) => quant.lot_id === lot.id);
        }
        if (owner_id) {
            quants = quants.filter( (quant) => quant.owner_id === owner_id);
        }
        if (package_id) {
            quants = quants.filter( (quant) => quant.package_id === package_id);
        }
        return quants;
    }

    async getRecordByBarcode(barcode, model=false, options={}) {
        const onlyInCache = Boolean(options.onlyInCache);
        const filters = options.filters || {};
        const fetchLater = Boolean(options.fetchLater);
        if (model) {
            if (this.dbBarcodeCache[model] === undefined) {
                if (fetchLater) {
                    this.waitingFetch.push({
                        barcode,
                        model,
                        options
                    });
                    if (model === "product.product") {
                        this.waitingFetch.push({
                            barcode,
                            model: "product.uom",
                            options
                        });
                    }
                    return null;
                }
                if (onlyInCache) {
                    return null;
                }
                throw new Error(`Model ${model} doesn't exist in the cache`);
            }
            if (this.dbBarcodeCache[model][barcode] === undefined) {
                if (fetchLater) {
                    this.waitingFetch.push({
                        barcode,
                        model,
                        options
                    });
                    if (model === "product.product") {
                        this.waitingFetch.push({
                            barcode,
                            model: "product.uom",
                            options
                        });
                    }
                    return null;
                }
                if (onlyInCache) {
                    return null;
                }
                await this._getMissingRecord(barcode, model, filters);
                return await this.getRecordByBarcode(barcode, model, {
                    onlyInCache: true,
                    filters,
                });
            }
            const ids = this.dbBarcodeCache[model][barcode];
            for (const id of ids) {
                const record = this.getRecord(model, id);
                let pass = true;
                if (filters[model]) {
                    const fields = Object.keys(filters[model]);
                    for (const field of fields) {
                        if (record[field] != filters[model][field]) {
                            pass = false;
                            break;
                        }
                    }
                }
                if (pass) {
                    return record;
                }
            }
        } else {
            const result = new Map();
            const models = Object.keys(this.dbBarcodeCache);
            for (const model of models) {
                if (this.dbBarcodeCache[model][barcode]) {
                    const ids = this.dbBarcodeCache[model][barcode];
                    for (const id of ids) {
                        const record = this.dbIdCache[model][id];
                        let pass = true;
                        if (filters[model]) {
                            const fields = Object.keys(filters[model]);
                            for (const field of fields) {
                                if (record[field] != filters[model][field]) {
                                    pass = false;
                                    break;
                                }
                            }
                        }
                        if (pass) {
                            result.set(model, JSON.parse(JSON.stringify(record)));
                            break;
                        }
                    }
                }
            }
            if (result.size < 1) {
                if (onlyInCache) {
                    return result;
                }
                await this._getMissingRecord(barcode, model, filters);
                return await this.getRecordByBarcode(barcode, model, {
                    onlyInCache: true,
                    filters,
                });
            }
            return result;
        }
    }

    _addToWaitingFetch(barcode, model, options) {
        this.waitingFetch.push({barcode, model, options});
    }

    _checkFilters(record, model, filters) {
        if (!filters[model]) return true;
        for (const [field, value] of Object.entries(filters[model])) {
            if (record[field] != value) return false;
        }
        return true;
    }

    _getBarcodeField(model) {
        if (this.barcodeFieldByModel[model] === undefined) {
            return null;
        }
        return this.barcodeFieldByModel[model];
    }

    async _getMissingRecord(barcode, model, filters={}) {
        const keyCache = JSON.stringify([...arguments]);
        const missCache = this.missingBarcodeKeyCache;
        const keyCacheWithoutModel = JSON.stringify([barcode, false, {}]);
        if (filters) {
            const keyCacheWithoutFilters = JSON.stringify([barcode, model, {}]);
            if (missCache.has(keyCacheWithoutFilters)) {
                return false;
            }
        }
        if (missCache.has(keyCache) || missCache.has(keyCacheWithoutModel)) {
            return false;
        }
        const params = {};
        if (model) {
            params.barcodes_by_model = {
                [model]: [barcode]
            };
        } else {
            params.barcode = barcode;
        }
        const domainsByModel = {};
        for (const filter of Object.entries(filters)) {
            const modelName = filter[0];
            const filtersByField = filter[1];
            domainsByModel[modelName] = [];
            for (const filterByField of Object.entries(filtersByField)) {
                if (filterByField[1]instanceof Array) {
                    domainsByModel[modelName].push([filterByField[0], "in", filterByField[1]]);
                } else {
                    domainsByModel[modelName].push([filterByField[0], "=", filterByField[1]]);
                }
            }
        }
        params.domains_by_model = domainsByModel;
        const result = await rpc("/barcode_wms/get_specific_barcode_data", params);
        this.setCache(result);
        missCache.add(keyCache);
    }

    async getMissingRecords(params={}) {
        if (!this.waitingFetch.length) {
            return;
        }
        params.barcodes_by_model = {};
        for (const data of this.waitingFetch) {
            const {barcode, model} = data;
            const keyCache = JSON.stringify([barcode, model, {}]);
            if (this.missingBarcodeKeyCache.has(keyCache)) {
                continue;
            }
            this.missingBarcodeKeyCache.add(keyCache);
            if (!params.barcodes_by_model[model]) {
                params.barcodes_by_model[model] = [];
            }
            params.barcodes_by_model[model].push(barcode);
        }
        if (Object.keys(params.barcodes_by_model).length) {
            const result = await rpc("/barcode_wms/get_specific_barcode_data", params);
            this.setCache(result);
            if (params.forceUnrestrictedSearch) {
                const foundBarcodes = [];
                const missingBarcodes = new Set();
                for (const model of Object.keys(result)) {
                    for (const record of result[model]) {
                        foundBarcodes.push(record[this.barcodeFieldByModel[model]]);
                    }
                }
                for (const model of Object.keys(params.barcodes_by_model)) {
                    for (const barcode of params.barcodes_by_model[model]) {
                        if (!foundBarcodes.includes(barcode) && !this.missingBarcodesCache.has(barcode)) {
                            missingBarcodes.add(barcode);
                            this.missingBarcodesCache.add(barcode);
                        }
                    }
                }
                if (missingBarcodes.size) {
                    const barcodes = [...missingBarcodes];
                    for (const bc of barcodes) {
                        this.missingBarcodeKeyCache.add(JSON.stringify([bc, false, {}]));
                    }
                    const updatedParams = {
                        ...params,
                        barcodes
                    };
                    delete updatedParams.barcodes_by_model;
                    const notRestrictedByModelResult = await rpc("/barcode_wms/get_specific_barcode_data", updatedParams);
                    this.setCache(notRestrictedByModelResult);
                }
            }
        }
        this.waitingFetch = [];
    }
    
    _setBarcodeInCacheForGS1(barcode, model, record) {
        const length = this.gs1LengthsByModel[model];
        if (!barcode || barcode.length >= length || isNaN(Number(barcode))) return;
        
        const paddedBarcode = barcode.padStart(length, "0");
        if (!this.dbBarcodeCache[model][paddedBarcode]) {
            this.dbBarcodeCache[model][paddedBarcode] = [record.id];
        } else if (!this.dbBarcodeCache[model][paddedBarcode].includes(record.id)) {
            this.dbBarcodeCache[model][paddedBarcode].push(record.id);
        }
    }
}
