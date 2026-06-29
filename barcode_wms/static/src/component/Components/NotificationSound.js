/** @odoo-module **/

import { Component, useRef, onMounted, onWillUnmount } from "@odoo/owl";

export class NotificationSound extends Component {
    setup() {
        super.setup();
        this.audio = useRef('audio');
        onMounted(async () => {
            this.audio.el.addEventListener('ended', () => { this.props.sound.src = null; });
        });
        onWillUnmount(async () => {
            this.audio.el.removeEventListener('ended', null);
        });
    }
}

NotificationSound.template = 'barcode_wms.NotificationSound';