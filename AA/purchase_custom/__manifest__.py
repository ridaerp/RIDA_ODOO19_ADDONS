# -*- coding: utf-8 -*-
{
    'name': "purchase_custom",

    'summary': """
        purchase_custom""",

    'description': """
       Rida purchase_custom
    """,

    'author': "Appness Tech",
    'website': "http://app-ness.com",


    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    # 'depends': ['base', 'account', 'purchase', 'nus_base', 'hr', 'stock'],
    'depends': ['base','base_rida', 'account', 'purchase', 'payment', 'account_budget', 'hr', 'stock','material_request'],

    # always loaded
    'data': [
        # 'security/sm_security.xml',
        'security/contract_security.xml',
        'security/ir.model.access.csv',
        # 'views/purchase_contract.xml',
        # 'views/external_service_management.xml',
        'views/contract.xml',
        # 'views/res_config_settings_views.xml',
        # 'views/purchase_bill.xml',
        'views/change_contract.xml',
        'views/payment_request.xml',
        # 'views/purchase_order.xml',
        # 'views/partner_views.xml',
        'report/ore_reports.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}
