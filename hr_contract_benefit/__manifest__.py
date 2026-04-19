# -*- coding: utf-8 -*-
{
    'name': "Appness HR : Contract Benefits",
    'summary': """Contract Benefits""",
    'description': """Contract Beneftis""",
    'author': "Appness Technology",
    'website': "http://www.appness.net",
    'category': 'HR',
    'version': '13.0.1',
    'sequence': 3,
    # any module necessary for this one to work correctly
    'depends': ['base','hr_payroll','hr_employee_main',],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/grade_benefit.xml',
        'views/hr_employee.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}