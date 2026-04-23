from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrPayrollLoan(models.Model):
    _name = 'hr.payroll.loan'
    _description = 'Payroll Loan'

    loan_type_id = fields.Many2one("hr.loan.config", "Loan Type", readonly=True)
    amount = fields.Float("Amount", readonly=True)
    slip_id = fields.Many2one("hr.payslip", "Payroll", readonly=True)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    loan_line_ids = fields.One2many('hr.payroll.loan', 'slip_id', string="Loans")
    loan = fields.Boolean("Automated Loan", default=True)
    loan_ids = fields.One2many('hr.loan.line', 'payroll_id', string="Loans")
    total_amount_paid = fields.Float(
        string="Total Loan Amount",
        compute='_compute_total_paid_loan'
    )


    def get_loan(self):
        for rec in self:
            loan_ids = self.env['hr.loan.line'].search([
                ('loan_id.employee_id', '=', rec.employee_id.id),
                ('paid', '=', False),
                ('active', '=', True),
                ('loan_id.state', '=', 'paid'),   # change to 'paid' only if your hr.loan.line state is really paid
                ('paid_date', '>=', rec.date_from),
                ('paid_date', '<=', rec.date_to),
            ])
         
            rec.loan_ids = [(6, 0, loan_ids.ids)]
        return True



    def compute_sheet(self):
        result = True
        for rec in self:
            rec.get_loan()
            rec.get_loans_by_type()
            result = super(HrPayslip, rec).compute_sheet()
        return result


    @api.depends('loan_ids', 'loan_ids.paid_amount')
    def _compute_total_paid_loan(self):
        for rec in self:
            rec.total_amount_paid = sum(rec.loan_ids.mapped('paid_amount'))

    def get_loans_by_type(self):
        for rec in self:
            rec.loan_line_ids.unlink()

            loan_types = self.env['hr.loan.config'].search([])
            for loan_type in loan_types:
                amount = sum(
                    line.paid_amount
                    for line in rec.loan_ids
                    if line.loan_id.loan_config_id.id == loan_type.id
                )

                if amount:
                    self.env['hr.payroll.loan'].create({
                        'loan_type_id': loan_type.id,
                        'slip_id': rec.id,
                        'amount': amount,
                    })

    def action_payslip_done(self):
        result = True
        for rec in self:
            rec.compute_sheet()
            result = super(HrPayslip, rec).action_payslip_done()

            for line in rec.loan_ids:
                line.paid = True
                if line.journal_id and line.journal_id.state != 'posted':
                    line.journal_id.action_post()
                line.action_paid_amount()

            rec.state = 'validated'

        return result

    def action_payslip_cancel(self):
        for rec in self:
            for line in rec.loan_ids:
                if line.paid:
                    line.write({'paid': False})
            rec.state = 'cancel'