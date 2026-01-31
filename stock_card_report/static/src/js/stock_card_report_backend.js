/** @odoo-module **/

throw new Error("stock_card_report_backend.js LOADED");


import { registry } from "@web/core/registry";
import { AbstractAction } from "@web/legacy/js/core/abstract_action";
import { Widget } from "@web/legacy/js/core/widget";

const ReportWidget = Widget;

const StockCardReportBackend = AbstractAction.extend({
    hasControlPanel: true,

    events: {
        "click .o_stock_card_reports_print": "print",
        "click .o_stock_card_reports_export": "export",
    },

    init(parent, action) {
        this._super(...arguments);
        this.actionManager = parent;
        this.given_context = {};
        this.odoo_context = action.context || {};
        this.controller_url = this.odoo_context.url;

        if (this.odoo_context.context) {
            this.given_context = this.odoo_context.context;
        }

        this.given_context.active_id =
            this.odoo_context.active_id || (action.params && action.params.active_id);

        this.given_context.model = this.odoo_context.active_model || false;
        this.given_context.ttype = this.odoo_context.ttype || false;
    },

    willStart() {
        return Promise.all([this._super(...arguments), this.get_html()]);
    },

    set_html() {
        const self = this;
        let def = Promise.resolve();
        if (!this.report_widget) {
            this.report_widget = new ReportWidget(this, this.given_context);
            def = this.report_widget.appendTo(this.$(".o_content"));
        }
        def.then(function () {
            self.report_widget.$el.html(self.html);
        });
    },

    start() {
        this.set_html();
        return this._super(...arguments);
    },

    get_html() {
        const self = this;
        const defs = [];
        return this._rpc({
            model: this.given_context.model,
            method: "get_html",
            args: [self.given_context],
            context: self.odoo_context,
        }).then(function (result) {
            self.html = result.html;
            defs.push(self.update_cp());
            return $.when.apply($, defs);
        });
    },

    update_cp() {
        if (this.$buttons) {
            const status = {
                breadcrumbs: this.actionManager.get_breadcrumbs(),
                cp_content: { $buttons: this.$buttons },
            };
            return this.update_control_panel(status);
        }
    },

    do_show() {
        this._super(...arguments);
        this.update_cp();
    },

    print() {
        const self = this;
        this._rpc({
            model: this.given_context.model,
            method: "print_report",
            args: [this.given_context.active_id, "qweb-pdf"],
            context: self.odoo_context,
        }).then(function (result) {
            self.do_action(result);
        });
    },

    export() {
        const self = this;
        this._rpc({
            model: this.given_context.model,
            method: "print_report",
            args: [this.given_context.active_id, "xlsx"],
            context: self.odoo_context,
        }).then(function (result) {
            self.do_action(result);
        });
    },

    canBeRemoved() {
        return Promise.resolve();
    },
});

registry.category("actions").add("stock_card_report_backend", StockCardReportBackend);

export default StockCardReportBackend;
