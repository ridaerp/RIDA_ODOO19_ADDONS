# -*- coding: utf-8 -*-
{
    'name': "master_data",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','product','material_request','stock','maintenance_fleet_inherit','acc_workflow', ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/vendor.xml',
        'views/location.xml',
        'views/analytic_account.xml',
        'views/account_account.xml',
        'views/product_category.xml',
        'views/equipment.xml',
        'views/area_request.xml',
        'views/update_area_request.xml',
        'views/update_area_price.xml',
        'views/update_grade_prices.xml',
        'views/update_price_location.xml',
        'data/ir_sequence_data.xml',
    ],
}
