# -*- coding: utf-8 -*-
{
    'name': "qhse_form",

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
    'depends': ['base', 'material_request','mail','qhse','base_rida', 'master_data'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'security/security_groups.xml',
        'security/security_rules.xml',
        'views/hot_work_permit.xml',
        'views/work_permit_view.xml',
        'views/confined_space_permit_views.xml',
        'views/blasting_space_permit_views.xml',
        'views/excavation_work_permit.xml',
        'views/height_work_permit.xml',
        'views/lifting_work_permit.xml',
        'views/loto_work_permit.xml',
        'views/work_site_view.xml',
        'views/ppe_complain_view.xml',
        # 'views/ppe_replacement_view.xml',
        'views/ppe_deductiont_view.xml',
        'views/ppe_medical_view.xml',
        'views/ppe_inspection_view.xml',
        'views/ppe_receipt_view.xml',
        'views/ppe_distribution_view.xml',
        # 'views/ppe_replacement_views.xml',
        'data/ir_sequence_data.xml',
    ],
}
