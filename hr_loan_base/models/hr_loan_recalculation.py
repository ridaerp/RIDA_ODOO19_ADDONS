from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta


class loan_recalculation(models.Model):
    _name = 'loan.recalculation'
    _rec_name = 'loan_id'

    loan_id = fields.Many2one("hr.loan", "Loan", readonly=True)
    employee_id = fields.Many2one("hr.employee", "Employee", compute="get_loan_details", store=True)
    loan_amount = fields.Float(string="Loan Amount", compute="get_loan_details", store=True)
    no_month = fields.Integer(string="No Of Month", default=1)
    payment_start_date = fields.Date(string="Start Date of Payment", required=True, default=fields.Date.today())
    loan_line_ids = fields.One2many('hr.loan.line', 'loan_r_id', string="Loan Line", readonly=True)
    note = fields.Text("Note")
    state = fields.Selection([('draft', 'draft'), ('confirm', 'Confirm')], string="State", default="draft")

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Sorry, Only DRAFT Recalculation Can Be Deleted."))
            else:
                res = super(loan_recalculation, rec).unlink()

    @api.depends('loan_id')
    def get_loan_details(self):
        if self.loan_id:
            self.employee_id = self.loan_id.employee_id.id
            date = False
            amount = 0.0
            for line in self.loan_id.loan_line_ids:
                if not line.paid:
                    amount += line.paid_amount
                if line.paid:
                    date = line.paid_date
            self.loan_amount = amount
            if date:
                self.payment_start_date = date + relativedelta(months=1)
            else:
                self.payment_start_date = fields.Date.today()

    def compute_loan_line(self):
        loan_line = self.env['hr.loan.line']
        loan_line.search([('loan_id', '=', self.loan_id.id), ('paid', '=', False)]).unlink()
        self.loan_id.activity_unlink(['hr_loan_base.mail_loan_recalculation'])
        for loan in self:
            date_start_str = loan.payment_start_date
            counter = 1
            amount_per_time = loan.loan_amount / loan.no_month
            for i in range(1, loan.no_month + 1):
                line_id = loan_line.create({
                    'loan_id': loan.loan_id.id,
                    'paid_date': date_start_str,
                    'paid_amount': amount_per_time,
                    'employee_id': loan.employee_id.id,
                    'loan_r_id': loan.id
                })
                counter += 1
                date_start_str = date_start_str + relativedelta(months=1)
            loan.state = 'confirm'
        self.loan_id.activity_schedule('hr_loan_base.mail_loan_recalculation', user_id=self.loan_id.create_uid.id)
        if self.no_month:
            self.loan_id.no_month = self.no_month
        return True


class hr_loan(models.Model):
    _name = "hr.loan"
    _inherit = "hr.loan"

    def open_loan_recalculation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'loan.recalculation',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }


class hr_loan_line(models.Model):
    _name = "hr.loan.line"
    _inherit = "hr.loan.line"

    loan_r_id = fields.Many2one('loan.recalculation', string="Loan Recalculate Ref.", ondelete='cascade')
