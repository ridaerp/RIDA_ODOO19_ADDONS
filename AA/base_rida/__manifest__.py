# -*- coding: utf-8 -*-
{
    'name': "base_rida",

    'summary': """
       Base Rida Module""",

    'description': """
        Base Rida Module
    """,

    'author': "Rida",

    'category': 'Base',
    
    'version': '0.1',

    'depends': ['base','hr_expense','account','accountant', 'hr','hr_holidays','hr_payroll','hr_attendance'],

    'data': [
        'security/base_rida_groups.xml',
        'security/ir.model.access.csv',
        'views/line_manager_views.xml',
        'views/hr_menu.xml',

    ],
}
