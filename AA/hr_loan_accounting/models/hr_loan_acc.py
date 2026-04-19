# -*- coding: utf-8 -*-
from email.policy import default
import time
from odoo import models, api, fields, _
from odoo.exceptions import UserError
from datetime import date



class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    loan_account_id = fields.Many2one('account.account',related='company_id.loan_account_id', string='Loan Account',store=True, readonly=False)

class Company(models.Model):
    _inherit = "res.company"
    loan_account_id = fields.Many2one('account.account', string='Loan Account',store=True )




class HrLoanAcc(models.Model):
    _inherit = 'hr.loan'



    employee_account_id = fields.Many2one('account.account', string='Salary Advance Account',
                                              related='company_id.loan_account_id')


    treasury_account_id = fields.Many2one('account.account', string="Treasury Account")
    journal_id = fields.Many2one('account.journal', string="Payment Journal")
    entry_count = fields.Integer(string="Entry Count", compute='compute_entery_count')
    move_id = fields.Many2one('account.move', string="Entry Journal", readonly=True)
    employee_code = fields.Char(string='Employee Code', related="employee_id.emp_code")
    rida_employee_type = fields.Selection(related="employee_id.rida_employee_type")
    register_payment = fields.Boolean(default=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('hr_officer', 'HR Officer Approval'),
        ('hr_approve', 'HR Manager Approval'),
        ('site_manager', 'Operation Director Approval'),
        ('finance', 'Finance Approval'),
        ('internal_audit', 'Internal Audit Approval'),
        ('ccso', 'COO Approval'),
        ('c_level', 'C level Approval'),
        ('accountant', 'Accountant Approval'),
        ('approve', 'Approved'),
        ('paid', 'Paid'),
        ('refuse', 'Refused'),
    ], string="State", default='draft', track_visibility='onchange', copy=False)

    def compute_entery_count(self):
        count = 0
        entry_count = self.env['account.move.line'].search_count([('loan_id', '=', self.id)])
        self.entry_count = entry_count

    def action_create_entries(self):
        """This create account move for request.
            """
        if not self.employee_account_id or not self.treasury_account_id or not self.journal_id:
            raise UserError("You must enter employee account & Treasury account and journal to create journal entries ")
        else:
            timenow = time.strftime('%Y-%m-%d')
            for loan in self:
                amount = loan.loan_amount
                loan_name = loan.employee_id.name
                partner_id = loan.employee_id.employee_partner_id.id
                reference = loan.name
                journal_id = loan.journal_id.id
                debit_account_id = loan.employee_account_id.id
                credit_account_id = loan.treasury_account_id.id

                Move = self.env['account.move']
                MoveLine = self.env['account.move.line'].with_context(check_move_validity=False)
                vals = {
                    'narration': loan_name,
                    'ref': reference,
                    'partner_id': partner_id,
                    'journal_id': journal_id,
                    'date': timenow,

                }
                move_id = Move.create(vals)

                debit_vals = {
                    'name': loan_name,
                    'account_id': debit_account_id,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'date': timenow,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                    'loan_id': loan.id,
                    'move_id': move_id.id,
                }
                credit_vals = {
                    'name': loan_name,
                    'account_id': credit_account_id,
                    'journal_id': journal_id,
                    'partner_id': partner_id,
                    'date': timenow,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'loan_id': loan.id,
                    'move_id': move_id.id,
                }

                MoveLine.create(debit_vals)
                MoveLine.create(credit_vals)

                self.write({'move_id': move_id.id})
                move_id.post()
            self.write({'state': 'paid'})
        return True

    def manager_approve(self):
        for rec in self:
            if rec.rida_employee_type == 'hq':
                rec.state = 'finance'
            else:
                rec.state = 'site_manager'
        return True

    def action_site_approve(self):
        for rec in self:
            rec.state = 'finance'
        return True

    def finance_action_approve(self):
        for rec in self:
            rec.state = 'internal_audit'
        return True

    def internal_audit_action_approve(self):
        for rec in self:
            rec.state = 'ccso'
        return True

    def ccso_approve(self):
        for rec in self:
            rec.state = 'accountant'

    def accountant_action_approve(self):
        for rec in self:
            rec.state = 'approve'
        return True

    def accountnt_action_refuse(self):
        for rec in self:
            if rec.rida_employee_type == 'site':
                rec.state = 'site_manager'
            else:
                rec.state = "ccso"

    def action_correct_privous_loan_account(self):
        loan_ids=self.env['hr.loan'].sudo().search([('state','=','paid'),('company_id', '=',  self.env.company.id)])
        for rec in loan_ids:
                if rec.id ==312:
                    account = self.env['account.account'].search([('id', '=', 92)], limit=1)
                    rec.employee_account_id=account.id
                if rec.id ==316:
                    account = self.env['account.account'].search([('id', '=', 49)], limit=1)
                    rec.employee_account_id = account.id
                if rec.id ==323:
                    account = self.env['account.account'].search([('id', '=', 1352)], limit=1)
                    rec.employee_account_id = account.id




    def action_correct(self):
        loan_ids=self.env['hr.loan'].sudo().search([('state','=','paid'),('company_id', '=',  self.env.company.id)])
        for loan_id in loan_ids:
                for loan in loan_id.loan_line_ids:
                    if not loan.sudo().journal_id:
                        if loan.paid_date >= date(2024, 9, 1):
                            print('>>>>>>>>>>>.   inside',loan_id.name,loan.paid_date)
                        # if loan.paid_date >= date.today():
                            amount = loan.paid_amount
                            line_ids = []
                            line_ids.append(
                                (0, 0, {'debit': 0, 'credit': amount, 'partner_id': loan.sudo().loan_id.sudo().employee_id.user_partner_id.sudo().id
                                    , 'account_id': loan.sudo().loan_id.sudo().employee_account_id.id, 'currency_id': loan.sudo().loan_id.company_id.sudo().currency_id.id,
                                        'analytic_account_id': loan.loan_id.sudo().employee_id.analytic_account_id.id,
                                        'loan_id': loan.sudo().loan_id.id,
                                        }))

                            line_ids.append((0, 0, {'debit': amount, 'credit': 0 , 'account_id': loan.sudo().loan_id.sudo().employee_account_id.id,
                                                    'loan_id': loan.loan_id.id,
                                                    }))
                            move_line = self.env['account.move'].sudo().create({
                                'ref': loan.sudo().loan_id.name,
                                'date': loan.paid_date,
                                'narration': f' Loan For {loan.sudo().loan_id.sudo().employee_id.name}',
                                'move_type': 'entry',
                                'currency_id': loan.loan_id.sudo().company_id.sudo().currency_id.id,
                                'invoice_date': fields.Date.today(),
                                'line_ids': line_ids,
                                'company_id': loan.loan_id.sudo().company_id.id,
                            })
                            loan.journal_id = move_line.id



    def action_register_payment(self):
        for rec in self:
            if not self.employee_account_id:
                raise UserError("You must enter employee account to register payment")
            if not self.journal_id:
                raise UserError("You must enter journal to register payment")
            create_payment = {
                'payment_type': 'outbound',
                'partner_type': 'customer',
                'partner_id': rec.employee_id.user_partner_id.id,
                'destination_account_id': rec.employee_account_id.id,
                'amount': rec.loan_amount,
                'ref': rec.name,
                'journal_id': rec.journal_id.id,
            }
            po = self.env['account.payment'].create(create_payment)
            rec.move_id = po.move_id.id
            rec.register_payment = True
            po.action_post()
            rec.state = "paid"
            #### Journals For Loan Installemens
            for loan in self.loan_line_ids:
                amount = loan.paid_amount
                line_ids = []
                line_ids.append((0, 0, {'debit': 0, 'credit': amount, 'partner_id': rec.employee_id.user_partner_id.id
                    , 'account_id': rec.employee_account_id.id, 'currency_id': self.company_id.currency_id.id,
                                        'analytic_distribution': {rec.sudo().employee_id.sudo().analytic_account_id.id: 100},
                                        'loan_id': rec.id,
                                        }))
                line_ids.append((0, 0, {'debit': amount, 'credit': 0
                    , 'account_id': rec.employee_account_id.id,
                                        'loan_id': rec.id,
                                        }))
                move_line = self.env['account.move'].sudo().create({
                    'ref': rec.name,
                    'date': loan.paid_date,
                    'narration': f' Loan For {rec.employee_id.name}',
                    'move_type': 'entry',
                    'currency_id': self.company_id.currency_id.id,
                    'invoice_date': fields.Date.today(),
                    'line_ids': line_ids,
                    'company_id': self.company_id.id,
                })
                loan.journal_id = move_line.id
            return po

    def button_payment(self):
        return {
            'name': _('Payment'),
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'account.payment',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('memo', '=', self.name)],
        }

    def button_journal_entries(self):
        return {
            'name': ('Journal Entiry'),
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('ref', '=', self.name)],
        }

    def button_action_post(self):
        for record in self:
            po = self.env['account.payment'].search([('memo', '=', record.name)])
            po.action_post()
            record.state = "paid"

    def reject_hr_officer(self):
        for rec in self:
            rec.state = 'draft'

    def reject_hr_manager(self):
        for rec in self:
            rec.state = 'hr_officer'

    def reject_finance_manager(self):
        for rec in self:
            rec.state = 'hr_approve'

    def reject_internal_audit(self):
        for rec in self:
            rec.state = 'finance_manager'

    def reject_site(self):
        for rec in self:
            rec.state = 'internal_audit'

    def reject_ccso(self):
        for rec in self:
            rec.state = 'internal_audit'
