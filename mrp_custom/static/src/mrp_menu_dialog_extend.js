/** @odoo-module **/
import { MrpMenuDialog } from "@mrp_workorder/mrp_display/dialog/mrp_menu_dialog";
import { patch } from "@web/core/utils/patch";

patch(MrpMenuDialog.prototype, {
    async block() {
        const record = this.props.record;
        const wcId = record.data.workcenter_id?.id;
        const woId = record.resId;
        // const moId = record.data.production_id?.id;

        const options = {
            additionalContext: {
                default_workcenter_id: wcId,
                default_workorder_ref_id: woId,
                // default_production_ref_id: moId,    

            },
            onClose: async () => {
                await this.props.reload();
            },
        };

        await this.action.doAction("mrp.act_mrp_block_workcenter_wo", options);
        this.props.close();
    }
});