# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import base64

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round, date_utils
from odoo.tools.misc import format_date
from odoo.tools import float_compare, float_is_zero
from odoo.tools.safe_eval import safe_eval

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    _description = 'Added workflows to payroll stages'

    salary_currency = fields.Many2one(related='version_id.salary_currency')
    analytic_account_id = fields.Many2one("account.analytic.account",string='Analytic Account')
    take_home = fields.Float(string="Take Home",readonly=False)
    payslip_day = fields.Float(string="WorkedDays",readonly=True,store=True,compute="caculate_workdays_take_home")
    take_home_wage = fields.Monetary(compute='_compute_basic_net',)

    employee_code=fields.Char(related="employee_id.emp_code")
    bank_acc_id=fields.Many2one(related="employee_id.bank_account_id",string="Bank Account Number",store=True)
    bank_id=fields.Many2one(related="bank_acc_id.bank_id",string="Bank Account Number",store=True)


    @api.model_create_multi
    def create(self, vals_list):
        payslips = super().create(vals_list)

        for payslip in payslips:
            if not payslip.struct_id:
                continue

            existing_input_type_ids = payslip.input_line_ids.mapped('input_type_id').ids
            allowed_input_types = payslip.struct_id.input_line_type_ids.sorted(
                key=lambda x: x.sequence, reverse=True
            )

            for input_type in allowed_input_types:
                if input_type.id in existing_input_type_ids:
                    continue

                values = {
                    'payslip_id': payslip.id,
                    'input_type_id': input_type.id,
                    'amount': 0.0,
                }

                if 'version_id' in self.env['hr.payslip.input']._fields and payslip.version_id:
                    values['version_id'] = payslip.version_id.id

                self.env['hr.payslip.input'].create(values)

        return payslips


    # @api.depends('employee_id', 'employee_id.analytic_account_id')
    # def _compute_analytic_account_id(self):
    #     for rec in self:
    #         rec.analytic_account_id = rec.employee_id.analytic_account_id


    # @api.depends('line_ids.total', 'line_ids.code')
    # def _compute_take_home(self):
    #     for rec in self:
    #         lines = rec.line_ids.filtered(lambda l: l.code == 'TH')
    #         rec.take_home = sum(lines.mapped('total')) if lines else 0.0


    # @api.depends('employee_id', 'employee_id.date_start', 'date_from', 'date_to')
    # def _compute_payslip_day(self):
    #     for rec in self:
    #         employee_start = rec.employee_id.date_start
    #         date_from = rec.date_from
    #         date_to = rec.date_to

    #         if not employee_start or not date_from or not date_to:
    #             rec.payslip_day = 30
    #             continue

    #         if date_from <= employee_start <= date_to:
    #             d1 = employee_start.day
    #             d11 = date_from.day
    #             d22 = date_to.day

    #             if d11 == d1:
    #                 rec.payslip_day = 30
    #             else:
    #                 rec.payslip_day = 32 - d1 if (d22 - d11) != 29 else 31 - d1
    #         else:
    #             rec.payslip_day = 30

    # def compute_sheet(self):
    #     res = super().compute_sheet()

    #     self._compute_take_home()
    #     self._compute_payslip_day()
    #     self._compute_analytic_account_id()
    #     self.compute_mazaya()

    #     return res

    def compute_sheet(self):
        res = super(HrPayslip, self).compute_sheet()
        for slip in self:
            # slip.caculate_workdays_take_home()
            slip.compute_mazaya()
        return res


    def unlink(self):
        if any(payslip.state not in ('draft', 'verify','close','cancel') for payslip in self):
            raise UserError("you cannot delete the payslip")
        self.write({'state': 'draft'})


        for rec in self:
            loan_ids = self.env['hr.loan.line'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('paid', '=', True), 
                ('state', '=', 'approve'),
                ('paid_date', '>=', rec.date_from),
                ('paid_date', '<=', rec.date_to),
            ])
            for line in rec.loan_ids:
                line.paid = False


        return super(HrPayslip, self).unlink()


    # @api.depends('date_from','mazaya_id','payslip_day')
    def compute_mazaya(self):
        for record in self:
            mazaya_total = mazaya_tax = 0
            Y,m,d = str(record.date_from).split('-')
            months = int(m)
            maz_lin_obj = self.env['rida.mazaya.line']
            basic_sal =((record.version_id.payroll_wage/30)*record.payslip_day)* 61/100

            gross_sal = record.version_id.payroll_wage
            if record.mazaya_id:
                maz_mon = maz_lin_obj.search([('month','=',months), ('mazaya_id','=',record.mazaya_id.id)],limit=1)
                if maz_mon:
                    if record.mazaya_id.based_on == 'basic':
                        mazaya_cash = maz_mon.cash_allow * basic_sal /100 # Calcccccccccccccu
                        mazaya_dress = maz_mon.dress_allow * basic_sal /100 # Calcccccccccccccu
                        mazaya_midical = maz_mon.midical_allow * basic_sal /100 # Calcccccccccccccu
                        mazaya_grant = maz_mon.grant_allow * basic_sal /100 # Calcccccccccccccu
                        mazaya_total = maz_mon.new_allow * basic_sal /100 # Calcccccccccccccu
                        mazaya_tax = mazaya_total*maz_mon.tax_allow/100
                    elif record.mazaya_id.based_on =='gross':
                        mazaya_cash = maz_mon.cash_allow * gross_sal /100# Calcccccccccccccu
                        mazaya_dress = maz_mon.dress_allow * gross_sal /100# Calcccccccccccccu
                        mazaya_midical = maz_mon.midical_allow * gross_sal /100# Calcccccccccccccu
                        mazaya_grant = maz_mon.grant_allow * gross_sal /100# Calcccccccccccccu
                        mazaya_total = maz_mon.new_allow * gross_sal /100# Calcccccccccccccu
                        mazaya_tax = mazaya_total*maz_mon.tax_allow/100
                    record.mazaya_cash= mazaya_cash
                    record.mazaya_dress= mazaya_dress
                    record.mazaya_midical= mazaya_midical
                    record.mazaya_grant= mazaya_grant
                    record.mazaya_total= mazaya_total
                    record.mazaya_tax = mazaya_tax



    @api.depends('employee_id.date_start', 'date_from', 'date_to')
    def caculate_workdays_take_home(self):
        for rec in self:
            rec.analytic_account_id = rec.employee_id.analytic_account_id
            rec.take_home = 0.0

            lines = rec.line_ids.filtered(lambda l: l.code == 'TH')
            rec.take_home = sum(lines.mapped('total')) if lines else 0.0

            employee_start = rec.employee_id.date_start
            date_from = rec.date_from
            date_to = rec.date_to

            if not employee_start or not date_from or not date_to:
                rec.payslip_day = 30
                continue

            if date_from <= employee_start <= date_to:
                d1 = employee_start.day
                d2 = date_from.day
                if d2 == d1:
                    rec.payslip_day = 30
                else:
                    d11 = date_from.day
                    d22 = date_to.day
                    rec.payslip_day = 32 - d1 if d22 - d11 != 29 else 31 - d1
            else:
                rec.payslip_day = 30



    def _compute_basic_net(self):
        super(HrPayslip,self)._compute_basic_net()
        for payslip in self:
            payslip.basic_wage = payslip._get_salary_line_total('BASIC')
            payslip.net_wage = payslip._get_salary_line_total('NET')
            payslip.take_home_wage = payslip._get_salary_line_total('TH')







    # Submit Button function
    def submit_draft_state(self):
        # self.write({'state': 'director_approve'})
        self.write({'state': 'director_approve'})

    # HR Director Approve Button function
    def director_approve_state(self):
        self.write({'state': 'verify'})

    # CCSO Approve Button function
    def ccso_approve_state(self):
        self.write({'state': 'verify'})


    # CCSO Approve Button function
    def action_draft_state(self):
        self.write({'state': 'draft'})



    def _prepare_line_values(self, line, account, date, debit, credit):
        batch_lines = self.company_id.batch_payroll_move_lines
        partner = self.employee_id.work_contact_id if (
            not batch_lines and line.salary_rule_id.employee_move_line
        ) else line.partner_id

        company_currency = self.env.company.currency_id
        salary_currency = self.salary_currency
        move_date = date or fields.Date.today()

        def _amount_vals(local_debit, local_credit):
            if salary_currency.id != company_currency.id:
                cur_debit = 0.0
                cur_credit = 0.0
                amount_currency = 0.0

                if local_debit > 0:
                    cur_debit = salary_currency._convert(
                        local_debit, company_currency, line.company_id, move_date
                    )
                    amount_currency = local_debit

                if local_credit > 0:
                    cur_credit = salary_currency._convert(
                        local_credit, company_currency, line.company_id, move_date
                    )
                    amount_currency = -local_credit

                return {
                    'currency_id': salary_currency.id,
                    'debit': cur_debit,
                    'credit': cur_credit,
                    'amount_currency': amount_currency,
                }

            return {
                'debit': local_debit,
                'credit': local_credit,
            }

        base_vals = {
            'name': line.name if line.salary_rule_id.split_move_lines else line.salary_rule_id.name,
            'partner_id': partner.id,
            'account_id': account.id,
            'journal_id': line.slip_id.struct_id.journal_id.id,
            'date': move_date,
            'analytic_distribution': line.salary_rule_id.analytic_distribution or line.slip_id.version_id.analytic_distribution,
            'tax_tag_ids': line.debit_tag_ids.ids if account.id == line.salary_rule_id.account_debit.id else line.credit_tag_ids.ids,
            'tax_ids': [(4, tax_id) for tax_id in account.tax_ids.ids],
        }

        if (
            not batch_lines
            and line.salary_rule_id.employee_move_line
            and self.employee_id.has_multiple_bank_accounts
        ):
            line_vals = []
            debit_allocations = self.compute_salary_allocations(debit)
            credit_allocations = self.compute_salary_allocations(credit)

            for ba in self.employee_id.bank_account_ids:
                subdebit = debit_allocations.get(str(ba.id), 0.0)
                subcredit = credit_allocations.get(str(ba.id), 0.0)

                vals = dict(base_vals)
                vals.update({
                    'employee_bank_account_id': ba.id,
                })
                vals.update(_amount_vals(subdebit, subcredit))
                line_vals.append(vals)

            return line_vals

        vals = dict(base_vals)
        vals.update(_amount_vals(debit, credit))
        return [vals]

    
    # def _prepare_line_values(self, line, account_id, date, debit, credit):
    #     # res = super(HrPayslip, self)._prepare_line_values()

    #     """ Extend Odoo Default method _prepare_line_values() 
    #         - Add multi currency feature to the function by comparing currency of payroll with the default company currency
    #           if it's differet from the company currency then we will convert it to the default currency by function:
    #           payroll_currency._convert(amount,company_currency,company,date) """
              
    #     if self.salary_currency.id != self.env.company.currency_id.id:
    #         cur_credit = cur_debit = amount_currency = 0.00
    #         if debit > 0:
    #             cur_debit = self.salary_currency._convert(debit, self.env.company.currency_id, line.company_id, date or fields.Date.today())
    #             amount_currency = debit
    #         if credit > 0:
    #             cur_credit = self.salary_currency._convert(credit, self.env.company.currency_id, line.company_id, date or fields.Date.today())
    #             amount_currency = -credit


    #         return {
    #         'name': line.name,
    #         'partner_id': line.partner_id.id,
    #         'account_id': account_id,
    #         'journal_id': line.slip_id.struct_id.journal_id.id,
    #         'currency_id': line.slip_id.salary_currency.id,
    #         'date': date,
    #         'debit': cur_debit,
    #         'credit': cur_credit,
    #         'amount_currency': amount_currency,
    #             'analytic_distribution': {
    #                 str(line.salary_rule_id.analytic_distribution or line.slip_id.employee_id.analytic_distribution): 100} if (
    #                         line.salary_rule_id.analytic_distribution or line.slip_id.employee_id.analytic_distribution) else False,
           
    #     }
    #     else:

    #         if line.salary_rule_id.apper_on_journal:

    #             return {
    #                 'name': line.name,
    #                 'partner_id': line.partner_id.id,
    #                 'account_id': account_id,
    #                 'journal_id': line.slip_id.struct_id.journal_id.id,
    #                 'date': date,
    #                 'debit': debit,
    #                 'credit': credit,
    #                 'analytic_distribution': {str(line.salary_rule_id.analytic_distribution or line.slip_id.employee_id.analytic_distribution): 100} if (line.salary_rule_id.analytic_distribution or
    #                     line.slip_id.employee_id.analytic_distribution) else False,
                    
    #             }

    #         else:                

    #             return {
    #                 'name': line.name,
    #                 'account_id': account_id,
    #                 'journal_id': line.slip_id.struct_id.journal_id.id,
    #                 'date': date,
    #                 'debit': debit,
    #                 'credit': credit,
    #                 'analytic_distribution': {str(line.salary_rule_id.analytic_distribution or line.slip_id.employee_id.analytic_distribution): 100}
    #                 if (line.salary_rule_id.analytic_distribution or line.slip_id.employee_id.analytic_distribution) else False,
                    
    #             }



    # def action_payslip_done(self):
    #     current_company = self.env.company
    #     for payslip in self:
    #         payslip_company = payslip.payslip_run_id.company_id if payslip.payslip_run_id else payslip.company_id
    #         if payslip_company != current_company:
    #             raise ValidationError(
    #                 _("You are currently logged into '%s', but the payslip belongs to '%s'.\n"
    #                   "Please switch to the correct company to proceed.") % (
    #                       current_company.name, payslip_company.name)
    #             )
    #     res = super().action_payslip_done()
    #     return res



    make_visible = fields.Boolean(string="User", compute='get_user')

    @api.depends('make_visible')
    def get_user(self, ):
        user_crnt = self._uid
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        if res_user.has_group('base_rida.rida_finance_manager'):
            self.make_visible = False
        else:
            self.make_visible = True


