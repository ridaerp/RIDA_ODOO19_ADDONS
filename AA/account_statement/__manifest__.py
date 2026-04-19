# -*- coding: utf-8 -*-
{
    'name': "Account Statement Report",

    'summary': """
        Account Statement Report
        """,

    'description': """
        
    """,

    'author': "Eng.Ekhlas Mohamed Repot",
    'website': "https://www.linkedin.com/in/eng-ekhlas-mohamed-software-engineer-48ab6596",

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/account_statement_view.xml',
        'reports/account_statement_template_view.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
