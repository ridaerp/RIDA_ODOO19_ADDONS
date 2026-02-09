# -*- coding: utf-8 -*-
{
    'name': "Accounting Custom",

    'summary': """
        account_custom""",

    'description': """
       Rida account_custom
    """,

    'author': "Appness Tech",
    'website': "http://app-ness.com",


    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly...

    # 'depends': ['base','hr_timesheet','base_rida', 'account','account_reports','stock_landed_costs','material_request','hr_recruitment','sales_team'],
    'depends': ['base','base_rida','sale','account','hr_overtime','account_reports','stock_landed_costs','material_request','dev_print_cheque',
                'account_asset','hr_recruitment','project','hr_timesheet'],
    # always loaded
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        # 'data/mail_template_data.xml',
        # 'data/ir_cron_data.xml'
        'views/asset_view.xml',
        'views/asset_tag_views.xml',  # Include the views file
        'views/new.xml',
        'views/payment.xml',
        'views/journal_new_view.xml',
        # 'views/accounting_report.xml',
        # 'wizard/cogs.xml',
        # 'wizard/profit_loss.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}