# class hr_payroll_workflow_run(models.Model):
#     _inherit = 'hr.payslip.run'
#     _description = 'Added workflows to payroll stages'
#     state = fields.Selection([
#         ('01_ready', 'Ready'),
#         ('02_close', 'Done'),
#         ('03_paid', 'Paid'),
#         ('04_cancel', 'Cancelled'),

#         ('draft', 'Draft'), 
#         ('director_approve','HR Director Approve'),
#         ('ccso_approve','CCSO Approve'),
#         ('verify', 'Payslips Approve'),
#         ('paid', 'Paid'),
#         ('close','Confirmed'),
#         ('to_pay','To pay'),
#         ('cancel', 'Rejected')], string='Status', index=True, readonly=True, copy=False, default='01_ready')
#     currency_id = fields.Many2one("res.currency",required=False,default=lambda self: self.env.company.currency_id,tracking=True)
#     structure_id = fields.Many2one('hr.payroll.structure', string='Salary Structure')
#     # Submit Button function
#     def set_to_submit_state_batch(self):  
#         # self.write({'state': 'director_approve'})
#         self.write({'state': 'director_approve'})
#         self.mapped('slip_ids').filtered(lambda slip: slip.state != 'cancel').submit_draft_state()

#     def action_draft(self):
#         self.write({'state': 'draft'})
#         self.mapped('slip_ids').filtered(lambda slip: slip.state != 'cancel').action_draft_state()

