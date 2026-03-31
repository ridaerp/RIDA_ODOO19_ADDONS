# -*- coding: utf-8 -*-
{
    'name': "Rida HR: Employee Leaves Management",
    'summary': """Employee Leaves Main """,
    'description': """Employee Leaves Main """,
    'author': "Appness Technology",
    'website': "http://www.appness.net",
    'category': 'HR',
    'version': '1.0',

    'depends': ['base','hr','base_rida','hr_holidays','hr_payroll','accountant',],

    # always loaded
    'data': [
      
      'security/ir.model.access.csv',
      'security/securit_rules.xml',
      'wizard/justification.xml',
      'wizard/transport_report_wizard_view.xml',
      'data/ir_sequence_data.xml',
      'views/holidays_inherit.xml',
      'views/public_holiday.xml',
      'views/autoallocate.xml',
      'views/rotation.xml',
    ],

}
