# -*- coding: utf-8 -*-
{
    'name': "material_request",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',


    # any module necessary for this one to work correctly

    'depends': ['base', 'mail','maintenance','base_rida', 'account', 'accountant', 'purchase', 'mrp', 'project','purchase_stock','stock_last_purchase_price','purchase_requisition','stock','stock_account', 'purchase_discount','mrp_landed_costs','stock_landed_costs_currency','sale', 'mrp', 'base_rida', 'purchase_order_delivery_status',],
    # 'hr_employee_main',


    # always loaded
    'data': [
        'security/groups.xml',
        'security/mr_security.xml',
        'security/ir.model.access.csv',
        'wizards/reassigned_supply.xml',
        'wizards/po_reject.xml',
        'views/material_request.xml',
        'views/purchase_view.xml',
        'views/issuance_request.xml',
        'views/purchase_requestion.xml',
        'views/non_accept_material.xml',
        'views/stock_picking_MR_custom_material.xml',
        'views/product_template.xml',
        'views/users.xml',
        'views/payment_request_view.xml',
        'views/views.xml',
        'views/contrac_new_view.xml',
        'views/accounting_purchase.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',

        'report/mr_RFQ_template.xml',
        ############added by ekhas code
        'views/ore_rock_purchases_view.xml',
        'report/purchase_contract.xml',
        'report/mr_print_pdf.xml',
        'wizards/advance_payments_wizard_view.xml',
        'views/weight_unit_view.xml',
        'views/chemical_view.xml',
        'views/meta_lab.xml',
        'views/inspection.xml',
        'views/completion_certificate_views.xml',
        'report/incentive_report.xml',
        'views/supplier_evaluation.xml',
        'views/technical_evaluation.xml',
        'views/lowest_price_evaluation.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    


}
