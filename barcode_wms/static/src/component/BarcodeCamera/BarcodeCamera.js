/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from '@web/core/l10n/translation';
import { browser } from "@web/core/browser/browser";
import { delay } from "@web/core/utils/concurrency";
import { loadJS, templates } from "@web/core/assets";
import { Deferred } from "@web/core/utils/concurrency";
import { isVideoElementReady, buildZXingBarcodeDetector } from "@web/core/barcode/ZXingBarcodeDetector";
import { CropOverlay } from "@web/core/barcode/crop_overlay";
import { Component, useRef, onWillStart, onMounted, onWillUnmount, App, useState } from "@odoo/owl";


class BarcodeCameraDialog extends Component {
    setup() {
        this.videoPreviewRef = useRef("videoPreview");
        this.interval = null;
        this.stream = null;
        this.detector = null;
        this.overlayInfo = {};
        this.zoomRatio = 1;
        this.state = useState({
            isReady: false,
        });
        onWillStart(async () => {
            let DetectorClass;
            if ("BarcodeDetector"in window) {
                DetectorClass = BarcodeDetector;
            } else {
                await loadJS("/web/static/lib/zxing-library/zxing-library.js");
                DetectorClass = buildZXingBarcodeDetector(window.ZXing);
            }
            const formats = await DetectorClass.getSupportedFormats();
            this.detector = new DetectorClass({
                formats
            });
        }
        );
        
        onMounted(async () => {
            const constraints = {
                video: {
                    facingMode: this.props.facingMode
                },
                audio: false,
            };
            try {
                this.stream = await browser.navigator.mediaDevices.getUserMedia(constraints);
            } catch (err) {
                const errors = {
                    NotFoundError: _t("No device can be found."),
                    NotAllowedError: _t("Odoo needs your authorization first."),
                };
                const errorMessage = _t("Could not start scanning. ") + (errors[err.name] || err.message);
                this.onError(new Error(errorMessage));
                return;
            }
            this.videoPreviewRef.el.srcObject = this.stream;
            await this.isVideoReady();
            const {height, width} = getComputedStyle(this.videoPreviewRef.el);
            const divWidth = width.slice(0, -2);
            const divHeight = height.slice(0, -2);
            const tracks = this.stream.getVideoTracks();
            if (tracks.length) {
                const [track] = tracks;
                const settings = track.getSettings();
                this.zoomRatio = Math.min(divWidth / settings.width, divHeight / settings.height);
            }
            this.interval = setInterval(this.detectCode.bind(this), 50);
        }
        );
        onWillUnmount( () => {
            clearInterval(this.interval);
            this.interval = null;
            if (this.stream) {
                this.stream.getTracks().forEach( (track) => track.stop());
                this.stream = null;
            }
        }
        );
    }
    isZXingBarcodeDetector() {
        return this.detector && this.detector.__proto__.constructor.name === "ZXingBarcodeDetector";
    }
    async isVideoReady() {
        return new Promise(async (resolve) => {
            while (!isVideoElementReady(this.videoPreviewRef.el)) {
                await delay(10);
            }
            this.state.isReady = true;
            resolve();
        }
        );
    }
    onZoomChange(event) {
        const zoomRatio = parseFloat(event.target.value); // Slider'dan gelen zoom değeri
        this.videoPreviewRef.el.style.transform = `scale(${zoomRatio})`; // Zoom'u uygula
        this.videoPreviewRef.el.style.transformOrigin = "center"; // Zoom merkezi
    }
    onResize(overlayInfo) {
        this.overlayInfo = overlayInfo;
        if (this.isZXingBarcodeDetector()) {
            this.detector.setCropArea(this.adaptValuesWithRatio(this.overlayInfo, true));
        }
    }
    onResult(result) {
        this.props.onClose({
            barcode: result
        });
    }
    onError(error) {
        this.props.onClose({
            error
        });
    }
    async detectCode() {
        try {
            const codes = await this.detector.detect(this.videoPreviewRef.el);
            for (const code of codes) {
                if (!this.isZXingBarcodeDetector() && this.overlayInfo.x && this.overlayInfo.y) {
                    const {x, y, width, height} = this.adaptValuesWithRatio(code.boundingBox);
                    if (x < this.overlayInfo.x || x + width > this.overlayInfo.x + this.overlayInfo.width || y < this.overlayInfo.y || y + height > this.overlayInfo.y + this.overlayInfo.height) {
                        continue;
                    }
                }
                this.onResult(code.rawValue);
                break;
            }
        } catch (err) {
            this.onError(err);
        }
    }
    adaptValuesWithRatio(object, dividerRatio=false) {
        const newObject = Object.assign({}, object);
        for (const key of Object.keys(newObject)) {
            if (dividerRatio) {
                newObject[key] /= this.zoomRatio;
            } else {
                newObject[key] *= this.zoomRatio;
            }
        }
        return newObject;
    }
}

BarcodeCameraDialog.components = {
    Dialog,
    CropOverlay,
};
BarcodeCameraDialog.template = "barcode_wms.BarcodeCameraDialog"

export function isBarcodeScannerSupported() {
    return navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
}

// export async function scanBarcode() {
//     console.log("scanBarcode");
//     const promise = new Promise((resolve, reject) => {
//         bus.on(busOk, null, resolve);
//         bus.on(busError, null, reject);
//     });
    
//     await mount(BarcodeCameraDialog, document.body);
//     return promise;
// }
export async function scanBarcode(facingMode="environment") {
    const promise = new Deferred();
    const appForBarcodeDialog = new App(BarcodeCameraDialog,{
        env: owl.Component.env,
        dev: owl.Component.env.isDebug(),
        templates,
        translatableAttributes: ["data-tooltip"],
        translateFn: _t,
        props: {
            onClose: (result={}) => {
                appForBarcodeDialog.destroy();
                if (result.error) {
                    promise.reject({
                        error: result.error
                    });
                } else {
                    promise.resolve(result.barcode);
                }
            }
            ,
            facingMode: facingMode,
        },
    });
    await appForBarcodeDialog.mount(document.body);
    return promise;
}