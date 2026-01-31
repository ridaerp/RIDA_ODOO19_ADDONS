from odoo import models, fields, api, _
from odoo.exceptions import   UserError
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import operator


class hr_loan(models.Model):
    _name = 'hr.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = "HR Loan Request"

    _rec_name = 'name'

    def unlink(self):
        for rec in self:
            if rec.state != "draft":

                raise UserError("Sorry, only DRAFT Loans can be deleted.")
            else:
                res = super(hr_loan, rec).unlink()
                return res

    def _compute_amount(self):
        for loan in self:
            total_paid_amount = 0.00
            for line in loan.loan_line_ids:
                if line.paid == True:
                    total_paid_amount += line.paid_amount

            balance_amount = loan.loan_amount - total_paid_amount
            loan.total_amount = loan.loan_amount
            loan.balance_amount = balance_amount
            loan.total_paid_amount = total_paid_amount

    def _get_old_loan(self):
        old_amount = 0.00
        for loan in self.search(
                [('employee_id', '=', self.employee_id.id), ('state', '!=', 'refuse'), ('state', '!=', 'draft')]):
            if loan.id != self.id:
                old_amount += loan.balance_amount
        self.loan_old_amount = old_amount

    @api.depends('total_amount', 'total_paid_amount', 'loan_line_ids.paid')
    def comp_progress(self):
        for rec in self:
            if rec.total_amount and rec.total_paid_amount != 0.0:
                rec.progress = (rec.total_paid_amount / rec.total_amount) * 100
            else:
                rec.progress = 0.0

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)

    active = fields.Boolean("active", default=True)
    name = fields.Char(string="Loan Name", readonly=True, default=lambda self: 'Loan/')
    date = fields.Date(string="Date Request", default=fields.Date.today(), readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, default=_default_employee)
    image = fields.Binary(related="employee_id.image_1920")
    parent_id = fields.Many2one('hr.employee', related="employee_id.parent_id", string="Manager")
    department_id = fields.Char(related="employee_id.department_id.name", readonly=True, string="Department",
                                store=True)
    job_id = fields.Many2one('hr.job', related="employee_id.job_id", readonly=True, string="Job Position")
    emp_salary = fields.Float(string="Employee Gross")
    loan_old_amount = fields.Float(string="Old Loan Amount Not Paid", compute='_get_old_loan')
    loan_amount = fields.Float(string="Loan Amount", required=True)
    total_amount = fields.Float(string="Total Amount", readonly=True, compute='_compute_amount')
    balance_amount = fields.Float(string="Remaining Amount", compute='_compute_amount')
    total_paid_amount = fields.Float(string="Total Paid Amount", compute='_compute_amount')
    progress = fields.Float(string="Progress %", compute=comp_progress, readonly=True, store=True)
    color = fields.Integer(string='Color Index')
    no_month = fields.Integer(string="No Of Month")
    # no_month = fields.Integer(string="No Of Month", default=1)
    payment_start_date = fields.Date(string="Start Date of Payment", required=True, default=fields.Date.today())
    loan_line_ids = fields.One2many('hr.loan.line', 'loan_id', string="Loan Line", index=True)
    loan_config_id = fields.Many2one(comodel_name='hr.loan.config', string='Loan Type', required=True, )
    emp_code = fields.Char(related="employee_id.emp_code", readonly=True, string="Employee Code", store=True)
    start_date = fields.Date(string='Contract Start Date', related="employee_id.version_id.date_start")
    expiry_date = fields.Date(string='Contract Expiry Date', related="employee_id.version_id.date_end")
    company_id = fields.Many2one('res.company', string='Company')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('hr_officer', 'HR Officer Approval'),
        ('hr_approve', 'HR Manager Approval'),
        ('site_manager', 'Operation Director Approval'),
        ('finance', 'Finance Approval'),
        ('internal_audit', 'Internal Audit Approval'),
        ('ccso', 'COO Approval'),
        ('c_level', 'C level Approval'),
        ('accountant', 'Accountant Approval'),
        ('approve', 'Approved'),
        ('paid', 'Paid'),
        ('refuse', 'Refused'),
    ], string="State", default='draft', track_visibility='onchange', copy=False)
    currency_id = fields.Many2one('res.currency', string='Currency',)


    @api.onchange('loan_amount')
    def _onchange_loan_amount(self):
        self.onchange_loan_config_id()

    @api.onchange('loan_config_id')
    def _onchange_loan_config(self):
        self.onchange_loan_config_id()

    @api.constrains('no_month')
    def _check_no_month(self):
        if self.no_month == 0:
            self.no_month = 1

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            if rec.sudo().employee_id:
                rec.emp_salary = rec.sudo().employee_id.payroll_wage
                rec.company_id = rec.sudo().employee_id.sudo().company_id
                rec.currency_id = rec.sudo().employee_id.sudo().currency_id
            else:
                raise UserError(f'The {rec.sudo().employee_id.name} Dosn\'t Have Contract')

    @api.model
    def create(self, values):
        for val in values:
            val['name'] = self.env['ir.sequence'].next_by_code('hr.loan.req.seq')
            res = super(hr_loan, self).create(val)
            return res

    def action_submit(self):
        for rec in self:
            rec.state = 'hr_officer'
            if rec.loan_old_amount > 0:
                message_id = self.env['mymodule.message.wizard'].create({'message': 'Your ave Old Loans To Pay.'})
                return {
                    'name': 'Message',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'mymodule.message.wizard',
                    'res_id': message_id.id,
                    'target': 'new'
                }

    def action_refuse(self):
        for rec in self:
            rec.state = 'refuse'

    def action_set_to_draft(self):
        self.state = 'draft'

    def onchange_employee_id(self, employee_id=False):
        old_amount = 0.00
        if employee_id:
            for loan in self.search(
                    [('employee_id', '=', employee_id), ('state', '!=', 'refuse'), ('state', '!=', 'draft')]):
                if loan.id != self.id:
                    old_amount += loan.balance_amount
            return {
                'value': {
                    'loan_old_amount': old_amount}
            }

    def action_approve(self):
        for rec in self:
            rec.state = 'hr_approve'
        return True

    def compute_loan_line(self):
        # self.onchange_loan_config_id()
        loan_line = self.env['hr.loan.line']
        loan_line.search([('loan_id', '=', self.id)])
        lines = [(5, 0, 0)]
        for loan in self:
            date_start = loan.payment_start_date
            counter = 1
            amount_per_time = loan.loan_amount / loan.no_month
            for i in range(1, loan.no_month + 1):
                line_id = {
                    'paid_date': date_start,
                    'paid_amount': amount_per_time,
                    'employee_id': loan.employee_id.id,
                    'loan_id': loan.id}
                lines.append((0, 0, line_id))
                loan.loan_line_ids = lines
                counter += 1
                date_start = date_start + relativedelta(months=1)
        return True

    def button_reset_balance_total(self):
        total_paid_amount = 0.00
        for loan in self:
            for line in loan.loan_line_ids:
                if line.paid == True:
                    total_paid_amount += line.paid_amount
            balance_amount = loan.loan_amount - total_paid_amount
            self.write({'total_paid_amount': total_paid_amount,
                        'balance_amount': balance_amount})

    # comparing function in loan restriction task for rida
    def get_truth(self, inp, relate, cut):
        ops = {'>': operator.gt,
               '<': operator.lt,
               '>=': operator.ge,
               '<=': operator.le,
               '==': operator.eq}
        return ops[relate](inp, cut)

    # loan new constrain in loan restriction task for rida
    @api.constrains('loan_config_id')
    def onchange_loan_config_id(self):
        if self.loan_config_id:
            if (not self.loan_config_id.employee_request) and (not self.env.user.has_group('hr.group_hr_user')):
                raise UserError(_("This Loan Type Should Be Created By HR Only"))
        for rec in self:
            if rec.loan_config_id.condition == 'formula':
                flag = 0
                emp_join_date = self.sudo().employee_id.contract_id.date_start
                # loan_config_line = self.env['hr.loan.config.line']
                # if rec.loan_config_id.sign == False :
                # 	raise UserError(_("This Loan Type Should Has Signe"))
                for route in self.loan_config_id.line_id:
                    if route.join_date_comparison == 'date':
                        if rec.get_truth(emp_join_date, route.sign, route.date):
                            flag += 1
                            line_num = len(self.loan_config_id.line_id)
                            if flag == line_num:
                                pass
                        else:
                            raise UserError(
                                _("The Joining Date Dose Not Meet the Loan Type Condition Date"))
                    elif route.join_date_comparison == 'number':
                        date_today = datetime.now().date()
                        date_join = emp_join_date
                        diff = relativedelta(date_today, date_join)
                        # Year
                        if route.interval_base == 'year':
                            if diff.years:
                                years = diff.years
                            else:
                                years = 0
                            if rec.get_truth(route.number, route.sign, years):
                                flag += 1
                                line_num = len(self.loan_config_id.line_id)
                                if flag == line_num:
                                    pass
                            else:
                                raise UserError(
                                    _("Working Years Dose Not Meet the Loan Type Condition Number of Years"))
                        else:
                            if diff.months:
                                if diff.years:
                                    months = diff.months + (12 * diff.years)
                                else:
                                    months = diff.months
                            else:
                                if diff.years:
                                    months = 12 * diff.years
                                else:
                                    months = 0
                            if rec.get_truth(months, route.sign, route.number):
                                flag += 1
                                line_num = len(self.loan_config_id.line_id)
                                if flag == line_num:
                                    pass
                            else:
                                raise UserError(
                                    ("Working Months Dose Not Meet the Loan Type Condition Number of Months"))
                if flag == 0:
                    raise UserError(
                        ("Dose Not Match any Condition"))
            if rec.loan_config_id.max_base == 'fixed':
                if rec.loan_amount:
                    if rec.loan_config_id.amount == 0 or rec.loan_amount <= rec.loan_config_id.amount:
                        pass
                    else:
                        raise UserError('Loan Amount Exceeded the Maximum Amount')
            elif rec.loan_config_id.max_base == 'gross_month':
                x = rec.loan_config_id.maximum_month_gross * rec.sudo().employee_id.contract_id.payroll_wage
                if rec.loan_amount > x:
                    raise UserError('Loan Amount Exceeded the Maximum Amount')
            else:
                pass
            rec.no_month = rec.loan_config_id.installment if rec.loan_config_id.set_no_of_installmens else 1
            rec.compute_loan_line()


