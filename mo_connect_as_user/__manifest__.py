# -*- coding: utf-8 -*-
{
    'name': 'Connect As User',
    'summary': 'Login as any user directly from the user form without a password',
    'description': 'Allows administrators with a dedicated security group to connect '
                   'as any system user with a single click, without needing their password.',
    'author': 'Mohamed Shaker',
    'website': 'www.mohamedshaker.com',
    'category': 'Administration',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mo_connect_as_user/static/src/js/connect_as_systray.js',
            'mo_connect_as_user/static/src/xml/connect_as_systray.xml',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}

