{
    'name': 'Employee Service',
    'version': '1.0',
    'summary': 'View Employee and Leaves from main Odoo HR',
    'author': 'Rida Group',
    'category': 'Human Resources',
    'depends': ['hr', 'hr_holidays','delegations','rida_hr_overtime','hr_employee_main'
                ,'hr_loan_base','hr_salary_advance','br_holidays_balance_report','hr_leave_main','rida_forms'],
    'data': [
        # 'security/ir.model.access.csv',
        # 'security/group.xml',
        # 'views/employee_service_views.xml',
        # 'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
