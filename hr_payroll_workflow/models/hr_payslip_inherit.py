# -*- coding: utf-8 -*-

from odoo import  api, fields, models, _
import base64
import logging
_logger = logging.getLogger(__name__)
from odoo.fields import Domain

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from collections import defaultdict

from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round, date_utils
from odoo.tools.misc import format_date
from odoo.tools import float_compare, float_is_zero
from odoo.tools.safe_eval import safe_eval
from collections import defaultdict

from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    _description = 'Added workflows to payroll stages'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('paid', 'Paid'),
        ('cancel', 'Canceled')],
        string='State', index=True, readonly=True, copy=False,
        default='draft', tracking=True,
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is confirmed then status is set to \'Done\'.
                \n* When the user cancels a payslip, the status is \'Canceled\'.""")
    state_display = fields.Selection([
            ('draft', 'Draft'),
            ('validated', 'Done'),
            ('paid', 'Paid'),
            ('cancel', 'Canceled'),
            ('warning', 'Warning'),
            ('error', 'Error'),
        ],
        string='Status',
        compute='_compute_state_display',
        store=True,
        readonly=True,
    )
    salary_currency = fields.Many2one(related='employee_id.salary_currency')
    analytic_account_id = fields.Many2one("account.analytic.account",string='Analytic Account')
    take_home = fields.Float(string="Take Home",readonly=False)
    payslip_day = fields.Float(string="WorkedDays",readonly=True,store=True)
    take_home_wage = fields.Monetary(compute='_compute_basic_net',)

    employee_code=fields.Char(related="employee_id.emp_code")
    bank_acc_id=fields.Many2one(related="employee_id.bank_account_id",string="Bank Account Number",store=True)
    bank_id=fields.Many2one(related="bank_acc_id.bank_id",string="Bank Account Number",store=True)

    def _check_send_payslip_mail(self):
        # Skip sending email for all payslips
        return False

    def _generate_pdf(self):
        # Prevent PDF generation and email sending
        return False
        
    @api.model_create_multi
    def create(self, vals_list):
        payslips = super().create(vals_list)

        for payslip in payslips:
            if not payslip.struct_id:
                continue
            payslip.analytic_account_id = payslip.employee_id.department_id.analytic_account_id
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

 

    def compute_sheet(self):
        result = True
        for slip in self:
            slip.caculate_workdays_take_home()
            slip.compute_mazaya()
            result = super(HrPayslip, slip).compute_sheet()

            th_lines = slip.line_ids.filtered(lambda l: l.code == 'TH')
            slip.take_home = sum(th_lines.mapped('total')) if th_lines else 0.0

        return result

    def caculate_workdays_take_home(self):
        for rec in self:
            # rec.analytic_account_id = rec.employee_id.department_id.analytic_account_id

            employee_start = rec.employee_id.date_start
            date_from = rec.date_from
            date_to = rec.date_to

            if not employee_start or not date_from or not date_to:
                rec.payslip_day = 30
                continue

            if date_from <= employee_start <= date_to:
                d1 = employee_start.day
                d2 = date_from.day

                if d1 == d2:
                    rec.payslip_day = 30
                else:
                    d22 = date_to.day
                    rec.payslip_day = 32 - d1 if (d22 - d2) != 29 else 31 - d1
            else:
                rec.payslip_day = 30



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


    def _action_create_account_move(self):
        AccountMove = self.env["account.move"]
        created_moves = self.env["account.move"]

        if self.env.context.get("skip_grouped_payroll_move"):
            return created_moves

        runs = self.mapped("payslip_run_id")

        if runs:
            slips_to_process = runs.mapped("slip_ids").filtered(
                lambda s: s.journal_id and not s.move_id and s.state != "cancel"
            )
        else:
            slips_to_process = self.filtered(
                lambda s: s.journal_id and not s.move_id and s.state != "cancel"
            )

        if not slips_to_process:
            return created_moves

        grouped_slips = defaultdict(list)

        for slip in slips_to_process:
            analytic = slip.version_id.analytic_distribution or {}
            analytic_key = tuple(sorted(analytic.items()))
            grouped_slips[analytic_key].append(slip.id)

        for analytic_key, slip_ids in grouped_slips.items():
            slips = self.browse(slip_ids)
            analytic_dict = dict(analytic_key)

            company = slips[0].company_id
            company_currency = company.currency_id
            date = slips[0].date_to or fields.Date.today()

            grouped_lines = defaultdict(lambda: {
                "name": "",
                "account_id": False,
                "debit": 0.0,
                "credit": 0.0,
                "amount_currency": 0.0,
                "currency_id": False,
                "analytic_distribution": {},
            })

            for slip in slips:
                salary_currency = slip.salary_currency 

                for line in slip.line_ids:
                    rule = line.salary_rule_id
                    amount = salary_currency.round(line.total)

                    if float_is_zero(amount, precision_rounding=salary_currency.rounding):
                        continue

                    def _convert_amount(debit, credit):
                        amount_currency = 0.0
                        debit_company = debit
                        credit_company = credit
                        currency_id = False

                        if salary_currency != company_currency:
                            currency_id = salary_currency.id

                            if debit > 0:
                                debit_company = salary_currency._convert(
                                    debit,
                                    company_currency,
                                    company,
                                    date,
                                )
                                amount_currency = debit

                            if credit > 0:
                                credit_company = salary_currency._convert(
                                    credit,
                                    company_currency,
                                    company,
                                    date,
                                )
                                amount_currency = -credit

                        return (
                            company_currency.round(debit_company),
                            company_currency.round(credit_company),
                            salary_currency.round(amount_currency),
                            currency_id,
                        )

                    if rule.account_debit:
                        debit = amount if amount > 0 else 0.0
                        credit = -amount if amount < 0 else 0.0

                        debit_company, credit_company, amount_currency, currency_id = _convert_amount(debit, credit)

                        key = (
                            rule.account_debit.id,
                            "debit",
                            analytic_key,
                            currency_id,
                        )

                        grouped_lines[key]["name"] = rule.name
                        grouped_lines[key]["account_id"] = rule.account_debit.id
                        grouped_lines[key]["debit"] += debit_company
                        grouped_lines[key]["credit"] += credit_company
                        grouped_lines[key]["amount_currency"] += amount_currency
                        grouped_lines[key]["currency_id"] = currency_id
                        grouped_lines[key]["analytic_distribution"] = analytic_dict

                    if rule.account_credit:
                        debit = -amount if amount < 0 else 0.0
                        credit = amount if amount > 0 else 0.0

                        debit_company, credit_company, amount_currency, currency_id = _convert_amount(debit, credit)

                        key = (
                            rule.account_credit.id,
                            "credit",
                            currency_id,
                        )

                        grouped_lines[key]["name"] = rule.name
                        grouped_lines[key]["account_id"] = rule.account_credit.id
                        grouped_lines[key]["debit"] += debit_company
                        grouped_lines[key]["credit"] += credit_company
                        grouped_lines[key]["amount_currency"] += amount_currency
                        grouped_lines[key]["currency_id"] = currency_id
                        grouped_lines[key]["analytic_distribution"] = {}

            move_lines = []

            for data in grouped_lines.values():
                debit = company_currency.round(data["debit"])
                credit = company_currency.round(data["credit"])

                if (
                    float_is_zero(debit, precision_rounding=company_currency.rounding)
                    and float_is_zero(credit, precision_rounding=company_currency.rounding)
                ):
                    continue

                vals = {
                    "name": data["name"] or "Payroll",
                    "account_id": data["account_id"],
                    "debit": debit,
                    "credit": credit,
                    "analytic_distribution": data["analytic_distribution"],
                }

                if data["currency_id"]:
                    vals.update({
                        "currency_id": data["currency_id"],
                        "amount_currency": data["amount_currency"],
                    })

                move_lines.append((0, 0, vals))

            total_debit = company_currency.round(sum(line[2]["debit"] for line in move_lines))
            total_credit = company_currency.round(sum(line[2]["credit"] for line in move_lines))
            difference = company_currency.round(total_debit - total_credit)

            if not float_is_zero(difference, precision_rounding=company_currency.rounding):
                if difference < 0:
                    adjustment_account = company.expense_currency_exchange_account_id
                    adjustment_debit = abs(difference)
                    adjustment_credit = 0.0
                else:
                    adjustment_account = company.income_currency_exchange_account_id
                    adjustment_debit = 0.0
                    adjustment_credit = difference

                if not adjustment_account:
                    raise UserError(
                        "Missing exchange difference account.\n"
                        "Difference: %s" % difference
                    )

                move_lines.append((0, 0, {
                    "name": "Exchange Difference Adjustment",
                    "account_id": adjustment_account.id,
                    "debit": company_currency.round(adjustment_debit),
                    "credit": company_currency.round(adjustment_credit),
                    "analytic_distribution": {},
                }))

            total_debit = company_currency.round(sum(line[2]["debit"] for line in move_lines))
            total_credit = company_currency.round(sum(line[2]["credit"] for line in move_lines))

            if float_compare(total_debit, total_credit, precision_rounding=company_currency.rounding) != 0:
                raise UserError(
                    "Grouped payroll entry is not balanced.\n"
                    "Debit: %s\nCredit: %s\nDifference: %s"
                    % (total_debit, total_credit, company_currency.round(total_debit - total_credit))
                )

            move = AccountMove.create({
                "journal_id": slips[0].journal_id.id,
                "date": date,
                "company_id": company.id,
                "line_ids": move_lines,
                "ref": "Payroll - Grouped by Analytic",
                'state':'draft'
            })

            slips.with_context(skip_grouped_payroll_move=True).write({
                "move_id": move.id
            })

            created_moves |= move

        return created_moves





    make_visible = fields.Boolean(string="User", compute='get_user')

    @api.depends('make_visible')
    def get_user(self, ):
        user_crnt = self._uid
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        if res_user.has_group('base_rida.rida_finance_manager'):
            self.make_visible = False
        else:
            self.make_visible = True





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
            if rec.department_id.analytic_account_id:
                analytic = rec.department_id.analytic_account_id
                rec.analytic_account_id = analytic
                rec.analytic_distribution = {analytic.id: 100}
            else:
                rec.analytic_account_id = False
                rec.analytic_distribution = {}


    # @api.onchange('department_id')
    # def get_analytic_account_id(self):
    #     for rec in self:
    #         if  rec.department_id.analytic_account_id:
    #             rec.analytic_account_id = rec.department_id.analytic_account_id
    #         else:
    #             rec.analytic_account_id =False

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


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def _get_valid_version_ids(self, date_start=None, date_end=None, structure_id=None, company_id=None, employee_ids=None, schedule_pay=None):
        date_start = date_start or self.date_start
        date_end = date_end or self.date_end
        structure = self.env["hr.payroll.structure"].browse(structure_id) if structure_id else self.structure_id
        schedule_pay = schedule_pay or self.schedule_pay
        company = company_id or self.company_id.id
        version_domain = Domain([
            ('company_id', '=', company),
            ('employee_id', '!=', False),
            ('employee_id.is_susupend', '=', False),
            ('contract_date_start', '<=', date_end),
            '|',
                ('contract_date_end', '=', False),
                ('contract_date_end', '>=', date_start),
            ('date_version', '<=', date_end),
            ('structure_type_id', '!=', False),
        ])
        if structure:
            version_domain &= Domain([('structure_type_id', '=', structure.type_id.id)])
        if employee_ids:
            version_domain &= Domain([('employee_id', 'in', employee_ids)])
        if schedule_pay:
            version_domain &= Domain([('schedule_pay', '=', schedule_pay)])
        all_versions = self.env['hr.version']._read_group(
            domain=version_domain,
            groupby=['employee_id', 'date_version:day'],
            order="date_version:day DESC",
            aggregates=['id:recordset'],
        )
        all_employee_versions = defaultdict(list)
        for employee, _, version in all_versions:
            all_employee_versions[employee] += [*version]
        valid_versions = self.env["hr.version"]
        for employee_versions in all_employee_versions.values():
            employee_valid_versions = self.env["hr.version"]
            for i in range(len(employee_versions)):
                version = employee_versions[i]
                if version.date_version <= date_start or employee_versions[-1] == version:
                    # End case: The first version in contract before the pay run start or the last version of the list
                    employee_valid_versions |= version
                    break
                if employee_valid_versions:
                    # Version already added => new contract?
                    if (employee_valid_versions[-1].contract_date_start > version.contract_date_start
                        and (version.contract_date_start >= version.date_version
                            or version.contract_date_start > employee_versions[i + 1].contract_date_start)):
                        # Take only the first version of the new contract founded
                        employee_valid_versions |= version
                elif version.contract_date_start >= version.date_version or version.contract_date_start > employee_versions[i + 1].contract_date_start:
                    # Take only the first version of the first contract founded
                    employee_valid_versions |= version
            valid_versions |= employee_valid_versions
        return valid_versions.ids



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