class hr_loan_line(models.Model):
    _name = "hr.loan.line"
    _description = "HR Loan Request Line"

    paid_date = fields.Date(string="Payment Date", required=True)
    journal_id = fields.Many2one('account.move', string='Journal Entry', readonly=1, copy=False)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    paid_amount = fields.Float(string="Paid Amount", required=True)
    paid = fields.Boolean(string="Paid")
    notes = fields.Text(string="Notes")
    loan_id = fields.Many2one(
        'hr.loan', string="Loan Ref.", ondelete='cascade')
    payroll_id = fields.Many2one('hr.payslip', string="Payslip Ref.")
    active = fields.Boolean(related="loan_id.active")
    state = fields.Selection(related="loan_id.state", store=True)

    def action_unpaid(self):
        if self.loan_id.active == False:
            raise UserError(
                _('Warning', "Loan Request must be approved and active"))
            return False
        else:
            self.paid = False
            return True

    def action_paid_amount(self):
        if self.loan_id.active == False:
            self.action_unpaid()
            return False
        context = self._context
        can_close = False
        loan_obj = self.env['hr.loan']
        created_move_ids = []
        loan_ids = []
        for line in self:
            if line.loan_id.state != 'paid':
                raise UserError("Loan Request must be approved")
            paid_date = line.paid_date
            amount = line.paid_amount
            loan_name = line.employee_id.name
            reference = line.loan_id.name
        return True


class hr_employee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def _compute_loans(self):
        for rec in self:
            count = 0
            loan_remain_amount = 0.00
            loan_ids = self.env['hr.loan'].search(
                [('employee_id', '=', rec.id)])
            for loan in loan_ids:
                loan_remain_amount += loan.balance_amount
                count += 1
            rec.loan_count = count
            rec.loan_amount = loan_remain_amount

    loan_amount = fields.Float(string="loan Amount", compute='_compute_loans')
    loan_count = fields.Integer(string="Loan Count", compute='_compute_loans')


class MyModuleMessageWizard(models.TransientModel):
    _name = 'mymodule.message.wizard'
    _description = "Show Message"

    message = fields.Text('Message', required=True)

    def action_close(self):
        loans = self.env['hr.loan'].browse(self.env.context.get('active_id'))
        for lo in loans:
            lo.state = 'hr_officer'
