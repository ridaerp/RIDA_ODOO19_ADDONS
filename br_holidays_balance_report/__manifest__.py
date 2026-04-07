

{
    'name': 'HR Balance Leave Report',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Time Off',
    'summary': 'Allocated balance, taken leaves and remaining balance per leave type for each employee',
    'description': 'User Can view Allocated balance, taken leaves and remaining balance per leave type for '
                   'each employee',
    'author': 'Banibro IT Solutions Pvt Ltd.',
    'company': 'Banibro IT Solutions Pvt Ltd.',
    'website': 'https://banibro.com',
    'license': 'AGPL-3',
    'email': "support@banibro.com",
    'depends': ['hr', 'hr_holidays'],
    'data': [
        'security/balance_report_security.xml',
        'security/ir.model.access.csv',
        'report/leave_balance_report_view.xml'
    ],
    'images': ['static/description/banner.png',
               'static/description/icon.png',],
    'installable': True,
    'application': False,
    'auto_install': False,
}
