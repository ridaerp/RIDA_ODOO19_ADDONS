# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle 
#
##############################################################################
from odoo import models,fields, api
from odoo import tools
from odoo.exceptions import UserError, ValidationError

class account_voucher(models.Model):
    _inherit ='account.payment'
    


    cheque_formate_id = fields.Many2one('cheque.setting', 'Cheque Formate', compute='_get_check_formate')
    cheque_no = fields.Char('Cheque No')
    text_free = fields.Char('Free Text')
    partner_text = fields.Char('Partner Title')
    check_date = fields.Date("Check Date")

    @api.depends('journal_id')
    def _get_check_formate(self):
        formate_id = self.env['cheque.setting'].search([('journal_id','=',self.journal_id.id)],limit=1)
        self.cheque_formate_id = formate_id.id

class account_voucher_journal_accounting(models.Model):
    _inherit ='account.journal'
    
    check_template = fields.Many2one('cheque.setting',readonly=True,compute = "_get_template")
    
    def _get_template(self):
        formate_journal_id = self.env['cheque.setting'].search([('journal_id','=',self.id)])
        self.check_template = formate_journal_id
# vim:expandtab:smartindent:tabstop=4:4softtabstop=4:shiftwidth=4:    
