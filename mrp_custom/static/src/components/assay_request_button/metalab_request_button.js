/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

class METLABRequestFormController extends FormController {
    setup() {
        super.setup();
        this.notification = useService("notification");
    }

    async onWillSaveRecord(record) {
        this.savingRecordId = record.resId;
        return super.onWillSaveRecord(...arguments);
    }

    async onRecordSaved(record) {
        if (record.resId !== this.savingRecordId) {
            this.notification.add(
                _t("The  Metallurgical has successfully been created."),
                { type: "success" }
            );
        }
        return super.onRecordSaved(...arguments);
    }
}


export const METLABRequestFormView = {
    ...formView,
    Controller: METLABRequestFormController,
};

// Register custom view type
registry.category("views").add("material_request.metallurgical_request_forms", METLABRequestFormView);
