# -*- coding: utf-8 -*-
{
    'name': "PDCs Management",
    'summary': """Account PDC Management""",
    'description': """This module allows you to manage customers and vendors post-dated checks""",
    'category': 'Accounting',
    'author': 'Appness Technology',
    'company': 'Appness Technology',
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'accounting',
     # any module necessary for this one to work correctly
    'depends': ['account','account_payment','account_accountant'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/account_pdc_view.xml',
        'views/account_payment_view.xml',
        'wizard/invoice_payment_wizard.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
