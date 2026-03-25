# -*- coding: utf-8 -*-
{
    'name': "rida_hr_overtime",

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
    'depends': ['base', 'base_rida', 'material_request'],

    # always loaded
    'data': [
        'data/ir_sequence_data.xml',
        'security/securit_rules.xml',
        'security/ir.model.access.csv',
        'views/overtime_config.xml',
        'views/views.xml',
        'views/overtime_auth.xml',
        'views/overtime_sectionhead_view.xml',
        'wizard/overtime_report_views.xml',


    ],
}