#     # HR Director Approve Button function
#     def set_to_director_approve_state_batch(self):  
#         # self.write({'state': 'ccso_approve'})
#         self.write({'state': 'verify'})
#         self.mapped('slip_ids').filtered(lambda slip: slip.state != 'cancel').director_approve_state()

#     # CCSO Approve Button function
#     def set_to_ccso_approve_state_batch(self):  
#         self.write({'state': 'verify'})
#         self.mapped('slip_ids').filtered(lambda slip: slip.state != 'cancel').ccso_approve_state()

#     def action_open_payslip_for_report(self):
#         self.ensure_one()
#         view = self.env.ref('hr_payroll_workflow.view_hr_payslip_treee')

#         return {
#             "type": "ir.actions.act_window",
#             "res_model": "hr.payslip",
#             "view_id": view.id,
#             "view_mode": 'tree',
#             # "view_id": [[hr_pay, "tree"], [False, "form"]],
#             "domain": [['id', 'in', self.slip_ids.ids]],
#             "name": "Payslips",
#         }




class HrContract(models.Model):
    _inherit = 'hr.employee'


    transportion_allowance=fields.Float("Transportation Allowance")
    car_allowance=fields.Float("Car Allowance")
    fuel_allowance=fields.Float("Fuel Allowance")
    phone_allowance=fields.Float("Phone Allowance")
    seconment_allowance=fields.Float("Seconment Allowance")
    medical_allowance=fields.Float("Medical Allowance")
    medicine_allowance=fields.Float("Medicine Allowance")

    other_recevible=fields.Float("Other Receivables")
    other_deductions=fields.Float("Other Deductions")

    acting_allowance=fields.Boolean("Acting Allowance")
    acting_type=fields.Selection([('50','50%'),('30','30%'),('15','15%')],"Acting Allowance")
    acting_amount=fields.Float("Acting Allowance")
    has_fuel_allows=fields.Boolean("Fuel Allowance",default=False)
    has_transport_allows=fields.Boolean("Transportation Allowance",default=False)
    has_car_allows=fields.Boolean("Car Allowance",default=False)
    has_phone_allows=fields.Boolean("Phone Allowance",default=False)
    has_scarcity_allowance=fields.Boolean("Scarcity Allowance",default=False)

    employee_type=fields.Selection(related="employee_id.rida_employee_type")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account",)
    workeddays=fields.Float("Working Days ")

    @api.onchange('department_id')
    def get_analytic_account_id(self):
        for rec in self:
            if  rec.department_id.analytic_account_id:
                rec.analytic_account_id = rec.department_id.analytic_account_id
            else:
                rec.analytic_account_id =False

    @api.onchange('acting_type')
    def get_acting_amount(self):
        if self.acting_allowance:
            self.acting_amount = float(str(self.acting_type))
        else:
            pass

    def _compute_dummy(self):
        pass

    @api.onchange('has_transport_allows')
    def get_trans_allowances(self):
        for rec in self:
            allowance_ids=self.env['hr.contract.allowance'].search([],limit=1)
            for recc in allowance_ids:
                if rec.has_transport_allows:
                    rec.transportion_allowance=recc.transportion_allowance

    @api.onchange('has_car_allows')
    def get_car_allowances(self):
        for rec in self:
            allowance_ids=self.env['hr.contract.allowance'].search([],limit=1)
            for recc in allowance_ids:
                if rec.has_car_allows:
                    rec.car_allowance=recc.car_allowance

    @api.onchange('has_fuel_allows')
    def get_fuel_allowance(self):
        for rec in self:
            allowance_ids=self.env['hr.contract.allowance'].search([],limit=1)
            for recc in allowance_ids:
                if rec.has_fuel_allows:
                    rec.fuel_allowance=recc.fuel_allowance

    @api.onchange('has_phone_allows')
    def get_phone_allowance(self):
        for rec in self:
            allowance_ids=self.env['hr.contract.allowance'].search([],limit=1)
            for recc in allowance_ids:
                if rec.has_phone_allows:
                    rec.phone_allowance=recc.phone_allowance

