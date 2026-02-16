from odoo import models, fields, api, tools, _
from odoo.exceptions import   UserError
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta


class hr_payslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        for rec in self:
            rec.get_loan()
            for line in rec.loan_ids:
                if rec.loan:
                    line.paid = True
                    if line.sudo().journal_id.state !='posted':
                        line.sudo().journal_id.sudo().action_post()
            rec.get_loans_by_type()
            return super(hr_payslip, rec).compute_sheet()
            






    loan_line_ids = fields.One2many('hr.payroll.loan', 'slip_id', string="Loans",store=True)
    loan = fields.Boolean("Automated Loan", default=True)

    @api.depends('employee_id')
    def get_loans_by_type(self):
        self.loan_line_ids.unlink()
        for rec in self:
            loan_types = self.env['hr.loan.config'].search([])
            for type in loan_types:
                vals = {'loan_type_id': type.id, 'slip_id': rec.id}
                amount = 0.0
                for line in rec.loan_ids:
                    if line.loan_id.loan_config_id.id == type.id:
                        amount += line.paid_amount
                vals['amount'] = amount
                self.env['hr.payroll.loan'].create(vals)

    def compute_total_paid_loan(self):
        for rec in self:
            total = 0.00
            for line in rec.loan_ids:
                if line.paid == True:
                    total += line.paid_amount
            rec.total_amount_paid = total

    loan_ids = fields.One2many('hr.loan.line', 'payroll_id', string="Loans",store=True,)
    total_amount_paid = fields.Float(string="Total Loan Amount", compute='compute_total_paid_loan')

    def get_loan(self):
        for rec in self:
            array = []
            loan_ids = self.env['hr.loan.line'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('paid', '=', False), ('active', '=', True),
                ('state', '=', 'approve'),
                ('paid_date', '>=', rec.date_from),
                ('paid_date', '<=', rec.date_to),
            ])
            for loan in loan_ids:
                array.append(loan.id)
            rec.loan_ids = array
            return array

    def action_payslip_done(self):
        for rec in self:
            res = super(hr_payslip, self).action_payslip_done()
            rec.compute_sheet()
            array = []
            for line in rec.loan_ids:
                if line.paid:
                    array.append(line.id)
                    line.action_paid_amount()
                else:
                    line.payroll_id = False

            rec.loan_ids = array
            rec.state = 'done'
            return res

    def action_payslip_cancel(self):
        for rec in self:
            if rec.filtered(lambda slip: slip.state == 'done'):
                raise UserError(_("Cannot cancel a payslip that is done."))
            for line in rec.loan_ids:
                if line.paid:
                    line.write({'paid': False})
            rec.state = 'cancel'

    def refund_sheet(self):
        for rec in self:
            for line in rec.loan_ids:
                if line.paid:
                    line.write({'paid': False})

            copied_payslip = rec.copy({'credit_note': True, 'name': _('Refund: ') + rec.name})
            copied_payslip.action_payslip_done()
            formview_ref = self.env.ref('hr_payroll.view_hr_payslip_form', False)
            treeview_ref = self.env.ref('hr_payroll.view_hr_payslip_tree', False)
            return {
                'name': ("Refund Payslip"),
                'view_mode': 'list, form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'hr.payslip',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
                'views': [(treeview_ref and treeview_ref.id or False, 'list'),
                          (formview_ref and formview_ref.id or False, 'form')],
                'context': {}
            }


class hrPayslipLine(models.Model):
    _name = 'hr.payroll.loan'
    _description = 'Payroll Loan'

    loan_type_id = fields.Many2one("hr.loan.config", "Loan Type", readonly=True)
    amount = fields.Float("Amount", readonly=True)
    slip_id = fields.Many2one("hr.payslip", "Payroll", readonly=True)
