from odoo import fields, api, models, _
import datetime
from dateutil.relativedelta import relativedelta


class hr_custody(models.Model):
    _name = 'hr.custody'

    name = fields.Char("Name", required=True)
    state = fields.Selection([('cleared', 'Cleared'), ('not_cleared', 'Not Cleared')], default='not_cleared',string="status")
    date = fields.Datetime('Time', default=datetime.datetime.now())
    clear_date = fields.Datetime('Clear Time')
    employee_id = fields.Many2one('hr.employee', 'Employee')