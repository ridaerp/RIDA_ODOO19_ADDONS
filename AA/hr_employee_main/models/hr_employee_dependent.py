from odoo import fields , api , models , _
import datetime
from dateutil.relativedelta import relativedelta



class HrEmployeeRelative(models.Model):
    _name = 'hr.employee.relative'
    _description = 'HR Employee Relative'

    employee_id = fields.Many2one(string='Employee',comodel_name='hr.employee',)
    relation_id = fields.Many2one('hr.employee.relative.relation',string='Relation',required=True,)
    name = fields.Char(string='Name',required=True,)
    gender = fields.Selection(string='Gender',selection=[('male', 'Male'),('female', 'Female'),('other', 'Other'),],)
    date_of_birth = fields.Date(string='Date of Birth',)
    age = fields.Float(compute='_compute_age',)
    job = fields.Char()
    phone_number = fields.Char()
    notes = fields.Text(string='Notes')

    @api.depends('date_of_birth')
    def _compute_age(self):
        for record in self:
            age = relativedelta(datetime.datetime.now(), record.date_of_birth)
            record.age = age.years + (age.months / 12)

class HrEmployeeRelativeRelation(models.Model):
    _name = 'hr.employee.relative.relation'
    _description = 'HR Employee Relative Relation'

    name = fields.Char(string='Relation',required=True,translate=True)