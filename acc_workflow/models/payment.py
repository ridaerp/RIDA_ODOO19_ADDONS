# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError



class AccountPayment(models.Model):

    _inherit='account.payment'
    
    ovearseas_id=fields.Many2one("overseas.payment","Overseas Payment")

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    _description = 'Register Payment'


    ##########comment by ekhlas########################
    
    # cheque_formate_id = fields.Many2one('cheque.setting', 'Cheque Formate', default='_get_check_formate')
    # check_date = fields.Date(string='Date')
    # partner_text = fields.Char('Partner Title')
    # cheque_no = fields.Char('Cheque No')
    # text_free = fields.Char('Free Text')


    # @api.depends('journal_id')
    # def _get_check_formate(self):
    #     formate_id = self.env['cheque.setting'].search([('set_default','=',True),('company_id','=',company_id)],limit=1)
    #     self.cheque_formate_id = formate_id.id



    cheque_formate_id = fields.Many2one('cheque.setting', 'Cheque Formate', compute='_get_check_formate')
    cheque_no = fields.Char('Cheque No')
    text_free = fields.Char('Free Text')
    partner_text = fields.Char('Partner Title')
    check_date = fields.Date("Check Date")

    @api.depends('journal_id')
    def _get_check_formate(self):
        formate_id = self.env['cheque.setting'].search([('journal_id','=',self.journal_id.id)],limit=1)
        self.cheque_formate_id = formate_id.id
