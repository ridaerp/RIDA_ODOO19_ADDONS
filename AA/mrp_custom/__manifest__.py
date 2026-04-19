# -*- coding: utf-8 -*-
{
    'name': "Production  Custom",

    'summary': """
        Production_Custom""",

    'description': """
       Rida Production Custom 
    """,

    'author': "Rida Group",
    'website': "",

    'category': 'MRP',
    'version': '0.1',

    # any module necessary for this one to work correctly...
    'assets': {
       
        'web.assets_backend': [
            'mrp_custom/static/src/hide_button.xml',
            'mrp_custom/static/src/mrp_menu_dialog_extend.js',
            'mrp_custom/static/src/components/assay_request_button/assay_request_button.js',
            'mrp_custom/static/src/components/assay_request_button/assay_request_button.xml',
            'mrp_custom/static/src/components/assay_request_button/metalab_request_button.js',
            'mrp_custom/static/src/components/assay_request_button/metalab_request_button.xml',
            'mrp_custom/static/src/components/assay_request_button/pregnant_sample_result.js',
            'mrp_custom/static/src/components/assay_request_button/pregnant_sample_button.xml',
        ],
        'shopfloor.assets': [
            'mrp_custom/static/src/components/assay_request_button/assay_request_button.js',
            'mrp_custom/static/src/components/assay_request_button/assay_request_button.xml',
            'mrp_custom/static/src/components/assay_request_button/metalab_request_button.js',
            'mrp_custom/static/src/components/assay_request_button/metalab_request_button.xml',
            'mrp_custom/static/src/components/assay_request_button/pregnant_sample_result.js',
            'mrp_custom/static/src/components/assay_request_button/pregnant_sample_button.xml',

        ],
},


    'depends': ['base','mrp','stock','mrp_workorder','maintenance_fleet_inherit','material_request'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/record_rule.xml',
        'security/security_groups.xml',
        
        'data/ir_sequences_data.xml',
        'data/ir_cron_data.xml',
        # 'views/t.xml',
        'views/work_order.xml',
        'views/Cell.xml',
        'views/parameter_log_sheets_view.xml',
        'views/product.xml',
        'views/chemical_lab_veiw.xml',
	    



    ],
    

    
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'application': True,
}
