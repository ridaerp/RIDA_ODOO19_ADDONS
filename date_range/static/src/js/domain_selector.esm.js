/** @odoo-module **/

import { domainFromTreeDateRange, treeFromDomainDateRange } from "./condition_tree.esm";
import { onWillStart, useChildSubEnv } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

const ARCHIVED_DOMAIN = `[("active", "in", [True, False])]`;

patch(DomainSelector.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.dateRanges = [];
        this.dateRangeTypes = [];
        useChildSubEnv({ domain: this });

        onWillStart(async () => {
            this.dateRanges = await this.orm.call("date.range", "search_read", []);
            this.dateRangeTypes = await this.orm.call("date.range.type", "search_read", []);
        });
    },

    getFieldDef(fieldName) {
        if (this.props?.getFieldDef) {
            return this.props.getFieldDef(fieldName);
        }
        if (this.fieldDefs && fieldName in this.fieldDefs) {
            return this.fieldDefs[fieldName];
        }
        return undefined;
    },

    async onPropsUpdated(p) {
        await super.onPropsUpdated(...arguments);

        let domain = null;
        let isSupported = true;
        try {
            domain = new Domain(p.domain);
        } catch {
            isSupported = false;
        }

        if (!isSupported) {
            this.tree = null;
            this.defaultCondition = null;
            this.fieldDefs = {};
            this.showArchivedCheckbox = false;
            this.includeArchived = false;
            return;
        }

        this.tree = treeFromDomainDateRange(domain, {
            getFieldDef: this.getFieldDef.bind(this),
            distributeNot: !p.isDebugMode,
        });
    },

    getOperatorEditorInfo(node) {
        const info = super.getOperatorEditorInfo(node);
        const fieldDef = this.getFieldDef(node.path);
        const dateRanges = this.dateRanges;
        const dateRangeTypes = this.dateRangeTypes.filter((dt) => dt.date_ranges_exist);

        patch(info, {
            extractProps({ value: [operator] } = {}) {
                const props = super.extractProps(...arguments);
                const safeOperator = typeof operator === "string" ? operator : "";
                const isDateField =
                    fieldDef && (fieldDef.type === "date" || fieldDef.type === "datetime");
                const hasDateRanges = isDateField && dateRanges.length;
                const hasDateRangeTypes = isDateField && dateRangeTypes.length;

                props.options = props.options || [];

                if (hasDateRanges) {
                    if (safeOperator.includes("daterange")) {
                        props.options = props.options.filter((opt) => opt[0] !== safeOperator);
                    }
                    if (safeOperator === "daterange") {
                        props.value = "daterange";
                    }
                    if (!props.options.some((opt) => opt[0] === "daterange")) {
                        props.options.push(["daterange", "daterange"]);
                    }
                }

                if (hasDateRangeTypes) {
                    const selectedDateRange = dateRangeTypes.find(
                        (rangeType) =>
                            rangeType.id === Number(safeOperator.split("daterange_")[1])
                    );

                    if (selectedDateRange) {
                        props.value = safeOperator;
                    }

                    const extraOptions = dateRangeTypes.map((rangeType) => [
                        `daterange_${rangeType.id}`,
                        `in ${rangeType.name}`,
                    ]);

                    for (const option of extraOptions) {
                        if (!props.options.some((opt) => opt[0] === option[0])) {
                            props.options.push(option);
                        }
                    }
                }

                return props;
            },

            isSupported([operator] = []) {
                const nodeOperator =
                    node && typeof node.operator === "string" ? node.operator : "";
                const selectedOperator =
                    typeof operator === "string" ? operator : "";

                if (nodeOperator.includes("daterange")) {
                    return selectedOperator.includes("daterange");
                }
                return super.isSupported(...arguments);
            },
        });

        return info;
    },

    update(tree) {
        const archiveDomain = this.includeArchived ? ARCHIVED_DOMAIN : `[]`;
        const domain = tree
            ? Domain.and([domainFromTreeDateRange(tree), archiveDomain]).toString()
            : archiveDomain;
        this.props.update(domain);
    },
});