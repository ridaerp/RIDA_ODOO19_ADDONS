{
    'name': "maintenance_fleet_inherit",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "RIDA ICT/Ekhlas Mohamed",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr_employee_main','fleet','maintenance','maintenance_equipment_status','material_request','base_maintenance','base_maintenance_group','mrp','account_asset'],

    # always loaded
    'data': [
        'data/ir_cron.xml',
        'security/security_group.xml',
        'security/ir.model.access.csv',
        'data/maintenance_stage.xml',
        'views/maintenance_inherit.xml',
        'views/fleet_inherit.xml',
        'views/templates.xml',
        'views/maintenance_veiw.xml',
        'views/vechile_request_view.xml',
        'views/equipment_plan_log_view.xml',
        'views/fleet_operation_view.xml',
        'wizard/daily_report.xml',
        'wizard/daily_availability_report.xml',
        'wizard/oil_consumption_view.xml',


    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
# -*- coding: utf-8 -*-
