# -*- coding: utf-8 -*-
{
    'name': "Rida HR : Salary Grade",
    'summary': """Salary Wage By Grade """,
    'description': """Salary Wage By Grade""",
    'author': "Appness Technology",
    'website': "http://www.appness.net",
    'category': 'HR',
    'version': '14.0.1',
    'sequence': 4,
    # any module necessary for this one to work correctly
    'depends': ['hr','hr_payroll','hr_contract_benefit'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/configuration.xml',
        'views/contract_inherit.xml',
        'views/job_band_view.xml',
        'views/travel_zone.xml',
        'views/trip_zone.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
     #   'demo.xml',
    ],
}
