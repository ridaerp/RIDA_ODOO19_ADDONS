

from odoo import models, fields, api



class User(models.Model):
    _inherit = "res.users"



    user_type = fields.Selection(string='User type', selection=[('hq', 'Corporate Service'),
     ('site', 'Operation'),('fleet','Fleet'),('rohax','Rohax')],required=False,default="hq")


class Employee(models.Model):
    _inherit = 'hr.employee'

    line_manager_id = fields.Many2one(comodel_name='res.users', string='Line Manager')
    line_line_manager_id = fields.Many2one(comodel_name='res.users', string='Line Line Manager')
    rida_employee_type = fields.Selection(string='Employee type',
                                              selection=[('hq', 'HQ Staff'), ('site', 'Site Staff')], required=True)



class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    line_manager_id = fields.Many2one(
        related='employee_id.line_manager_id',
    )

    line_line_manager_id = fields.Many2one(
        related='employee_id.line_line_manager_id',
    )

    rida_employee_type = fields.Selection(
        related='employee_id.rida_employee_type',
    )


    dep = fields.Selection(selection=[
            ('division', 'Division'),
            ('department', 'Department'),
            ('section', 'Section'),
            ('unit', 'Unit'),
        ])

    contract_start_date = fields.Date(string='Contract Start Date')
    contract_end_date = fields.Date(string='Contract end Date')



    




