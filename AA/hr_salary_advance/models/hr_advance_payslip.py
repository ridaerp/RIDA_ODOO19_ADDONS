# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields
from odoo.exceptions import UserError


class SalaryRuleInput(models.Model):
    _inherit = 'hr.payslip'

    def get_inputs(self, contract_ids, date_from, date_to):
        """This Compute the other inputs to employee payslip.
                           """
        res = super(SalaryRuleInput, self).get_inputs(contract_ids, date_from, date_to)
        adv_salary = self.env['salary.advance'].search([('employee_id', '=', res.employee_id.id)])
        for adv_obj in adv_salary:
            current_date = date_from.month
            date = adv_obj.date
            existing_date = date.month
            if current_date == existing_date:
                state = adv_obj.state
                amount = adv_obj.advance
                for result in res:
                    if state == 'paid' and amount != 0 and result.get('code') == 'SAR':
                        result['amount'] = amount
        return res

    salary_advance = fields.Float(string="Salary Advance",readonly=True)

    def get_salary_advance(self):
        for payslip in self:
            from_date = payslip.date_from
            to_date = payslip.date_to
            adv_salary = self.env['salary.advance'].search([
                ('employee_id', '=', payslip.employee_id.id),
                ('state', '=', 'paid'),
                ('date', '>=', from_date),
                ('date', '<=', to_date)
            ])
            amount = 0
            for adv in adv_salary:
                amount += adv.advance

            payslip.salary_advance = amount
            for rec in adv_salary:
                  if rec.sudo().journal_account_for_salary.state != 'posted':
                      rec.sudo().journal_account_for_salary.sudo().action_post()


    def compute_sheet(self):
        self.get_salary_advance()
        super(SalaryRuleInput, self).compute_sheet()



