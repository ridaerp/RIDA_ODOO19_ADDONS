from odoo import api, fields, models
from datetime import datetime


class ProfitLossCustom(models.TransientModel):
    _name = 'profit.loss.custom'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    date_from = fields.Date('From', default=lambda self: datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d'))
    date_to = fields.Date('To', default=fields.Date.today())
    analytic_account_ids = fields.Many2many('account.analytic.account', string='Analytic Accounts')
    account_ids = fields.Many2many('account.account', string='Accounts')
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True, default='posted')
    with_details = fields.Boolean(string="With Details")

    def _compute_account_balance(self, accounts, other_domain):
        domain = [('account_id.id', '=', accounts.id)]
        if other_domain:
            domain += other_domain
        res = []
        account = self.env['account.move.line'].search(domain)
        debit = sum(rec.debit for rec in account)
        credit = sum(rec.credit for rec in account)
        balance = sum(rec.balance for rec in account)
        res.append([debit, credit, abs(balance)])
        return res

    def print_report(self):
        ####################################################### Total Income
        if self.account_ids:
            accounts = self.env['account.account'].search(
                [('id', 'in', self.account_ids.ids), ('user_type_id.name', '=', 'Income'),
                 ('company_id', '=', self.company_id.id)])
        else:
            accounts = self.env['account.account'].search(
                [('user_type_id.name', '=', 'Income'), ('company_id', '=', self.company_id.id)])
        list_accounts_total_income = []
        debit_balance = 0
        credit_balance = 0
        balance = 0
        other_domain = []
        if self.analytic_account_ids:
            other_domain += [('analytic_account_id.id', 'in', self.analytic_account_ids.ids)]
        if self.target_move == 'posted':
            other_domain += ['&', ('move_id.state', '=', 'posted')]
        if self.date_from or self.date_to:
            other_domain += [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        for rec in accounts:
            x = self._compute_account_balance(rec, other_domain)
            list_accounts_total_income.append([rec.name, rec.code, x])
            if x[0][2]:
                debit_balance += x[0][0]
                credit_balance += x[0][1]
                balance += x[0][2]
        total_income = abs(balance)

        ####################################################### Other Income
        if self.account_ids:
            accounts = self.env['account.account'].search(
                [('id', 'in', self.account_ids.ids), ('user_type_id.name', '=', 'Other Income'),
                 ('company_id', '=', self.company_id.id)])
        else:
            accounts = self.env['account.account'].search(
                [('user_type_id.name', '=', 'Other Income'), ('company_id', '=', self.company_id.id)])
        list_accounts_other_income = []
        debit_balance = 0
        credit_balance = 0
        balance = 0
        other_domain = []
        if self.analytic_account_ids:
            other_domain += [('analytic_account_id.id', 'in', self.analytic_account_ids.ids)]
        if self.target_move == 'posted':
            other_domain += ['&', ('move_id.state', '=', 'posted')]
        if self.date_from or self.date_to:
            other_domain += [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        for rec in accounts:
            x = self._compute_account_balance(rec, other_domain)
            list_accounts_other_income.append([rec.name, rec.code, x])
            if x[0][2]:
                debit_balance += x[0][0]
                credit_balance += x[0][1]
                balance += x[0][2]
        total_other_income = abs(balance)
        ################################################### less: Government Deduction 
        if self.account_ids:
            accounts = self.env['account.account'].search(
                ['|', ('user_type_id.name', '=', 'Expenses'), ('user_type_id.name', '=', 'Cost of Revenue'),
                 ('company_id', '=', self.company_id.id), ('id', 'in', self.account_ids.ids)])
            accounts = self.env['account.account'].search(
                [('group_id.name', '=', 'Government Deductions'), ('id', 'in', accounts.ids)])
        else:
            accounts = self.env['account.account'].search(
                ['|', ('user_type_id.name', '=', 'Expenses'), ('user_type_id.name', '=', 'Cost of Revenue'),
                 ('company_id', '=', self.company_id.id)])
            accounts = self.env['account.account'].search(
                [('group_id.name', '=', 'Government Deductions'), ('id', 'in', accounts.ids)])
        debit_balance = 0
        credit_balance = 0
        balance = 0
        list_accounts_government_deductions = []
        if self.analytic_account_ids:
            other_domain += [('analytic_account_id.id', 'in', self.analytic_account_ids.ids)]
        if self.target_move == 'posted':
            other_domain += ['&', ('move_id.state', '=', 'posted')]
        if self.date_from or self.date_to:
            other_domain += [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        for rec in accounts:
            x = self._compute_account_balance(rec, other_domain)
            list_accounts_government_deductions.append([rec.name, rec.code, x])
            if x[0][2]:
                debit_balance += x[0][0]
                credit_balance += x[0][1]
                balance += x[0][2]
        total_government_deductions = balance
        ###################################### Total Cost Of Revenu
        ################################ Direct Cost (Wage)
        if self.account_ids:
            accounts = self.env['account.account'].search(
                [('group_id.name', '=', 'Salaries & Benefits'), ('id', 'in', self.account_ids.ids),
                 ('company_id', '=', self.company_id.id)])
        else:
            accounts = self.env['account.account'].search(
                [('group_id.name', '=', 'Salaries & Benefits'), ('company_id', '=', self.company_id.id)])

        list_accounts_direct_cost_wage = []
        debit_balance = 0
        credit_balance = 0
        balance = 0
        other_domain = [('analytic_account_id.analytic_type', '=', 'prod_cost_center')]
        if self.analytic_account_ids:
            other_domain += [('analytic_account_id.id', 'in', self.analytic_account_ids.ids)]
        if self.target_move == 'posted':
            other_domain += ['&', ('move_id.state', '=', 'posted')]
        if self.date_from or self.date_to:
            other_domain += [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        for rec in accounts:
            x = self._compute_account_balance(rec, other_domain)
            list_accounts_direct_cost_wage.append([rec.name, rec.code, x])
            if x[0][2]:
                debit_balance += x[0][0]
                credit_balance += x[0][1]
                balance += x[0][2]
        total_direct_cost_wage = balance
        ###################################### Total Cost Of Revenu
        ################################  Direct Cost  (Expense)
        if self.account_ids:
            accounts = self.env['account.account'].search(
                ['|', ('user_type_id.name', '=', 'Expenses'), ('user_type_id.name', '=', 'Cost of Revenue'),
                 ('company_id', '=', self.company_id.id), ('id', 'in', self.account_ids.ids)])
            accounts = self.env['account.account'].search(
                [('id', 'in', accounts.ids), ('group_id.name', '!=', 'Salaries & Benefits'),
                 ('group_id.name', '!=', 'Raw Material')])
        else:
            accounts = self.env['account.account'].search(
                ['|', ('user_type_id.name', '=', 'Expenses'), ('user_type_id.name', '=', 'Cost of Revenue'),
                 ('company_id', '=', self.company_id.id)])
            accounts = self.env['account.account'].search(
                [('id', 'in', accounts.ids), ('group_id.name', '!=', 'Salaries & Benefits'),
                 ('group_id.name', '!=', 'Raw Material')])
        list_accounts_direct_cost_expense = []
        debit_balance = 0
        credit_balance = 0
        balance = 0
        other_domain = [('analytic_account_id.analytic_type', '=', 'prod_cost_center')]
        if self.analytic_account_ids:
            other_domain += [('analytic_account_id.id', 'in', self.analytic_account_ids.ids)]
        if self.target_move == 'posted':
            other_domain += ['&', ('move_id.state', '=', 'posted')]
        if self.date_from or self.date_to:
            other_domain += [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        for rec in accounts:
            x = self._compute_account_balance(rec, other_domain)
            list_accounts_direct_cost_expense.append([rec.name, rec.code, x])
            if x[0][2]:
                debit_balance += x[0][0]
                credit_balance += x[0][1]
                balance += x[0][2]
        total_direct_cost_expense = balance
        ###################################### Total Cost Of Revenu
        ################################ InDirect Cost (Wage)
        if self.account_ids:
            accounts = self.env['account.account'].search(
                [('group_id.name', '=', 'Salaries & Benefits'), ('id', 'in', self.account_ids.ids),
                 ('company_id', '=', self.company_id.id)])
        else:
            accounts = self.env['account.account'].search(
                [('group_id.name', '=', 'Salaries & Benefits'), ('company_id', '=', self.company_id.id)])
        list_accounts_indirect_cost_wage = []
        debit_balance = 0
        credit_balance = 0
        balance = 0
        other_domain = [('analytic_account_id.analytic_type', '=', 'ser_cost_center')]
        if self.analytic_account_ids:
            other_domain += [('analytic_account_id.id', 'in', self.analytic_account_ids.ids)]
        if self.target_move == 'posted':
            other_domain += ['&', ('move_id.state', '=', 'posted')]
        if self.date_from or self.date_to:
            other_domain += [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        for rec in accounts:
            x = self._compute_account_balance(rec, other_domain)
            list_accounts_indirect_cost_wage.append([rec.name, rec.code, x])
            if x[0][2]:
                debit_balance += x[0][0]
                credit_balance += x[0][1]
                balance += x[0][2]
        total_indirect_cost_wage = balance
        ###################################### Total Cost Of Revenu
        ################################### Direct Material
        if self.account_ids:
            accounts = self.env['account.account'].search(
                [('group_id.name', '=', 'Raw Material'), ('id', 'in', self.account_ids.ids),
                 ('company_id', '=', self.company_id.id)])
        else:
            accounts = self.env['account.account'].search(
                [('group_id.name', '=', 'Raw Material'), ('company_id', '=', self.company_id.id)])

        list_accounts_direct_material = []
        debit_balance = 0
        credit_balance = 0
        balance = 0
        other_domain = [('analytic_account_id.analytic_type', '=', 'prod_cost_center')]
        if self.analytic_account_ids:
            other_domain += [('analytic_account_id.id', 'in', self.analytic_account_ids.ids)]
        if self.target_move == 'posted':
            other_domain += ['&', ('move_id.state', '=', 'posted')]
        if self.date_from or self.date_to:
            other_domain += [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        for rec in accounts:
            x = self._compute_account_balance(rec, other_domain)
            list_accounts_direct_material.append([rec.name, rec.code, x])
            if x[0][2]:
                debit_balance += x[0][0]
                credit_balance += x[0][1]
                balance += x[0][2]
        total_direct_material = balance

        ###################################### Total Cost Of Revenu
        ################################  InDirect Cost  (Expense)
        if self.account_ids:
            accounts = self.env['account.account'].search(
                ['|', ('user_type_id.name', '=', 'Expenses'), ('user_type_id.name', '=', 'Cost of Revenue'),
                 ('company_id', '=', self.company_id.id), ('id', 'in', self.account_ids.ids)])
            accounts = self.env['account.account'].search(
                [('id', 'in', accounts.ids), ('group_id.name', '!=', 'Salaries & Benefits'),
                 ('group_id.name', '!=', 'Raw Material')])
        else:
            accounts = self.env['account.account'].search(
                ['|', ('user_type_id.name', '=', 'Expenses'), ('user_type_id.name', '=', 'Cost of Revenue'),
                 ('company_id', '=', self.company_id.id)])
            accounts = self.env['account.account'].search(
                [('id', 'in', accounts.ids), ('group_id.name', '!=', 'Salaries & Benefits'),
                 ('group_id.name', '!=', 'Raw Material')])
        list_accounts_indirect_cost_expense = []
        debit_balance = 0
        credit_balance = 0
        balance = 0
        other_domain = [('analytic_account_id.analytic_type', '=', 'ser_cost_center')]
        if self.analytic_account_ids:
            other_domain += [('analytic_account_id.id', 'in', self.analytic_account_ids.ids)]
        if self.target_move == 'posted':
            other_domain += ['&', ('move_id.state', '=', 'posted')]
        if self.date_from or self.date_to:
            other_domain += [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        for rec in accounts:
            x = self._compute_account_balance(rec, other_domain)
            list_accounts_indirect_cost_expense.append([rec.name, rec.code, x])
            if x[0][2]:
                debit_balance += x[0][0]
                credit_balance += x[0][1]
                balance += x[0][2]
        total_indirect_cost_expense = balance
        total_direct_cost = total_direct_cost_wage + total_direct_cost_expense + total_direct_material
        total_indirect_cost = total_indirect_cost_wage + total_indirect_cost_expense
        total_cogs = total_direct_cost + total_indirect_cost
        cogs_balance = [
            ['Direct Cost', total_direct_cost, 1, 0],
            ['Direct Material', total_direct_material, 0, list_accounts_direct_material],
            ['Direct Expenses', total_direct_cost_expense, 0, list_accounts_direct_cost_expense]
            , ['Direct wages ', total_direct_cost_wage, 0, list_accounts_direct_cost_wage],
            ['Indirect Cost', total_indirect_cost, 1, 0],
            ['Indirect Expenses', total_indirect_cost_expense, 0, list_accounts_indirect_cost_expense],
            ['Indirect wages', total_indirect_cost_wage, 0, list_accounts_indirect_cost_wage],
        ]
        ################################

        ###################################### Administrative Expenses
        ############################### Wage Expenses
        if self.account_ids:
            accounts = self.env['account.account'].search(
                ['|', ('user_type_id.name', '=', 'Expenses'), ('user_type_id.name', '=', 'Cost of Revenue'),
                 ('company_id', '=', self.company_id.id), ('id', 'in', self.account_ids.ids)])
            accounts = self.env['account.account'].search(
                [('group_id.name', '=', 'Salaries & Benefits'), ('id', 'in', accounts.ids)])
        else:
            accounts = self.env['account.account'].search(
                ['|', ('user_type_id.name', '=', 'Expenses'), ('user_type_id.name', '=', 'Cost of Revenue'),
                 ('company_id', '=', self.company_id.id)])
            accounts = self.env['account.account'].search(
                [('group_id.name', '=', 'Salaries & Benefits'), ('id', 'in', accounts.ids)])
        debit_balance = 0
        credit_balance = 0
        balance = 0
        list_accounts_wage_expenses = []
        other_domain = [('analytic_account_id.analytic_type', '!=', 'admin_cost_center'),('analytic_account_id.analytic_type', '!=', 'ser_cost_center')]
        if self.analytic_account_ids:
            other_domain += [('analytic_account_id.id', 'in', self.analytic_account_ids.ids)]
        if self.target_move == 'posted':
            other_domain += ['&', ('move_id.state', '=', 'posted')]
        if self.date_from or self.date_to:
            other_domain += [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        for rec in accounts:
            x = self._compute_account_balance(rec, other_domain)
            list_accounts_wage_expenses.append([rec.name, rec.code, x])
            if x[0][2]:
                debit_balance += x[0][0]
                credit_balance += x[0][1]
                balance += x[0][2]
        total_wage_expense = balance
        ###################################### Administrative Expenses
        ############################### Other Expenses
        if self.account_ids:
            accounts = self.env['account.account'].search(
                ['|', ('user_type_id.name', '=', 'Expenses'), ('user_type_id.name', '=', 'Cost of Revenue'),
                 ('company_id', '=', self.company_id.id), ('id', 'in', self.account_ids.ids)])
            accounts = self.env['account.account'].search(
                [('group_id.name', '!=', 'Salaries & Benefits'), ('id', 'in', accounts.ids)])
        else:
            accounts = self.env['account.account'].search(
                ['|', ('user_type_id.name', '=', 'Expenses'), ('user_type_id.name', '=', 'Cost of Revenue'),
                 ('company_id', '=', self.company_id.id)])
            accounts = self.env['account.account'].search(
                [('group_id.name', '!=', 'Salaries & Benefits'), ('id', 'in', accounts.ids)])
        debit_balance = 0
        credit_balance = 0
        balance = 0
        list_accounts_others_expenses = []
        other_domain = [('analytic_account_id.analytic_type', '=', 'admin_cost_center')]
        if self.analytic_account_ids:
            other_domain += [('analytic_account_id.id', 'in', self.analytic_account_ids.ids)]
        if self.target_move == 'posted':
            other_domain += ['&', ('move_id.state', '=', 'posted')]
        if self.date_from or self.date_to:
            other_domain += [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        for rec in accounts:
            x = self._compute_account_balance(rec, other_domain)
            list_accounts_others_expenses.append([rec.name, rec.code, x])
            if x[0][2]:
                debit_balance += x[0][0]
                credit_balance += x[0][1]
                balance += x[0][2]
        total_other_expense = balance
        expense_balance = [
            ['Wage Expenses', total_wage_expense, 1, list_accounts_wage_expenses],
            ['Others Expenses', total_other_expense, 1, list_accounts_others_expenses],
        ]
        ################################################### Totals
        total_net_sale = total_income - total_government_deductions
        gross_profit_loss = abs(total_cogs) - abs(total_net_sale)
        total_expense = total_wage_expense + total_other_expense
        net_profit_loss_before_tax = total_expense - (-gross_profit_loss)
        tax_profit_15 = net_profit_loss_before_tax * 0.15
        net_profit_loss_after_tax = (net_profit_loss_before_tax - tax_profit_15)

        net_profit = (net_profit_loss_before_tax - tax_profit_15) + (-total_other_income)
        balance = [
            ['Gross Sales from Operation', total_income, 1, list_accounts_total_income],
            ['Government Deductions', total_government_deductions, 1, list_accounts_government_deductions],
            ['Net Sale', abs(total_net_sale), 1, 0],
            ['Less: Cost of goods sold', total_cogs, 1, 0, cogs_balance],
            ['Gross Profit / loss', abs(gross_profit_loss), 1, 0],
            ['General Expenses', total_expense, 1, 0, expense_balance],
            ['Net Profit from Operation before Tax', abs(net_profit_loss_before_tax), 1, 0],
            ['Less: Tax Provision 15%', abs(tax_profit_15), 1, 0],
            ['Other Income', abs(total_other_income), 1, list_accounts_other_income],
            ['Net Profit', abs(net_profit), 1, 0]]
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'analytic_account_ids': self.analytic_account_ids,
                'balance': balance,
                'target_move': self.target_move,
                'with_details': self.with_details,
                'debit_balance': debit_balance,
                'credit_balance': credit_balance,
            },
        }
        return self.env.ref('acc_workflow.report_pl_custom_report').report_action(self, data=data)


class ProfitLossCustomReport(models.AbstractModel):
    _name = 'report.acc_workflow.pl_custom_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']
        analytic_account_ids = data['form']['analytic_account_ids']
        target_move = data['form']['target_move']
        with_details = data['form']['with_details']
        debit_balance = data['form']['debit_balance']
        credit_balance = data['form']['credit_balance']
        balance = data['form']['balance']
        report_data = {
            'date_from': date_from,
            'date_to': date_to,
            'analytic_account_ids': analytic_account_ids,
            'balance': balance,
            'with_details': with_details,
            'debit_balance': debit_balance,
            'credit_balance': credit_balance,
        }
        return {
            'doc_ids': docids,
            'doc_model': 'profit.loss.custom',
            'data': data['form'],
            'docs': self.env['profit.loss.custom'].browse(docids),
            'report_data': report_data,
        }
