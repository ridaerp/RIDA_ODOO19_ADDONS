import { MrpMenuDialog } from "@mrp_workorder/mrp_display/dialog/mrp_menu_dialog";
import { patch } from "@web/core/utils/patch";

patch(MrpMenuDialog.prototype, {
    async block() {
        // 1. استخراج البيانات من السجل الحالي (Work Order)
        const record = this.props.record;

        // جلب معرف مركز العمل (Work Center)
        let wcId = null;
        if (record.data.workcenter_id) {
            // التعامل مع أشكال البيانات المختلفة [id, name] أو {res_id: id}
            wcId = Array.isArray(record.data.workcenter_id)
                   ? record.data.workcenter_id[0]
                   : (record.data.workcenter_id.res_id || record.data.workcenter_id);
        }

        // جلب معرف أمر العمل (Work Order)
        const woId = record.resId || record.data.id;

        // 2. بناء السياق (Context) مع تنظيف أي قيم قديمة
        const customContext = {
            'default_workcenter_id': wcId,
            'default_workorder_id': woId,
            'active_id': woId,
            'active_model': 'mrp.workorder',
        };

        console.log("🛠️ محاولة الحظر ببيانات:", customContext);

        // 3. استدعاء الأكشن مع التأكد من تمرير السياق في المكانين (الرئيسي والإضافي)
        await this.action.doAction('mrp.act_mrp_block_workcenter_wo', {
            additionalContext: customContext,
            props: {
                context: customContext, // تمرير مباشر للـ props في Odoo 19
            },
            onClose: async () => {
                if (this.props.reload) {
                    await this.props.reload();
                }
            },
        });

        // 4. إغلاق النافذة
        if (this.props.close) {
            this.props.close();
        }
    }
});