class HrContract(models.Model):
    _inherit = 'hr.employee.public'

    transportion_allowance = fields.Float("Transportation Allowance")
    car_allowance=fields.Float("Car Allowance")
    fuel_allowance=fields.Float("Fuel Allowance")
    phone_allowance=fields.Float("Phone Allowance")
    seconment_allowance=fields.Float("Seconment Allowance")
    medical_allowance=fields.Float("Medical Allowance")
    medicine_allowance=fields.Float("Medicine Allowance")
    other_recevible=fields.Float("Other Receivables")
    other_deductions=fields.Float("Other Deductions")
    acting_allowance=fields.Boolean("Acting Allowance")
    acting_type=fields.Selection([('50','50%'),('30','30%'),('15','15%')],"Acting Allowance")
    acting_amount=fields.Float("Acting Allowance")
    has_fuel_allows=fields.Boolean("Fuel Allowance",default=False)
    has_transport_allows=fields.Boolean("Transportation Allowance",default=False)
    has_car_allows=fields.Boolean("Car Allowance",default=False)
    has_phone_allows=fields.Boolean("Phone Allowance",default=False)
    has_scarcity_allowance=fields.Boolean("Scarcity Allowance",default=False)
    workeddays=fields.Float("Working Days ")



class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    analytic_account_id = fields.Many2one("account.analytic.account",string="Cost Center")



