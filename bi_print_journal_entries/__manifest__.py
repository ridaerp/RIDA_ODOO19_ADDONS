# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Print Journal Entries Report in Odoo',
    'version': '19.0.0.0',
    'category': 'Accounting',
    'license': 'OPL-1',
    'summary': 'Allow to print pdf report of Journal Entries.',
    'description': """
    Allow to print pdf report of Journal Entries.
    journal entry
    print journal entry 
    journal entries
    print journal entry reports
    account journal entry reports
    journal reports
    account entry reports

    
""",
    'price': 000,
    'currency': 'EUR',
    'author': 'BROWSEINFO',
    'website': 'https://www.browseinfo.com/demo-request?app=bi_print_journal_entries&version=19&edition=Community',
    'depends': ['base','account'],
    'data': [
            'report/report_journal_entries.xml',
            'report/report_journal_entries_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'live_test_url':'https://www.browseinfo.com/demo-request?app=bi_print_journal_entries&version=19&edition=Community',
    "images":["static/description/Banner.gif"],
}

