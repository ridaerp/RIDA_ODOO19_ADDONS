# -*- coding: utf-8 -*-
{
    'name': "Appness HR: Employee Cost Center",
    'summary': """Link Employee to accounting module through cost centers""",
    'description': """Link Employee to accounting module through cost centers""",
    'category': 'HR',
    'version': '14.0.1',
    'author': "Appness Technology",
    'website': "http://www.appness.net",
    # any module necessary for this one to work correctly
    'depends': ['hr','hr_employee_main', 'account'],
    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/costcenter_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}