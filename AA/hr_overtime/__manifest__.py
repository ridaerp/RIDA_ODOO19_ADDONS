# -*- coding: utf-8 -*-
{
    'name': "Rida HR: HR Overtime",
    'summary': """This module will manage the employee overtime in human resources,
        fully integrated with payrol """,
    'description': """This module will manage the employee overtime in human resources,
        fully integrated with payroll.
    """,
    'category': 'HR',
    'version': '13.0.1',
    'license': 'LGPL-3',
    'author': 'Appness Technology',
    'company': 'Appness Technology',
    'website': 'https://www.appness.net',
    'depends': ['base_rida', 'base', 'hr_payroll','hr_contract_benefit'],
    'data': [
        # 'security/groups.xml',
        'security/ir.model.access.csv',
        'security/record_rule.xml',
        # 'data/hr_overtime_data.xml',
        'data/mail_data.xml',
        'views/overtime.xml',
        'views/site_overtime.xml',
        'views/overtime_all_confirm.xml',
        'views/overtime_config.xml',
        'views/payroll.xml',
        'views/hr_employee.xml',
        # 'wizard/hr_overtime_wizard.xml',
        'report/reports_view.xml',
        'report/hr_overtime_report_summary_pdf_view.xml',


    ],
}