class HrContractallowances(models.Model):
    _name = 'hr.contract.allowance'

    name=fields.Char("Name")
    transportion_allowance=fields.Float("Transportation Allowance",default=45000)
    car_allowance=fields.Float("Car Allowance",default=250000)
    fuel_allowance=fields.Float("Fuel Allowance",default=65000)
    phone_allowance=fields.Float("Phone Allowance")

    @api.onchange('car_allowance')
    def onchange_car(self):
        employee_contract_id=self.env['hr.contract'].search([('has_car_allows','=',True)])
        for emp in employee_contract_id:
            emp.car_allowance= self.car_allowance

    @api.onchange('fuel_allowance')
    def onchange_fuel(self):
        employee_contract_id=self.env['hr.contract'].search([('has_fuel_allows','=',True)])
        for emp in employee_contract_id:
            emp.fuel_allowance= self.fuel_allowance

    @api.onchange('phone_allowance')
    def onchange_phone(self):
        employee_contract_id=self.env['hr.contract'].search([('has_phone_allows','=',True)])
        for emp in employee_contract_id:
            emp.phone_allowance= self.phone_allowance


    @api.onchange('transportion_allowance')
    def onchange_transportation(self):
        employee_contract_id=self.env['hr.contract'].search([('has_transport_allows','=',True)])
        for emp in employee_contract_id:
            emp.transportion_allowance= self.transportion_allowance


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    apper_on_journal = fields.Boolean(string="Appears on Payslip On Journal")

class HrPayslinputType(models.Model):
    _inherit = 'hr.payslip.input.type'

    sequence = fields.Integer(string='Sequence')
    car_allowance=fields.Float("Car Allowance")
    fuel_allowance=fields.Float("Fuel Allowance")
    phone_allowance=fields.Float("Phone Allowance")
    seconment_allowance=fields.Float("Seconment Allowance")
    medical_allowance=fields.Float("Medical Allowance")
    medicine_allowance=fields.Float("Medicine Allowance")

    other_recevible=fields.Float("Other Receivables")
    other_deductions=fields.Float("Other Deductions")

    acting_allowance=fields.Boolean("Acting Allowance")
    acting_type=fields.Selection([('50','50%'),('30','30%'),('15','15%')],"Acting Allowance")
    acting_amount=fields.Float("Acting Allowance")
    has_fuel_allows=fields.Boolean("Fuel Allowance",default=False)
    has_transport_allows=fields.Boolean("Transportation Allowance",default=False)
    has_car_allows=fields.Boolean("Car Allowance",default=False)
    has_phone_allows=fields.Boolean("Phone Allowance",default=False)
    has_scarcity_allowance=fields.Boolean("Scarcity Allowance",default=False)
    workeddays=fields.Float("Working Days ")