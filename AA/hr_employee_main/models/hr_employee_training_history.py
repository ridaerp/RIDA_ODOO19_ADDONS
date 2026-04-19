from odoo import fields, api, models, _
import datetime
from dateutil.relativedelta import relativedelta

class hr_training(models.Model):
    _name = 'hr.training'

    name = fields.Char("Training Program", required=True)
    provider = fields.Char("Provider", required=True)
    date_from = fields.Date(string='From')
    date_to = fields.Date(string='To')
    Certification = fields.Boolean(string='Certification')
    attachment = fields.Binary(string='Attachment')
    employee_id = fields.Many2one('hr.employee', 'Employee')