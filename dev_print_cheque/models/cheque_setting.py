# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle 
#
##############################################################################
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class cheque_setting(models.Model):
    _name = 'cheque.setting'
    _description = 'Cheque Setting'

    name = fields.Char('Name', required="1")
    journal_id = fields.Many2one('account.journal',domain = "[('type','=','bank')]")
    font_size = fields.Float('Font Size', default="13", required="1")
    color = fields.Char('Color', default="#000", required="1")
    set_default = fields.Boolean('Default Template', copy=False)
    company_id = fields.Many2one('res.company',string='Company', default=lambda self:self.env.user.company_id.id, required="1")

    is_partner = fields.Boolean('Print Partner', default=True)
    is_partner_bold = fields.Boolean('Font Bold')
    partner_text = fields.Selection([('prefix', 'Prefix'), ('suffix', 'Suffix')], string='Partner Title')
    partner_m_top = fields.Float('Partner From Top', default=130)
    partner_m_left = fields.Float('Partner From Left', default=70)

    print_partner_address = fields.Boolean('Print Customer Address')
    partner_address_top_margin = fields.Float('Address From Top')
    partner_address_left_margin = fields.Float('Address From Left')

    is_date = fields.Boolean('Print Date', default=True)
    date_formate = fields.Selection([('dd_mm', 'DD MM'), ('mm_dd', 'MM DD')], string='Date Formate', default='dd_mm')
    year_formate = fields.Selection([('yy', 'YY'), ('yyyy', 'YYYY')], string='Year Format', default='yy')
    date_m_top = fields.Float('Date From Top', default=90)
    f_d_m_left = fields.Float('First Digit', default=550)
    s_d_m_left = fields.Float('Second Digit', default=560)
    t_d_m_left = fields.Float('Third Digit', default=590)
    fo_d_m_left = fields.Float('Fourth Digit', default=600)
    fi_d_m_left = fields.Float('Fifth Digit', default=625)
    si_d_m_left = fields.Float('Six Digit', default=635)
    se_d_m_left = fields.Float('Seven Digit', default=645)
    e_d_m_left = fields.Float('Eight Digit', default=655)
    
    date_seprator = fields.Char('Seperator')

    is_amount = fields.Boolean('Print Amount', default=True)
    amt_m_top = fields.Float('Amt From Top', default=185)
    amt_m_left = fields.Float('Amt From Left', default=550)
    is_star = fields.Boolean('Print Hash', help="if true then print 3 star before and after Amount", default=True)

    is_currency = fields.Boolean('Print Currency')

    is_amount_word = fields.Boolean('Print Amount Words', default=True)
    is_word_bold = fields.Boolean('Word Font Bold')
    word_in_f_line = fields.Float('Split Words After', default=5,
                                  help="How Many Words You want to print in first line, The rest will go in second line")
    amt_w_m_top = fields.Float('From First Top', default=158.76)
    amt_w_m_left = fields.Float('From First Left', default=70)
    is_star_word = fields.Boolean('Word Print Star', help="if true then print 3 star before and after Words Amount",
                                  default=True)

    amt_w_s_m_top = fields.Float('From Sec Top', default=185)
    amt_w_s_m_left = fields.Float('From Sec Left', default=70)

    is_company = fields.Boolean('Print Company')
    c_margin_top = fields.Float('Company From Top', default=280)
    c_margin_left = fields.Float('Company From Left', default=560)

    print_journal = fields.Boolean('Print Journal')
    journal_margin_top = fields.Float('Journal From Top', default=700)
    journal_margin_left = fields.Float('Journal From Left', default=10)

    is_stub = fields.Boolean('Print Stub')
    stub_margin_top = fields.Float('Stub From Top', default=400)
    stub_margin_left = fields.Float('Stub From Left', default=10)

    is_cheque_no = fields.Boolean('Print Cheque No')
    cheque_margin_top = fields.Float('Cheque From Top', default=50)
    cheque_margin_left = fields.Float('Cheque From Left', default=520)

    is_free_one = fields.Boolean('Print Free Text One')
    f_one_margin_top = fields.Float('One From Top', default=255)
    f_one_margin_left = fields.Float('One From Left', default=70)

    is_free_two = fields.Boolean('Print Free Text Two')
    f_two_margin_top = fields.Float('Two From Top', default=255)
    f_two_margin_left = fields.Float('Two From Left', default=300)

    is_acc_pay = fields.Boolean('Print A/C PAY', default=True)
    acc_pay_m_top = fields.Float('Pay From Top', default=50)
    acc_pay_m_left = fields.Float('Pay From Left', default=50)
    
    is_f_line_sig = fields.Boolean('Print Signature')
    f_sig_m_top = fields.Float('Sign From Top', default=255)
    f_sig_m_left = fields.Float('Sign From Left', default=510)
    
    is_s_line_sig = fields.Boolean('Second Print Signature')
    s_sig_m_top = fields.Float('From Top', default=350)
    s_sig_m_left = fields.Float('From Left', default=510)
    
    is_print_footer_text = fields.Boolean('Print Footer Text')
    is_footer_text_bold = fields.Boolean('Footer Font Bold')
    cheque_footer_text = fields.Char('Footer Text')
    footer_font_size = fields.Integer('Footer Font Size', default=13)
    footer_m_top = fields.Float('Footer From Top', default=240)
    footer_m_left = fields.Float('Footer From Left', default=240)
    
    
    @api.constrains('set_default', 'company_id')
    def _check_description(self):
        for line in self:
            if line.set_default:
                line_ids = self.env['cheque.setting'].search([('set_default','=',True),('company_id','=',line.company_id.id)])
                if len(line_ids) > 1:
                    raise ValidationError("One Company have one default cheque template")





# vim:expandtab:smartindent:tabstop=4:4softtabstop=4:shiftwidth=4:
