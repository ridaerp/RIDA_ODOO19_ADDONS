from odoo import models, fields, api, tools, _
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta


class hr_payslip(models.Model):
   _inherit = 'hr.payslip'


   def get_loan(self):
      for rec in self:
         array = []
         loan_ids = self.env['hr.loan.line'].search([
               ('employee_id', '=', rec.employee_id.id),
               ('paid', '=', False), ('active', '=', True),
               ('state', '=', 'paid'),
               ('paid_date', '>=', rec.date_from),
               ('paid_date', '<=', rec.date_to),
         ])
         for loan in loan_ids:
               array.append(loan.id)
         rec.loan_ids = array
         return array



   def compute_sheet(self):
      for rec in self:
         rec.get_loan()
         for line in rec.loan_ids:
            if rec.loan:
               line.paid = True
            rec.get_loans_by_type()
         return super(hr_payslip, rec).compute_sheet()
               


