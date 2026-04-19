# -*- coding: utf-8 -*-

{
    'name': "Warehouse Restrictions",

    'summary': """
         Warehouse and Stock Locations, Picking types and picking Restriction on Users.""",

    'description': """
        This Module Restricts the User from Accessing Warehouse and Process Stock Moves other than allowed to Warehouses and Stock Locations.
    """,

    'author': "DVIT, Techspawn Solutions",
    'website': "http://www.dvit.me",

    'category': 'Warehouse',

    'depends': ['base', 'stock'],

    'data': [
        'views/users.xml',
        'security/security.xml',
        'security/ir.model.access.csv',

    ],
    "images": [
        'static/description/banner.png'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
}
