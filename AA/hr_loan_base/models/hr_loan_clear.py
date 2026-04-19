from odoo import models, fields, api , _
from odoo.exceptions import   UserError
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

class loan_clear(models.Model):
	_name = 'loan.clear'
	_rec_name = 'loan_id'


	loan_id = fields.Many2one("hr.loan","Loan", readonly=True)
	employee_id = fields.Many2one("hr.employee", "Employee", compute="get_loan_details", store=True)
	loan_amount = fields.Float(string="Loan Amount", compute="get_loan_details", store=True)
	loan_line_ids = fields.One2many('hr.loan.line', 'loan_c_id', string="Loan Line", readonly=True)
	note = fields.Text("Note")
	company_id = fields.Many2one("res.company", string="Branch", related="employee_id.company_id", store=True, readonly=True)
	state = fields.Selection([('draft', 'draft'), ('confirm', 'Confirm')], string ="State", default ="draft")

	def unlink(self):
		for rec in self:
			if rec.state != "draft":
				raise UserError(_("Sorry, Only DRAFT Clear Can Be Deleted."))
			else:
				res = super(loan_clear, rec).unlink()

	@api.depends('loan_id')
	def get_loan_details(self):
		if self.loan_id:
			self.employee_id = self.loan_id.employee_id.id
			amount = 0.0
			for line in self.loan_id.loan_line_ids:
				if not line.paid:
					amount += line.paid_amount
			self.loan_amount = amount


	def compute_loan_line(self):
		loan_line = self.env['hr.loan.line']
		self.loan_id.activity_unlink(['hr_loan_base.mail_loan_clear'])
		for loan in loan_line.search([('loan_id', '=', self.loan_id.id),('paid','=',False)]):
			loan.paid = True
			loan.loan_c_id = self.id

		self.loan_id.progress = 100
		self.state = 'confirm'
		self.loan_id.activity_schedule('hr_loan_base.mail_loan_clear', user_id=self.loan_id.create_uid.id)
		return True


class hr_loan_line(models.Model):
	_name="hr.loan.line"
	_inherit = "hr.loan.line"

	loan_c_id = fields.Many2one('loan.clear', string="Loan Clear Ref.", ondelete='cascade')