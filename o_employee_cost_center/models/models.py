from odoo import fields , api , models, _
from odoo.exceptions import UserError
from dateutil import relativedelta
import datetime


class Department(models.Model):
    _inherit= "hr.department"

    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')

class HrEmployee(models.Model):
    _inherit = "hr.employee"


    @api.depends('department_id','department_id.analytic_account_id')
    def compute_analytic_account(self):
        for rec in self:
            if rec.department_id and rec.department_id.analytic_account_id:
                rec.analytic_account_id = rec.department_id.analytic_account_id.id
            else:
                return

    analytic_account_id = fields.Many2one('account.analytic.account','Cost Center',compute="compute_analytic_account",store=True,groups="hr.group_hr_user")

# class HrContract(models.Model):
#     _inherit = "hr.contract"
#
#     @api.depends('department_id','department_id.analytic_account_id')
#     def compute_analytic_account(self):
#         for rec in self:
#             if rec.department_id and rec.department_id.analytic_account_id:
#                 rec.analytic_account_id = rec.department_id.analytic_account_id.id
#             else:
#                 return
#
#     analytic_account_id = fields.Many2one('account.analytic.account','Cost Center',compute="compute_analytic_account",store=True,groups="hr.group_hr_user")