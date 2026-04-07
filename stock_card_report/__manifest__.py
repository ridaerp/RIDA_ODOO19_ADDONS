# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Stock Card Report",
    "summary": "Add stock card report on Inventory Reporting.",
    "category": "Warehouse",
    "website": "https://github.com/OCA/stock-logistics-reporting",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["web", "stock", "date_range", "report_xlsx_helper"],
    "data": [
        "security/ir.model.access.csv",
        "data/paper_format.xml",
        "data/report_data.xml",
        "reports/stock_card_report.xml",
        "wizard/stock_card_report_wizard_view.xml",
    ],

    "assets": {
        "web.assets_backend": [
            "stock_card_report/static/src/css/report.css",
            "stock_card_report/static/src/js/stock_card_report_backend.js",
        ],
    },
    "installable": True,
}
