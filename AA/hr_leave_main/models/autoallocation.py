from odoo import fields , api , models , _
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta

class hrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.model
    def _cron_check_remaining_leaves(self):
       date = datetime.datetime.today()
       curr_year = str(date.year)
       if date.day == 1 and date.month == 1:
           for employee in self.env['hr.employee'].search([]):
               if employee :
                    legal_leave_annual = self.env['hr.leave.type'].sudo().search([('year','=',curr_year),('leave_type', '=', 'annual'),('company_id', '=',employee.company_id.id or False)], limit=1)
                    date_start_contract = employee.date_start
                    date_info = relativedelta(date,date_start_contract)
                    months = date_info.months + date_info.years*12
                    if legal_leave_annual:
                        leave_allocation = self.env['hr.leave.allocation'].create({
                            'name': 'Auto leave Allocation',
                            'employee_id': employee.id,
                            'holiday_status_id': legal_leave_annual.id,
                            'state': 'validate',
                            'number_of_days': 30})
                  
       else:
        today = datetime.date.today()
        fdy = today.replace(day=1, month=1)
        for employee in self.env['hr.employee'].search([]):
            if employee and employee.date_start > fdy :
                legal_leave_type = self.env['hr.leave.type'].sudo().search([('year','=',curr_year),('leave_type', '=', 'annual'),('company_id', '=',employee.company_id.id or False)], limit=1)
                if legal_leave_type:
                     leave_allocation = self.env['hr.leave.allocation'].search([('state', '=', 'validate'),('holiday_status_id', '=', legal_leave_type.id),('holiday_type', '=', 'employee'),('employee_id', '=', employee.id)], limit=1)
                if not leave_allocation:
                        leave_allocation = self.env['hr.leave.allocation'].create({
                            'name': 'Auto leave Allocation New Contract',
                            'employee_id': employee.id,
                            'holiday_status_id': legal_leave_type.id,
                            'state': 'validate',
                            'number_of_days': 30-employee.date_start.month*2.5})