# -*- coding: utf-8 -*-
import time
from datetime import datetime
from odoo import fields, models, api, _
from odoo.exceptions import  UserError, ValidationError
from odoo import exceptions


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sal_account_id = fields.Many2one('account.account',related='company_id.sal_account_id', string='Salary Advance Account',store=True, readonly=False)

class Company(models.Model):
    _inherit = "res.company"
    sal_account_id = fields.Many2one('account.account', string='Salary Advance Account',store=True )



class SalaryAdvanceAccount(models.Model):
    _inherit = "salary.advance"



    state = fields.Selection([('draft', 'Draft'),
                              ('hr_officer', 'HR Officer Approval'),
                              ('hr_manager', 'HR payroll Manager Approval'),
                              ('site_manager', 'Operation Director'),
                              ('finance', 'Finance Approval'),
                              ('internal_audit', 'Internal Audit Approval'),
                              ('ccso', 'COO Approval'),
                              ('accountant', 'Accountant Approval'),
                              ('approve', 'Approved'),
                              ('paid', 'Paid'),
                              ('cancel', 'Cancelled'),
                              ('reject', 'Rejected')], string='Status', default='draft', track_visibility='onchange')
    debit = fields.Many2one('account.account', string='Debit Account')
    credit = fields.Many2one('account.account', string='Credit Account')
    journal_account_for_salary = fields.Many2one('account.move')
    journal = fields.Many2one('account.journal', string='Journal')
    move_id = fields.Many2one('account.move', string="Journal Entry ", readonly=True)
    pay_id = fields.Many2one('account.payment', string="Payment ", readonly=True)
    # account_id = fields.Many2one("account.account", string="Employee Account")
    register_payment = fields.Boolean(default=False)
    account_id = fields.Many2one('account.account', string='Salary Advance Account',
                                              related='company_id.sal_account_id')




    def update_activities(self):
        for rec in self:
            users = []
            # rec.activity_unlink(['hr_salary_advance.mail_act_approval'])
            if rec.state not in ['draft','hr_officer','hr_manager','ceo','approve','reject']:
                continue
            message = ""
            if rec.state == 'hr_manager':
                users = self.env.ref('base_rida.rida_hr_manager_notify').user_ids
                message = "Approve"

            if rec.state == 'finance':
                users = self.env.ref('account.group_account_user').user_ids
                message = "Confirm"

            elif rec.state == 'reject':
                users = [self.create_uid]
                message = "Cancelled"
            for user in users:
                self.activity_schedule('hr_salary_advance.mail_act_approval', user_id=user.id, note=message)




    def approve_request_acc_dept(self):
        """This Approve the employee salary advance request from accounting department.
                   """
        salary_advance_search = self.search([('employee_id', '=', self.employee_id.id), ('id', '!=', self.id),
                                             ('state', '=', 'approve')])
        current_month = datetime.strptime(str(self.date), '%Y-%m-%d').date().month
        for each_advance in salary_advance_search:
            existing_month = datetime.strptime(str(each_advance.date), '%Y-%m-%d').date().month
            if current_month == existing_month:
                raise UserError('Advance can be requested once in a month')
         # if not self.journal:
         #        raise UserError("You must enter Journal to register the payment")
        if not self.account_id:
                raise UserError('You must enter Account to Employee Address to register the payment')
        if not self.move_id:
                raise UserError("You must register payment first")
        self.state = 'approve'



    def action_post(self):
        for record in self:
            po = self.env['account.payment'].search([('ref', '=', record.name)])
            po.write({'state': 'posted'})
            record.state = "paid"





    def action_register_payment(self):
        for rec in self:
            if not rec.journal:
                raise UserError("You must enter Journal to register the payment")
            if not rec.account_id:
                raise UserError('You must enter Account to Employee Address to register the payment')




            create_payment = {
                'payment_type': 'outbound',
                'partner_type': 'customer',
                'partner_id': rec.employee_id.employee_partner_id.id,
                'destination_account_id':rec.account_id.id,
                'company_id': rec.company_id.id,
                'amount': rec.advance,
                'currency_id': rec.currency_id.id,
                'ref': rec.name,
                'journal_id': rec.journal.id,
            }
            po = self.env['account.payment'].create(create_payment)
            rec.move_id = po.move_id.id
            rec.register_payment = True
            po.action_post()

            rec.state = "paid"
            for rec in self:
                line_ids = []
                line_ids.append(
                    (0, 0, {'debit': 0, 'credit': rec.advance, 'partner_id': rec.employee_id.employee_partner_id.id
                        , 'account_id': rec.account_id.id, 'currency_id': self.company_id.currency_id.id,


                            }))
                line_ids.append((0, 0, {'debit': rec.advance, 'credit': 0
                    , 'account_id': rec.account_id.id,

                                        }))
                self.journal_account_for_salary = self.env['account.move'].sudo().create({
                    'ref': rec.name,
                    'date': rec.date,
                    'narration': f' Salary Advance For {rec.employee_id.name}',
                    'move_type': 'entry',
                    'currency_id': self.company_id.currency_id.id,
                    'invoice_date': fields.Date.today(),
                    'line_ids': line_ids,
                    'company_id': self.company_id.id,
                })
            return po


    def button_payment(self):
        return {
            'name': _('Payment'),
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'account.payment',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('ref', '=', self.name)],
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


