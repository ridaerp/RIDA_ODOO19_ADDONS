from odoo import models, fields, api, _
import time
from dateutil.relativedelta import relativedelta
import datetime

from datetime import date

from datetime import datetime, date, time



class MazayaPayroll(models.Model):
    _inherit='hr.payslip'

    
    mazaya_id = fields.Many2one(string='Mazaya',comodel_name='rida.mazaya' ,readonly=True,domain="[('state', '=', 'approved')]")
    mazaya_tax = fields.Float(string='Mazaya Tax',readonly=True,store=True )
    mazaya_total = fields.Float(string='Total Mazaya',readonly=True,store=True )
    mazaya_cash = fields.Float(string='Cash Allowance')
    mazaya_dress = fields.Float(string='Dress Allowance')
    mazaya_midical = fields.Float(string='Medical Allowance')
    mazaya_grant = fields.Float(string='Grant')


    # git mazaya based on company
    @api.constrains('employee_id')
    def onchange_employee(self):
        for rec in self:
            if self.employee_id:
                comp_id = rec.employee_id.company_id.id
                currency_id = rec.employee_id.salary_currency.id
                maza_obj = self.env['rida.mazaya']
                maz_ids = maza_obj.search([('company','=',comp_id),('currency_id', '=', currency_id),('state', '=', 'approved')])
                rec.mazaya_id = maz_ids.id


    def compute_sheet(self):
        self.compute_mazaya()
        # raise UserError('test')
        resource = super(MazayaPayroll,self).compute_sheet()
        return resource

    @api.depends('date_from','mazaya_id')
    def compute_mazaya(self):
        for record in self:
            mazaya_total = mazaya_tax = 0
            Y,m,d = str(record.date_from).split('-')
            months = int(m)
            maz_lin_obj = self.env['rida.mazaya.line']
            basic_sal = record.employee_id.basic_salary
            gross_sal = record.employee_id.payroll_wage

            if record.mazaya_id:
                maz_mon = maz_lin_obj.search([('month','=',months), ('mazaya_id','=',record.mazaya_id.id)])
                if maz_mon:
                    if record.mazaya_id.based_on == 'basic':
                        mazaya_cash = maz_mon.cash_allow * basic_sal /100 # Calcccccccccccccu
                        mazaya_dress = maz_mon.dress_allow * basic_sal /100 # Calcccccccccccccu
                        mazaya_midical = maz_mon.midical_allow * basic_sal /100 # Calcccccccccccccu
                        mazaya_grant = maz_mon.grant_allow * basic_sal /100 # Calcccccccccccccu
                        mazaya_total = maz_mon.new_allow * basic_sal /100 # Calcccccccccccccu
                        mazaya_tax = mazaya_total*maz_mon.tax_allow/100
                    elif record.mazaya_id.based_on =='gross':
                        mazaya_cash = maz_mon.cash_allow * gross_sal /100# Calcccccccccccccu
                        mazaya_dress = maz_mon.dress_allow * gross_sal /100# Calcccccccccccccu
                        mazaya_midical = maz_mon.midical_allow * gross_sal /100# Calcccccccccccccu
                        mazaya_grant = maz_mon.grant_allow * gross_sal /100# Calcccccccccccccu
                        mazaya_total = maz_mon.new_allow * gross_sal /100# Calcccccccccccccu
                        mazaya_tax = mazaya_total*maz_mon.tax_allow/100
                    self.mazaya_cash= mazaya_cash
                    self.mazaya_dress= mazaya_dress
                    self.mazaya_midical= mazaya_midical
                    self.mazaya_grant= mazaya_grant
                    self.mazaya_total= mazaya_total
                    self.mazaya_tax = mazaya_tax

