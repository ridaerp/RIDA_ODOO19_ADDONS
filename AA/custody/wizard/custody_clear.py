# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class CustodyClearWizardLine(models.TransientModel):

    _name = "custody.clear.wizard.line"
    account_id = fields.Many2one('account.account')
    amount = fields.Float()
    desc = fields.Char("Description")
    wizard_id = fields.Many2one('custody.clear.wizard')

class CustodyClearWizard(models.TransientModel):

    _name = "custody.clear.wizard"

    @api.model
    def _default_amount(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        custody = self.env['account.custody'].browse(active_ids)
        return custody.residual

    def _default_currency(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        custody = self.env['account.custody'].browse(active_ids)
        return custody.currency_id.id

    def _default_journal(self):
        journal = self.env['account.journal'].search([['code', '=', 'CLR']], limit=1)
        return journal.id

    account_id = fields.Many2one('account.account', "Clearing Account")
    amount = fields.Float(string='Amount', required=True, default=_default_amount)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=_default_currency)
    journal_id = fields.Many2one('account.journal', default=_default_journal)
    communication = fields.Char(string='Note')
    account_ids = fields.One2many('custody.clear.wizard.line', 'wizard_id', string='Accounts')

    @api.constrains('amount')
    def _check_amount(self):
        if not self.amount > 0.0:
            raise ValidationError('The amount must be strictly positive.')

    def validate(self):

        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        custody = self.env['account.custody'].browse(active_ids)

        partner = custody.employee_id.address_home_id

        journal = self.journal_id
        credit_line = debit_line = []
        ctx = dict(self._context)
        for rec in self:
            if len(rec.account_ids) < 1:
                raise ValidationError("Please select at least one account!")
            amount = 0.0
            for line in rec.account_ids:
                amount += line.amount
            if amount > custody.residual:
                raise ValidationError("Clearing amount cannot be greater than custody residual. (" + str(custody.residual) +")")
            move = self.env['account.move'].search([['custody_id','=', custody.id],['state','=','draft']], limit=1)

            desc = rec.communication or " "
            if move:
                move = move

            else:
                move = self.env['account.move'].create({
                    'journal_id': journal.id,
                    'ref':  custody.name + "-" + desc,
                    'custody_id': custody.id,
                })
            AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False)

            credit_line = AccountMoveLine.search([['move_id','=', move.id],['account_id','=', custody.account_id.id]],limit=1)
            if credit_line:
                credit_line.update({
                    'credit': credit_line.credit + amount
                })
            else:
                AccountMoveLine.create({
                    'name': custody.employee_id.name,
                    'move_id': move.id,
                    'account_id': custody.account_id.id,
                    'credit': amount,
                    'partner_id': partner.id,
                })

            for line in rec.account_ids:
                AccountMoveLine.create({
                    'name': line.desc or custody.employee_id.name,
                    'move_id': move.id,
                    'account_id': line.account_id.id,
                    'debit': line.amount,
                    'analytic_account_id': custody.analytic_id.id if custody.analytic_id else False,
                    'partner_id': partner.id,
#                    'custody_id': custody.employee_id.address_home_id.id
                })
            move.post()

            to_reconcile = custody.move_id.line_ids.filtered(lambda l: l.account_id == custody.account_id)
            to_reconcile += move.line_ids.filtered(lambda l: l.account_id == custody.account_id)
            to_reconcile.reconcile()

            custody.clear_amount += amount
            # changing amount to be new_amount to make custody state = cleard after adding amedment amount in extened custody module
            # if custody.clear_amount == custody.amount:
            if custody.clear_amount == custody.amount:
                custody.state = "cleared"
            else:
                custody.state = "partially_cleared"

        return {'type': 'ir.actions.act_window_close'}
