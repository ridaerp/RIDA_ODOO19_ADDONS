# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError


class AccountPDC(models.Model):
    _name = 'account.pdc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = "PDC"
    _order = 'maturity_date desc'

    name = fields.Char('Reference')
    type = fields.Selection([('customer', 'Customer'), ('vendor', 'Vendor')])
    maturity_date = fields.Date('Maturity Date')
    clear_date = fields.Date(string="Clearance Date")
    partner_id = fields.Many2one('res.partner', 'Partner')
    journal_id = fields.Many2one('account.journal', 'Clearing Journal',
                                 domain=[('type', 'in', ('bank', 'cash')), ('is_check_journal', '!=', True)])
    payment_id = fields.Many2one('account.payment', 'Payment')
    state = fields.Selection([('draft', 'New'), ('reject', 'Rejected'), ('clear', 'Cleared')], default='draft',
                             track_visibility="onchange")
    amount = fields.Monetary()
    currency_id = fields.Many2one('res.currency', "Currency")
    move_id = fields.Many2one('account.move', "Journal Entry")
    company_id = fields.Many2one('res.company', "Company", default=lambda self: self.env.user.company_id)
    note = fields.Text()
    check_no = fields.Char('Check Number')

    def clear(self):
        self.ensure_one()
        AccountMove = self.env['account.move']
        AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False)
        if not self.clear_date:
            raise UserError('Please add clearance date!')
        if not self.journal_id:
            raise UserError('Select Clearing Journal')
        Move = AccountMove.create({
            'journal_id': self.journal_id.id,
            'ref': 'Check Clearing: ' + self.name,
            'date': self.clear_date
        })
        debit_line = {'date': self.clear_date}
        credit_line = {'date': self.clear_date}


        # old code v 14
        # #if self.type == 'customer':
        #     debit_line['account_id'] = self.journal_id.default_account_id.id
        #     credit_line['account_id'] = self.payment_id.journal_id.payment_credit_account_id.id
        # else:
        #     credit_line['account_id'] = self.journal_id.default_account_id.id
        #     debit_line['account_id'] = self.payment_id.journal_id.payment_debit_account_id.id
        #


        if self.type == 'customer':
            debit_line['account_id'] =  self.journal_id.default_account_id.id
            credit_line['account_id'] = self.payment_id.journal_id.default_account_id.id
        else:
            credit_line['account_id'] =  self.journal_id.default_account_id.id
            debit_line['account_id'] = self.payment_id.journal_id.default_account_id.id






        debit_line['partner_id'] = self.partner_id.id
        debit_line['name'] = 'Check Clearing: ' + self.name
        debit_line['debit'] = self.amount
        debit_line['credit'] = 0.0
        debit_line['move_id'] = Move.id

        credit_line['partner_id'] = self.partner_id.id
        credit_line['name'] = 'Check Clearing: ' + self.name
        credit_line['debit'] = 0.0
        credit_line['credit'] = self.amount
        credit_line['move_id'] = Move.id

        AccountMoveLine.create(debit_line)
        AccountMoveLine.create(credit_line)
        Move.action_post()
        self.state = 'clear'
        self.move_id = Move.id

    def reject(self):
        self.ensure_one()
        partner_account = False
        if self.type == 'customer':
            partner_account = self.payment_id.partner_id.property_account_receivable_id
        else:
            partner_account = self.payment_id.partner_id.property_account_payable_id
        #
        # for move in self.payment_id.move_line_ids.mapped('move_id'):
        #     move._reverse_moves()
        #     reversal_move_id = self.env['account.move'].search([('reversed_entry_id', '=', move.id)])
        #
        #     reversal_move_id.post()
        #     move.line_ids.sudo().remove_move_reconcile()
        #     raise UserError(self.payment_id.move_line_ids.filtered(lambda r: r.account_id == partner_account))
        #     self.payment_id.move_line_ids.filtered(lambda r: r.account_id == partner_account).reconcile()
        # self.payment_id.state = 'cancel'
        # self.state = 'reject'

        reverse_id = 0

        for move in self.payment_id.move_id.line_ids.mapped('move_id'):
            # if self.payment_id.invoice_ids:
            move.line_ids.sudo().remove_move_reconcile()
            move._reverse_moves()
            reverse_id = self.env['account.move'].search([('reversed_entry_id', '=', move.id)])
            reverse_id.action_post()
            to_reconcile = self.env['account.move.line'].search([('move_id', 'in', [move.id, reverse_id.id]),
                                                                 ('account_id', '=', partner_account.id)])
            to_reconcile.reconcile()
            for l in move.line_ids:
                l.payment_id = False
            self.move_id = reverse_id
        self.payment_id.state = 'draft'
        self.move_id = reverse_id
        self.state = "reject"
