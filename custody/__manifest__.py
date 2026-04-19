# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Custody',
    'summary': """
        This Module Manage custody in your company """,

    'description': """
        This Module Manage custody in your company from payment until clearing either partially or fully cleared
    """,
     'author': 'Appness Technology',
    'category': 'Accounting',
    'sequence': 6,

    'depends': ['base','base_rida','account','analytic','hr','material_request','hr_employee_main'],
    'data': [
        'security/custody_security.xml',
        'security/ir.model.access.csv',
        # 'wizard/custody_clear.xml',
        'views/account_custody_view.xml',
        'views/account_custody_manager.xml',
        'views/clearance.xml',
        'data/ir_sequence_data.xml',
        'data/journal.xml',
        'report/account_custody_report_template.xml',
        'report/account_custody_report.xml'

    ],
    'installable': True,
    'website': 'https://www.appness.net',
}
