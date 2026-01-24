# -*- coding: utf-8 -*-
{
    'name': "Rida HR : Employee Directory",
    'summary': """This Module contain employee main profile """,
    'description': """This Module contain employee main profile""",
    'author': "Appness Technology",
    'website': "http://www.appness.net",
    'category': 'HR',
    'version': '14.0.1',
    'sequence': 1,
    # any module necessary for this one to work correctly
    'depends': ['base','hr','account','base_rida','hr_leave_main'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/groups.xml',
        'views/hr_employee.xml',
        'views/trip_permission.xml',
        'views/recruitment_plan.xml',
        'views/recruitment_request.xml',
        # 'views/res_config_setting.xml',
        'data/employee_notification.xml',
        'views/hr_department.xml',
        'views/location.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}