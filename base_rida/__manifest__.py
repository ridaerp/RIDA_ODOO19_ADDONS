# -*- coding: utf-8 -*-
{
    'name': "base_rida",

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
    'depends': ['base','hr_expense','account','hr','hr_holidays','hr_payroll','hr_work_entry_contract','hr_work_entry_contract_enterprise','hr_attendance'],

    # always loaded
    'data': [
        'security/base_rida_groups.xml',
        'security/ir.model.access.csv',
        'views/line_manager_views.xml',
        'views/hr_menu.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
