from odoo import fields, api, models, _


class hr_employee(models.Model):
	_inherit = 'hr.employee'

	project_analytic_account_id = fields.Many2one(comodel_name='account.analytic.account', string='Project Analytic Account')
