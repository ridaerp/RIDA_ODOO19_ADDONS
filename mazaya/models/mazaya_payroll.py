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

