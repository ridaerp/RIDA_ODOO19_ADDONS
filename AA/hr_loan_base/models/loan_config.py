from odoo import models, fields, api , _

class hr_loan_config(models.Model):
	_name = 'hr.loan.config'

	line_id = fields.One2many(comodel_name='hr.loan.config.line', inverse_name='line_id', string='')
	name = fields.Char("Loan Name")
	payroll_code = fields.Char("Payroll Code")
	description = fields.Text("Description")
	condition = fields.Selection([('always','Always'),('formula','Formula')], string="Condition", required=True)
	date = fields.Date("Date")
	amount = fields.Float("Amount")
	number = fields.Integer("Number")
	join_date_comparison = fields.Selection([('number', 'Number Of Month'),('date', 'Date')])
	interval_base = fields.Selection([('year', 'Year'), ('month', 'Month')])
	sign = fields.Selection([('greater','>'),('less','<'),('equal','='),('greater_equal','>='),('less_equal','=<')])
	employee_request = fields.Boolean("Request By Employee", default=True)
	maximum_month_gross = fields.Integer("Maximum Amount (Gross Month)")
	installment = fields.Integer("number of Installment")
	set_no_of_installmens = fields.Boolean(string='Set number of deduction')
	max_base = fields.Selection([('fixed','Fixed Amount'),('gross_month','Gross month')], string="Maximum Amount Based")
