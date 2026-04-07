# -*- coding: utf-8 -*-
{
    'name': "Rida - Budget",


    'author': "IMT Team",
    'website': "https://ridagroup.com",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'accounting',
    'version': '19.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account_accountant', 'account_budget', 'hr','material_request','hr_employee_main', 'account_budget_multi_currency'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/account_budget_views.xml',
        'views/account_budget_department_form_views.xml',
        'views/budget_department_views.xml',
        'report/budget_pivot_report.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
