/** @odoo-module **/

export class BarcodeObject {
    constructor(rawValue) {
        this.rawValue = rawValue;
        this.nomenclature = undefined;
        this.parsedBarcode = undefined;
        this.parsedData = {};
        this.isParsed = false;
        this.missingRecords = [];
        this.isURN = Boolean(this.rawValue.match(/^urn:.*$/));
        if (this.parser) {
            try {
                this.parsedBarcode = this.parser.parse_barcode(this.rawValue);
            } catch (err) {
                console.log(`%cWarning: error about ${this.rawValue}`, "text-weight: bold;");
                console.log(err.message);
            }
            if (this.parsedBarcode && !Array.isArray(this.parsedBarcode)) {
                this.parsedBarcode = [this.parsedBarcode];
            }
            this.isParsed = Boolean(this.parsedBarcode?.length);
        } else {
            console.warn("No parser set !");
        }
        BarcodeObject.mappingRawBarcodeToObject[rawValue] = this;
    }

    async setRecords(options=false) {
        if (!this.isParsed) {
            return;
        }
        options = options || {
            fetchLater: true,
            onlyInCache: true,
        };
        this.missingRecords = [];
        for (const barcodeData of this.parsedBarcode) {
            const {type, code} = barcodeData;
            if (type === "product") {
                await this.fetchProduct(code, options);
            } else if (type === "lot") {
                await this.fetchTrackingNumber(code, options);
            }
        }
    }

    get cache() {
        return BarcodeObject.__cache;
    }

    get hasMissingRecords() {
        return this.isParsed && Boolean(this.missingRecords.length);
    }

    get parser() {
        return BarcodeObject.__parser;
    }

    async fetchTrackingNumber(lotBarcode, options) {
        const lot = await this.cache.getRecordByBarcode(lotBarcode, "stock.lot", options);
        if (lot) {
            this.parsedData.lot = lot;
        } else {
            this.missingRecords.push({
                type: "lot",
                lotBarcode
            });
        }
    }

    async fetchProduct(productBarcode, options) {
        let product = await this.cache.getRecordByBarcode(productBarcode, "product.product", options);
        if (!product) {
            const packaging = await this.cache.getRecordByBarcode(productBarcode, "product.uom", {
                onlyInCache: true,
            });
            if (packaging) {
                product = this.cache.getRecord("product.product", packaging.product_id, false);
                this.parsedData.packaging = packaging;
                this.parsedData.quantity = packaging.uom_id.factor;
            }
        }
        if (product) {
            this.parsedData.product = product;
        } else {
            this.missingRecords.push({
                type: "product",
                productBarcode
            });
        }
    }
}

BarcodeObject.mappingRawBarcodeToObject = {};
BarcodeObject.setEnv = (cache, parser) => {
    BarcodeObject.__cache = cache;
    BarcodeObject.__parser = parser;
};
BarcodeObject.forBarcode = (barcode) => {
    if (BarcodeObject.mappingRawBarcodeToObject[barcode]) {
        return BarcodeObject.mappingRawBarcodeToObject[barcode];
    }
    return new BarcodeObject(barcode);
};
