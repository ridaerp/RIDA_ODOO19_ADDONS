# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle 
#
##############################################################################

{
    'name': 'Dynamic Print Cheque - Check writing',
     'sequence':1,
    'category': 'Generic Modules/Accounting',
    'description': """
         App will  configure and print cheque/check Dynamically for any bank with different Cheque format.

Cheque print, check print, check writing, bank check print, check dynamic, bank cheque, cheque dynamic, cheque printing, bank cheque, dynamic print cheque, cheque payment, payment check, 

    Dynamic print cheque
    How can we create dynamic cheque
    Dynamic cheque print
    Accounting voucher
    Cheque acconting voucher
    Odoo dynamic cheque
    Odoo dynamic cheque print
    Print dynamic cheque
    Odoo11 dynamic cheque print
    Print cheque
    Print cheque odoo
    Dynamically print cheque
    Dynamic cheque
    Cheque accounting voucher
    Accounting cheque voucher
    Dynamic bank cheque
    Dynamic bank cheque print in odoo
    Odoo dynamic cheque
    Odoo dynamic bank cheque
    Odoo dynamic bank cheque print
    cheque Printer
    check print
    dynamic check print
    check printing configuration
    cheque printing
    payment cheque print
    cheque payment print 
Dynamic print cheque

How can we create dynamic cheque

Dynamic cheque print

Accounting voucher

Cheque acconting voucher

Odoo dynamic cheque

Odoo dynamic cheque print

Print dynamic cheque

Odoo11 dynamic cheque print

Print cheque

Print cheque odoo

Dynamically print cheque

Dynamic cheque

Cheque accounting voucher

Accounting cheque voucher

Dynamic bank cheque

Dynamic bank cheque print in odoo

Odoo dynamic cheque

Odoo dynamic bank cheque

Odoo dynamic bank cheque print

Odoo Dynamic Print Cheque

Manage Dynamic Print Cheque

Odoo Manage Dynamic Print Cheque

Odoo How can we create dynamic cheque

Odoo Dynamic cheque print

Odoo Accounting voucher

Odoo Cheque acconting voucher

Odoo Print dynamic cheque

Manage Odoo11 dynamic cheque print

Odoo Print cheque

Manage Print cheque odoo

Odoo Dynamically print cheque

Odoo Dynamic cheque

Odoo Cheque accounting voucher

Odoo Accounting cheque voucher

Odoo Dynamic bank cheque

Manage Dynamic bank cheque print in odoo

Cheque Writing

Odoo Cheque Writing

Configure and print cheque/check for any bank with different Cheque format

Odoo Configure and print cheque/check for any bank with different Cheque format

Adjust all possible values like customer name, date, amount, amount in words, signature based on your needs/Format.

Odoo Adjust all possible values like customer name, date, amount, amount in words, signature based on your needs/Format.

Print bold format values.

Odoo Print bold format values.

Adjust font size.

Odoo Adjust font size.

Adjust font color.

Odoo Adjust font color.

Print Free text on bottom.

Odoo Print Free text on bottom.

Print Stub Lines with cheque no in below half page.

Odoo Print Stub Lines with cheque no in below half page.

Print journal entires with transatation in below half page.

Odoo Print journal entires with transatation in below half page.

Dynamic Print Check

Odoo Dynamic Print Check

Manage Dynamic Print check

Odoo Manage Dynamic Print Check


    """,
    'author': 'DevIntelle Consulting Service Pvt.Ltd', 
    'website': 'http://www.devintellecs.com',
    'summary':'odoo App will  configure and print cheque/check Dynamically for any bank with different Cheque format',
    'depends': ['account','account_check_printing','account_edi'],
    'data': [
        'security/ir.model.access.csv',
        # 'wizard/print_cheque_wizard_views.xml',
        'views/report_print_cheque.xml',
        'views/report_menu.xml',
        'views/cheque_setting_view.xml',
        'views/account_vocher_view.xml',
        # 'views/account_check_print.xml',
    ],
    'demo': [],
    'test': [],
    'css': [],
    'qweb': [],
    'js': [],
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'price':35.0,
    'currency':'EUR',
    'live_test_url':'https://youtu.be/usddBBEk1Tg',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
