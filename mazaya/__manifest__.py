# -*- coding: utf-8 -*-

{
    'name': 'Rida HR: Mazaya',
    'description': '',
    'author': 'Appness Technology',
    'depends': ['base','hr_payroll','base_rida', 'hr_overtime', 'hr_contract_grade_base'],
    'data': [
        'security/ir.model.access.csv',     
        'views/mazaya_view.xml',
        'views/menu_item.xml',
    ],
    'application': True,
}