# -*- coding: utf-8 -*-
{
    'name': "Rida Stock Custom",

    'summary': """
        Rida Stock Custom""",

    'description': """
       Rida custom product reordering rules,...
    """,

    'author': "Appness Tech",
    'website': "http://app-ness.com",


    'category': 'Inventory/Inventory',
    'version': '0.1',

    # any module necessary for this one to work correctly
    # 'depends': ['base', 'account', 'purchase', 'nus_base', 'hr', 'stock'],
    'depends': ['stock','account', 'stock_picking_batch','base_rida','stock_last_purchase_price','acc_workflow','material_request','stock_intercompany_transfer'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/stock_orderpoint_custom.xml',
        'views/stock_picking_custom_material.xml',
        'views/scrap_custom_view.xml',
        'views/adjustment_custom_view.xml',
        'report/report_deliveryslip.xml',

    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
