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


    


    # def _create_payment_vals_from_wizard(self,first_batch_result):
    #     payment_vals = {
    #         'date': self.payment_date,
    #         'amount': self.amount,
    #         'payment_type': self.payment_type,
    #         'partner_type': self.partner_type,
    #         'ref': self.communication,
    #         'journal_id': self.journal_id.id,
    #         'currency_id': self.currency_id.id,
    #         'partner_id': self.partner_id.id,
    #         'partner_bank_id': self.partner_bank_id.id,
    #          'payment_method_id': self.payment_method_line_id.payment_method_id.id,
    #         'destination_account_id': self.line_ids[0].account_id.id,
    #         'cheque_formate_id':self.cheque_formate_id.id or '',
    #         'text_free':self.text_free or '',
    #         'partner_text':self.partner_text or '',
    #         'cheque_no':self.cheque_no or '',
    #         ################add by ekhlas ##################3
    #         'check_date':self.check_date,
    #
    #     }
        #
        # if not self.currency_id.is_zero(self.payment_difference) and self.payment_difference_handling == 'reconcile':
        #     payment_vals['write_off_line_vals'] = {
        #         'name': self.writeoff_label,
        #         'amount': self.payment_difference,
        #         'account_id': self.writeoff_account_id.id,
        #     }
        # return payment_vals
      
