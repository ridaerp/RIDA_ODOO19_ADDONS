/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

class AssayRequestFormController extends FormController {
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
                _t("The Chemical assay  has successfully been created."),
                { type: "success" }
            );
        }
        return super.onRecordSaved(...arguments);
    }
}


export const AssayRequestFormView = {
    ...formView,
    Controller: AssayRequestFormController,
};

// Register custom view type
registry.category("views").add("material_request.view_chemical_request_form", AssayRequestFormView);



// /** @odoo-module **/

// import { _t } from "@web/core/l10n/translation";
// import { registry } from "@web/core/registry";
// import { useService } from "@web/core/utils/hooks";
// import { FormController } from "@web/views/form/form_controller";
// import { formView } from "@web/views/form/form_view";

// class AssayRequestFormController extends FormController {
//     setup() {
//         super.setup();
//         this.notification = useService("notification");
//         this.rpc = useService("rpc");
//     }

//     async onClickGenerate() {
//         if (!this.model.root.resId) {
//             this.notification.add(_t("Please save the record before generating samples."), { type: "warning" });
//             return;
//         }

//         try {
//             await this.rpc("/chemical_request/generate", {
//                 args: [[this.model.root.resId]],
//             });

//             this.model.load();
//             this.notification.add(_t("Samples generated successfully."), { type: "success" });

//         } catch (error) {
//             this.notification.add(_t("Error generating samples: ") + error.message, { type: "danger" });
//         }
//     }

//     async onClickSubmit() {
//         if (!this.model.root.resId) {
//             this.notification.add(_t("Please save the record before submitting."), { type: "warning" });
//             return;
//         }

//         try {
//             await this.rpc("/chemical_request/submit", {
//                 args: [[this.model.root.resId]],
//             });

//             this.model.load();
//             this.notification.add(_t("Request submitted successfully."), { type: "success" });

//         } catch (error) {
//             this.notification.add(_t("Error submitting request: ") + error.message, { type: "danger" });
//         }
//     }
// }

// export const AssayRequestFormView = {
//     ...formView,
//     Controller: AssayRequestFormController,
// };

// registry.category("views").add("material_request.view_chemical_request_form", AssayRequestFormView);
