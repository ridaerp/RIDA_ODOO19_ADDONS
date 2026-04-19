/** @odoo-module */

import { MrpMenuDialog } from "@mrp_workorder/mrp_display/dialog/mrp_menu_dialog";
import { patch } from "@web/core/utils/patch";

patch(MrpMenuDialog.prototype, {
    /**
     * Overwrites the original block method.
     */
    block() {
        // This console log helps confirm your patched method is being called.
        console.log("🔁 Custom Patched Block Method Called (Odoo 17)");

        const options = {
            additionalContext: {
                default_workcenter_id: this.props.record.data.workcenter_id[0],
                // default_is_block: '1',
                // Add your custom context keys here, as in your initial custom class attempt
                // default_workorder_id: this.props.record.resId, // Assuming resId holds the workorder ID
                default_workorder_ref_id: this.props.record.resId, // Assuming resId holds the workorder ID
                custom_param: 'my_custom_value',
            },

            onClose: async () => {
                // 'this.props.reload' is a function passed via props to the dialog
                await this.props.reload();
            },
        };


        // 'this.action' is a service hooked in the original component's setup method.
        // It should be available here.
        this.action.doAction('mrp.act_mrp_block_workcenter_wo', options);

        // 'this.props.close' is a function passed via props to close the dialog
        this.props.close();
    }
});