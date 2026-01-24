# -*- coding: utf-8 -*-
{
    'name': "Rida HR : hr_payroll_workflow",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Scrum Team",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base_rida', 'hr_payroll', 'hr_payroll_account','mazaya','hr_loan_base','hr_loan_accounting','hr_salary_advance','hr_salary_advance_accounting'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security_rules.xml',
        'views/hr_payroll_workflow.xml',
        'wizard/hr_payroll_payslips_by_employees_views.xml'
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
