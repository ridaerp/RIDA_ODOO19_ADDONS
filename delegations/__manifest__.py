# -*- coding: utf-8 -*-
{
    'name': "Rida HR :Delegations",
    'summary': """
        Access Rights Delegation
        """,
    'author': "Appness Technology Co.Ltd.",
    'website': "http://www.app-ness.com",
    'category': 'hr',
    'version': '1.1',
    'price': 39,
    'currency': 'USD',
    'depends': ['hr', 'base_rida','material_request'],
    'support': 'support@app-ness.com',
    'data': [
        'data/ir_cron.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/delegation_views.xml',
        # 'views/res_config_views.xml',
    ],
    'images': [
        'static/description/delegations.png',
    ]
}
