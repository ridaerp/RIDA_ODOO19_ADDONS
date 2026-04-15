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

class hr_payroll_workflow(models.Model):
    _inherit = 'hr.payslip'
    _description = 'Added workflows to payroll stages'

    salary_currency = fields.Many2one(related='employee_id.salary_currency')
    analytic_account_id = fields.Many2one("account.analytic.account",string='Analytic Account')
    take_home = fields.Float(string="Take Home",readonly=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('director_approve','Payroll Manager Approve'),
        ('ccso_approve','CCSO Approve'),
        ('verify','verify'),
        ('paid' , 'Paid'),
        ('done', 'Confirmed'),
        ('cancel', 'Rejected'),
        ('to_pay','To pay')
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, the status is \'Waiting\'.
                \n* If the payslip is confirmed then status is set to \'Confirmed\'.
                \n* When user cancel payslip the status is \'Rejected\'.""")

    payslip_day = fields.Float(string="WorkedDays",readonly=True)

    take_home_wage = fields.Monetary(compute='_compute_basic_net')

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


    # @api.model
    # def create(self, vals):
    #     res = super(hr_payroll_workflow, self).create(vals)
    #     # allowed_input_types = res.struct_id.input_line_type_ids
    #     allowed_input_types = res.struct_id.input_line_type_ids.sorted(key=lambda x: x.sequence, reverse=True)
    #     # Get existing input lines
    #     # Create or update input lines
    #     for input_type in allowed_input_types:
    #             input_line = self.env['hr.payslip.input'].create({
    #                 'payslip_id': res.id,
    #                 'input_type_id': input_type.id,
    #                 'amount': 0.0,  # Default amount
    #                 'version_id': res.version_id.id,
    #             })
    #     return res

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


        return super(hr_payroll_workflow, self).unlink()

    @api.depends('date_from','mazaya_id','payslip_day')
    def compute_mazaya(self):
        for record in self:
            mazaya_total = mazaya_tax = 0
            Y,m,d = str(record.date_from).split('-')
            months = int(m)
            maz_lin_obj = self.env['rida.mazaya.line']

            basic_sal =((record.employee_id.payroll_wage/30)*record.payslip_day)* 61/100

            gross_sal = record.employee_id.payroll_wage
            if record.mazaya_id:
                maz_mon = maz_lin_obj.search([('month','=',months), ('mazaya_id','=',record.mazaya_id.id)])
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
                    self.mazaya_cash= mazaya_cash
                    self.mazaya_dress= mazaya_dress
                    self.mazaya_midical= mazaya_midical
                    self.mazaya_grant= mazaya_grant
                    self.mazaya_total= mazaya_total
                    self.mazaya_tax = mazaya_tax

    ############ekhlas code ###################

    def _compute_basic_net(self):
        super(hr_payroll_workflow,self)._compute_basic_net()
        for payslip in self:
            payslip.basic_wage = payslip._get_salary_line_total('BASIC')
            payslip.net_wage = payslip._get_salary_line_total('NET')
            payslip.take_home_wage = payslip._get_salary_line_total('TH')


    ############end of code ###################


    ############ekhlas code ###################
    def caculate_workdays_take_home(self):
        for rec in self:
            rec.analytic_account_id=rec.employee_id.analytic_account_id
            lines=self.env['hr.payslip.line'].search([('slip_id','=',rec.id),('code','=','TH')])
            for line in lines:
                rec.take_home=line.amount
            if rec.employee_id.date_start<=rec.date_to and rec.employee_id.date_start>=rec.date_from:
                d1=datetime.strptime(str(rec.employee_id.date_start),"%Y-%m-%d").day
                d2=datetime.strptime(str(rec.date_from),"%Y-%m-%d").day

                if d2==d1:
                    rec.payslip_day=30

                else:
                    d11=datetime.strptime(str(rec.date_from),"%Y-%m-%d").day
                    d22=datetime.strptime(str(rec.date_to),"%Y-%m-%d").day
                    if d22-d11!=29:
                        rec.payslip_day=32-d1

                    else:
                        rec.payslip_day=31-d1

            else:
                rec.payslip_day=30


    def compute_sheet(self):
        res = super(hr_payroll_workflow,self).compute_sheet()
        # for payslip in payslips:
        self.write({'state':'draft'})
        self.caculate_workdays_take_home()

        return res

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


    
    def _prepare_line_values(self, line, account_id, date, debit, credit):
        # res = super(hr_payroll_workflow, self)._prepare_line_values()

        """ Extend Odoo Default method _prepare_line_values() 
            - Add multi currency feature to the function by comparing currency of payroll with the default company currency
              if it's differet from the company currency then we will convert it to the default currency by function:
              payroll_currency._convert(amount,company_currency,company,date) """
              
        if self.salary_currency.id != self.env.company.currency_id.id:
            cur_credit = cur_debit = amount_currency = 0.00
            if debit > 0:
                cur_debit = self.salary_currency._convert(debit, self.env.company.currency_id, line.company_id, date or fields.Date.today())
                amount_currency = debit
            if credit > 0:
                cur_credit = self.salary_currency._convert(credit, self.env.company.currency_id, line.company_id, date or fields.Date.today())
                amount_currency = -credit


            return {
            'name': line.name,
            'partner_id': line.partner_id.id,
            'account_id': account_id,
            'journal_id': line.slip_id.struct_id.journal_id.id,
            'currency_id': line.slip_id.salary_currency.id,
            'date': date,
            'debit': cur_debit,
            'credit': cur_credit,
            'amount_currency': amount_currency,
                'analytic_distribution': {
                    str(line.salary_rule_id.analytic_account_id.id or line.slip_id.employee_id.analytic_account_id.id): 100} if (
                            line.salary_rule_id.analytic_account_id or line.slip_id.employee_id.analytic_account_id) else False,
           
        }
        else:

            if line.salary_rule_id.apper_on_journal:

                return {
                    'name': line.name,
                    'partner_id': line.partner_id.id,
                    'account_id': account_id,
                    'journal_id': line.slip_id.struct_id.journal_id.id,
                    'date': date,
                    'debit': debit,
                    'credit': credit,
                    'analytic_distribution': {str(line.salary_rule_id.analytic_account_id.id or line.slip_id.employee_id.analytic_account_id.id): 100} if (line.salary_rule_id.analytic_account_id or
                        line.slip_id.employee_id.analytic_account_id) else False,
                    
                }

            else:                

                return {
                    'name': line.name,
                    'account_id': account_id,
                    'journal_id': line.slip_id.struct_id.journal_id.id,
                    'date': date,
                    'debit': debit,
                    'credit': credit,
                    'analytic_distribution': {str(line.salary_rule_id.analytic_account_id.id or line.slip_id.employee_id.analytic_account_id.id): 100}
                    if (line.salary_rule_id.analytic_account_id or line.slip_id.employee_id.analytic_account_id) else False,
                    
                }


    #############################added by ekhlas code
    def action_payslip_done(self):
        current_company = self.env.company
        for payslip in self:
            payslip_company = payslip.payslip_run_id.company_id if payslip.payslip_run_id else payslip.company_id
            if payslip_company != current_company:
                raise ValidationError(
                    _("You are currently logged into '%s', but the payslip belongs to '%s'.\n"
                      "Please switch to the correct company to proceed.") % (
                          current_company.name, payslip_company.name)
                )

        res = super().action_payslip_done()
        self._action_create_account_move()
        return res


    make_visible = fields.Boolean(string="User", compute='get_user')

    @api.depends('make_visible')
    def get_user(self, ):
        user_crnt = self._uid
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        if res_user.has_group('base_rida.rida_finance_manager'):
            self.make_visible = False
        else:
            self.make_visible = True


class hr_payroll_workflow_run(models.Model):
    _inherit = 'hr.payslip.run'
    _description = 'Added workflows to payroll stages'
    state = fields.Selection([
        ('01_ready', 'Ready'),
        ('02_close', 'Done'),
        ('03_paid', 'Paid'),
        ('04_cancel', 'Cancelled'),

        ('draft', 'Draft'), 
        ('director_approve','HR Director Approve'),
        ('ccso_approve','CCSO Approve'),
        ('verify', 'Payslips Approve'),
        ('paid', 'Paid'),
        ('close','Confirmed'),
        ('to_pay','To pay'),
        ('cancel', 'Rejected')], string='Status', index=True, readonly=True, copy=False, default='draft')
    currency_id = fields.Many2one("res.currency",required=False,default=lambda self: self.env.company.currency_id,tracking=True)
    structure_id = fields.Many2one('hr.payroll.structure', string='Salary Structure')
    # Submit Button function
    def set_to_submit_state_batch(self):  
        # self.write({'state': 'director_approve'})
        self.write({'state': 'director_approve'})
        self.mapped('slip_ids').filtered(lambda slip: slip.state != 'cancel').submit_draft_state()

    def action_draft(self):
        self.write({'state': 'draft'})
        self.mapped('slip_ids').filtered(lambda slip: slip.state != 'cancel').action_draft_state()

    # HR Director Approve Button function
    def set_to_director_approve_state_batch(self):  
        # self.write({'state': 'ccso_approve'})
        self.write({'state': 'verify'})
        self.mapped('slip_ids').filtered(lambda slip: slip.state != 'cancel').director_approve_state()

    # CCSO Approve Button function
    def set_to_ccso_approve_state_batch(self):  
        self.write({'state': 'verify'})
        self.mapped('slip_ids').filtered(lambda slip: slip.state != 'cancel').ccso_approve_state()

    def action_open_payslip_for_report(self):
        self.ensure_one()
        view = self.env.ref('hr_payroll_workflow.view_hr_payslip_treee')

        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip",
            "view_id": view.id,
            "view_mode": 'tree',
            # "view_id": [[hr_pay, "tree"], [False, "form"]],
            "domain": [['id', 'in', self.slip_ids.ids]],
            "name": "Payslips",
        }


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