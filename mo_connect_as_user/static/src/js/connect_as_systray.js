/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { session } from "@web/session";

export class ConnectAsReturnSystray extends Component {
    setup() {
        this.state = useState({
            originalUid: session.connect_as_original_uid || false,
            originalName: session.connect_as_original_name || "",
        });
    }

    get isConnectAsSession() {
        return !!this.state.originalUid;
    }

    get originalName() {
        return this.state.originalName;
    }

    onClickReturn() {
        window.location.href = "/web/connect_as/return";
    }
}

ConnectAsReturnSystray.template = "mo_connect_as_user.ReturnSystray";

export const systrayItem = {
    Component: ConnectAsReturnSystray,
};

registry.category("systray").add("mo_connect_as_user.return", systrayItem, { sequence: 1 });
