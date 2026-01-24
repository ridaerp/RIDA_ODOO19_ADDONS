# -*- coding: utf-8 -*-

{
    'name': 'Rida HR: Mazaya',
    'description': '',
    'author': 'Appness Technology',
    'depends': ['hr_work_entry_contract' , 'hr_contract', 'base','hr_payroll','base_rida', 'hr_overtime',],
    'data': [
        'security/ir.model.access.csv',     
        'views/mazaya_view.xml',
        'views/menu_item.xml',
    ],
    'application': True,
}