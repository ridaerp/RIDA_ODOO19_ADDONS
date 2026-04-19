# from openerp import models, fields, api , _
from odoo import models, fields, api, _
# from openerp.exceptions import except_orm, Warning, RedirectWarning, UserError
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

class hr_payslip(models.Model):
    _name='hr.payslip'
    _inherit='hr.payslip'

    overtime = fields.Float("Overtime", readonly=True)
    site_overtime = fields.Float("Site Overtime", readonly=True)
    employee_type = fields.Selection(string='Employee type', selection=[('hq', 'HQ Staff'), ('site', 'Site Staff')],required=True, related = "employee_id.rida_employee_type")
    
    def compute_sheet(self):
        for payslip in self:
            # Ensure single record processing
            payslip.ensure_one()
            if payslip.employee_type == 'hq':
                self.compute_overtime()
        else:
            self.compute_site_overtime()
        res = super(hr_payslip,self).compute_sheet()
        return res

    def compute_overtime(self):
        for rec in self:
            ovt = 0.0
            pay_obj = self.env['hr.payslip']
            pay_id = rec.id
            emp_id = rec.employee_id.id
            ovtm_obj = self.env['hr.over.time']
            ovtm_ids = ovtm_obj.search([('employee_id','=',emp_id),('date','>=',rec.date_from),('date','<=',rec.date_to),('state','=','paid')])
            for ovtm_id in ovtm_ids:
                ovt += ovtm_id.net_overtime
            rec.overtime = ovt

    def compute_site_overtime(self):
        for rec in self:
            ovt = 0.0
            pay_obj = self.env['hr.payslip']
            pay_id = rec.id
            emp_id = rec.employee_id.id
            ovtm_obj = self.env['hr.site.overtime']
            ovtm_ids = ovtm_obj.search([('employee_id','=',emp_id),('date','>=',rec.date_from),('date','<=',rec.date_to),('state','=','paid')])
            for ovtm_id in ovtm_ids:
                ovt += ovtm_id.net_overtime
            rec.site_overtime = ovt
