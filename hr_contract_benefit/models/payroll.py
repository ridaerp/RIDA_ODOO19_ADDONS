# # -*- coding: utf-8 -*-
# from odoo import models, fields, api
# from odoo.exceptions import   UserError
# import time
# import datetime
# class HrPayslipEmployee(models.TransientModel):
#     _inherit="hr.payslip.employees"

#     def compute_sheet(self):
#         self.ensure_one()
#         active_id = self._context.get('active_id')
#         date_from = self.env['hr.payslip.run'].search([('id','=',active_id)]).date_start
#         date_to = self.env['hr.payslip.run'].search([('id','=',active_id)]).date_end
#         slp_start = datetime.datetime.strftime(date_from, '%Y-%m-%d')
#         slp_end = datetime.datetime.strftime(date_to, '%Y-%m-%d')
#         total_amount = 0.00


#         for emp in self.employee_ids:
#             if emp.is_susupend:
#                 self.write({'employee_ids': [(3, emp.id)]})

#         res = super(HrPayslipEmployee,self).compute_sheet()
#         return res