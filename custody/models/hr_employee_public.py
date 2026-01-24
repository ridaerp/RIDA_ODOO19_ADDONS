from odoo import api, fields, models, tools


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    id_expiry_date = fields.Date(readonly=True)
    passport_expiry_date = fields.Date(readonly=True)
    age = fields.Integer(readonly=True)
    # grade_id = fields.Many2one("grade.grade", "Grade")
    # rank_id = fields.Many2one("rank.rank", "Rank")
    address_home_id = fields.Many2one(
        'res.partner', 'Address', help='Enter here the private address of the employee, not the one linked to your company.',
        groups="base.group_user", tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    # custody_id = fields.One2many('hr.custody', 'employee_id', groups="hr.group_hr_user")
    # relative_ids = fields.One2many(string='Relatives',comodel_name='hr.employee.relative',inverse_name='employee_id', groups="hr.group_hr_user")
    # training_ids = fields.One2many('hr.training', 'employee_id', groups="hr.group_hr_user")

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    id_expiry_date = fields.Date(string='ID Expiry Date', help='Expiry date of Identification ID')
    passport_expiry_date = fields.Date(string='Passport Expiry Date', help='Expiry date of Passport ID')
    age = fields.Integer(string="Age", readonly=True, compute="_compute_age")
    custody_id = fields.One2many('hr.custody', 'employee_id', groups="hr.group_hr_user")
    relative_ids = fields.One2many(string='Relatives',comodel_name='hr.employee.relative',inverse_name='employee_id', groups="hr.group_hr_user")
    training_ids = fields.One2many('hr.training', 'employee_id', groups="hr.group_hr_user")