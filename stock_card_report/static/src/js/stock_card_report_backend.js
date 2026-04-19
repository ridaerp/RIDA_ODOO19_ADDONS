/** @odoo-module **/

import { Component, xml, onWillStart, useState, markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class StockCardReportBackend extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        // action context from ir.actions.client
        const ctx = (this.props && this.props.action && this.props.action.context) || {};

        this.state = useState({
            loading: true,
            html: "",
        });

        // Build the same given_context you used before
        this.given_context = (ctx.context || {});
        this.given_context.active_id = ctx.active_id || (this.props.action.params && this.props.action.params.active_id);
        this.given_context.model = ctx.active_model || "report.stock.card.report";
        this.given_context.ttype = ctx.ttype || false;

        this.odoo_context = ctx;

        onWillStart(async () => {
            await this.loadHtml();
        });
    }

    async loadHtml() {
        try {
            this.state.loading = true;
            const model = this.given_context.model;

            // calls: model.get_html([given_context])
            const result = await this.orm.call(model, "get_html", [this.given_context], {
                context: this.odoo_context,
            });

            this.state.html = markup(result?.html || "");

        } catch (e) {
            this.notification.add(`Failed to load report HTML: ${e.message || e}`, { type: "danger" });
            throw e;
        } finally {
            this.state.loading = false;
        }
    }

    async printPdf() {
        await this._print("qweb-pdf");
    }

    async exportXlsx() {
        await this._print("xlsx");
    }

    async _print(reportType) {

        const model = this.given_context.model;
        const activeId = this.given_context.active_id;

        if (!activeId) {
            this.notification.add("No active_id found for this report.", { type: "warning" });
            return;
        }

        const action = await this.orm.call(model, "print_report", [activeId, reportType], {
            context: this.odoo_context || {},
        });

        if (!action) {
            this.notification.add("No action returned from server.", { type: "danger" });
            return;
        }

        action.context = action.context || this.odoo_context || {};

        await this.actionService.doAction(action, { context: this.odoo_context || {} });
    }
}

StockCardReportBackend.template = xml`
    <div class="o_stock_card_report_backend">
        <div class="d-flex align-items-center justify-content-between mb-3">
            <h3 class="m-0">Stock Card Report</h3>

            <div class="btn-group">
                <button type="button" class="btn btn-secondary" t-on-click="printPdf" t-att-disabled="state.loading">
                    Export PDF
                </button>
                <button type="button" class="btn btn-primary" t-on-click="exportXlsx" t-att-disabled="state.loading">
                    Export XLSX
                </button>
            </div>
        </div>

        <t t-if="state.loading">
            <div class="o_view_nocontent_smiling_face">Loading…</div>
        </t>
        <t t-else="">
            <!-- Render html returned from python -->
            <div class="o_stock_card_report_content" t-out="state.html"/>
        </t>
    </div>
`;

registry.category("actions").add("stock_card_report_backend", StockCardReportBackend);

export default StockCardReportBackend;
