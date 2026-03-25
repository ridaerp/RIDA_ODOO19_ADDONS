# -*- coding: utf-8 -*-
from odoo import models, fields, api,_
# from odoo.exceptions import except_orm, Warning, RedirectWarning, UserError
from odoo.exceptions import UserError, AccessError, ValidationError
from calendar import monthrange
import time
#Import logger
import logging
import json
#Get the logger
_logger = logging.getLogger(__name__)

class hr_overtime_report_wizard(models.TransientModel):
    _name='hr.overtime.report.wizard'

    department_id = fields.Many2one('hr.department', "Department")
    employee_id = fields.Many2one('hr.employee', "Employee")
    date_from =fields.Date("From")
    date_to =fields.Date("To")

    
    def print_report(self):
        self.ensure_one()
        [data] = self.read()
        datas = {
            'ids': [],
            'model': 'hr.over.time',
            'form': data,
        }
        return self.env.ref('hr_overtime.hr_overtime_report_id').report_action(self,data=datas)



class OTReport(models.AbstractModel):
    _name = 'report.hr_overtime.over_time_report_op_temp'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']
        department_id = data['form']['department_id']
        employee_id = data['form']['employee_id']
        domain = [('date', '>=', str(date_from)),('date','<=',str(date_to))]
        if department_id:
            domain.append(('department_id','=',department_id[0]))
        if employee_id:
            domain.append(('employee_id','=',employee_id[0]))
        docs = self.env['hr.over.time'].search(domain)
        # _logger.critical("docs" + json.dumps(docs, indent=4, sort_keys=True, default=str))
        total_normal = 0 
        total_night = 0 
        total_holiday = 0 
        total_weekend = 0 
        for rec in docs:
            total_normal += rec.hours_normal
            total_night += rec.hours_night 
            total_holiday += rec.hours_holiday
            total_weekend += rec.hours_weekend
        # raise UserError(json.dumps(total_night, indent=4, sort_keys=True, default=str))
        if not docs:
            raise UserError('No Overtime Records match your selection!')
        # raise UserError(department_id)
        return {
           'data': data,
           'docs': docs,
           # 'employee_id': employee_id,
           'total_normal':total_normal,
           'total_night':total_night,
           'total_holiday':total_holiday,
           'total_weekend':total_weekend,
           'date_from':date_from,
           'date_to':date_to,
           
        }