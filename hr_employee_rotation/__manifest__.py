# -*- coding: utf-8 -*-
{
    'name': "Rida HR: Employee Movement",
    'summary': """Employee Movement """,
    'description': """Employee Rotation""",
    'author': "Appness Technology",
    'website': "http://www.app-ness.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'HR',
    'version': '14.0.1',
    'sequence': 5,

    # any module necessary for this one to work correctly
    'depends': ['base','hr','hr_contract', 'o_employee_cost_center'],

    # always loaded
    'data': [
      'security/ir.model.access.csv',
    #    'security/record_rule.xml',
      'data/mail_data.xml',
      'views/employee_rotation.xml',
      'views/hr_employee_extension.xml',
      'views/employee_rotation_extension.xml',      
    ],
    # only loaded in demonstration mode
    'demo': [
   #     'demo.xml',
    ],
}