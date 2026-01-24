# -*- coding: utf-8 -*-
{
    'name': "Rida Forms",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "ICT Rida ",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','base_rida','maintenance','material_request','hr_contract_grade_base'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/dr_security.xml',
        'data/ir_sequence_data.xml',
        'views/exit_permission.xml',
        'views/reject_view.xml',
        # 'views/views.xml',
        'views/transportation_request.xml',
        'views/visit_request_view.xml',
        'views/residence_request_view.xml',
        'views/stationary_request_view.xml',
        'views/checkin_camp_view.xml',
        # 'views/template_transportation_request_portal.xml',
        'views/air_request.xml',
        # 'views/meeting_request.xml',
        # 'views/vehicle_request.xml',
        'views/menu_item.xml',
        'views/templates.xml',
        'views/it_custody.xml',
        'views/device_request.xml',
        'views/sim_card.xml',
        'views/sim_card_avaliable.xml',
        'wizards/po_count_wizard.xml',
        'security/ir.model.access.csv',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
