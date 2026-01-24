from odoo import fields, api, models, _


class hr_employee(models.Model):
	_inherit = 'hr.employee'

	project_analytic_account_id = fields.Many2one(comodel_name='account.analytic.account', string='Project Analytic Account')
	contract_start_date = fields.Date(string='Contract Start Date', related='contract_id.date_start',readonly=True,store=True)
	contract_end_date = fields.Date(string='Contract end Date', related='contract_id.date_end',readonly=True,store=True)
	# analytic_account_id = fields.Many2one(comodel_name='account.analytic.account', string='Analytic Account', related='employee_id.analytic_account_id',readonly=True,store=True)
