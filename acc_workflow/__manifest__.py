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

    'depends': ['base','base_rida','sale','account', 'hr_timesheet', 'hr_recruitment','hr_overtime','account_reports','stock_landed_costs','material_request','dev_print_cheque',
                'account_asset','project', 'rida_migration'],
    # always loaded
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'views/asset_view.xml',
        'views/asset_tag_views.xml',
        'views/new.xml',
        'views/payment.xml',
        'views/journal_new_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}
