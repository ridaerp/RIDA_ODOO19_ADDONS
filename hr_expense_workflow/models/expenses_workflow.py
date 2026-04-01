# -*- coding: utf-8 -*-
from email.policy import default

from odoo import models, fields, api, _
from odoo.tools import email_split, float_is_zero
from soupsieve import select
from odoo.exceptions import AccessError, UserError, ValidationError, RedirectWarning

class Expenses(models.Model):
    _inherit  = 'hr.expense'
    department_id=fields.Many2one(related="employee_id.department_id",string="Department")
    payment_mode=fields.Selection(default="own_account")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('lm', 'line manager Approval'),
        ('submitted', 'Submitted'), # أضف هذه القيمة لأنها موجودة في الصورة
        ('approved', 'Accountant Approval'),
        ('finance', 'Finance Manager Approval'),
        ('site', 'Operation Director Approval'),
        ('internal_audit', 'Internal Audit'),
        ('ccso', 'CCSO'),
        ('paid', 'Paid'), # أضف هذه القيمة لحل مشكلة KeyError
        ('posted','Posted'),
        ('in_payment', 'In Payment'), # موجودة أيضاً في الصورة
        ('refused', 'Refused') # موجودة أيضاً في الصورة
    ], string='Status', index=True, readonly=True, tracking=True, copy=False, default='draft', required=True, help='Expense Report State')
    employee_id = fields.Many2one('hr.employee', string="Employee", required=False)
    emp_type = fields.Selection(string='Employee Type', related='employee_id.rida_employee_type')
    user_type_ = fields.Selection(related="create_uid.user_type")

    department_id=fields.Many2one(related="employee_id.department_id",string="Department",    store=True,readonly=True)
    number=fields.Char("")

    # def action_approve_expense_sheets(self):
    #     self._check_can_approve()
    #     # self._validate_analytic_distribution()
    #     duplicates = self.expense_line_ids.duplicate_expense_ids.filtered(lambda exp: exp.state in {'approved', 'done'})
    #     if duplicates:
    #         action = self.env["ir.actions.act_window"]._for_xml_id('hr_expense.hr_expense_approve_duplicate_action')
    #         action['context'] = {'default_sheet_ids': self.ids, 'default_expense_ids': duplicates.ids}
    #         return action
    #     self._do_approve()

    # أضف هذا الحقل في كلاس ExpensesCustom
    is_editable = fields.Boolean(compute='_compute_is_editable')

    @api.depends('state')
    def _compute_is_editable(self):
        for expense in self:
            # السماح بالتعديل إذا كان في المسودة أو حالات الاعتماد الوسطى
            if expense.state in ['draft', 'submitted', 'lm', 'finance', 'internal_audit', 'site', 'ccso']:
                expense.is_editable = True
            else:
                # إذا كان قد دفع أو تم ترحيله يمنع التعديل إلا للمدير المالي
                expense.is_editable = self.env.user.has_group('account.group_account_manager')

    def action_approve_expense_sheets(self):
        for expense in self:
            # تحقق إذا كان يمكن الموافقة عليه (يمكنك كتابة custom logic هنا)
            # if expense.state != 'ccso':
            #     raise UserError("Cannot approve expense not in draft state")

            # الموافقة مباشرة على الـ expense
            expense.state = 'approved'

            # يمكن إضافة duplicate check لو لازال مطلوب
            duplicates = expense.duplicate_expense_ids.filtered(lambda exp: exp.state in {'approved', 'done'})
            if duplicates:
                action = self.env["ir.actions.act_window"]._for_xml_id('hr_expense.hr_expense_approve_duplicate_action')
                action['context'] = {'default_expense_ids': duplicates.ids}
                return action

#     ###############ekhlas code -odoo 17-journal entreus
    def _do_approve(self):
        # super(ExpensesWorkflow, self)._do_approve()
        sheets_to_approve = self.filtered(lambda s: s.state in {'submit', 'draft','ccso','site'})
        sheets_to_approve._check_can_create_move()
        # sheets_to_approve._do_create_moves()
        for sheet in sheets_to_approve:
            sheet.write({
                'approval_state': 'approve',
                'user_id': sheet.user_id.id or self.env.user.id,
                'approval_date': fields.Date.context_today(sheet),
            })
        # self.activity_update()

#     ###############ekhlas code -odoo 17-journal entreus

    def _check_can_create_move(self):
        pass

    def action_submit_sheet(self):
        if self.user_type_=='rohax':
            self.action_submit_expenses()
        else:
            self.write({'state': 'lm'})
            # self.activity_update()
        
    # lm manager buttons
    def action_approve_sheets(self):
        self.ensure_one()
        line_managers = []
        today = fields.Date.today()
        line_manager = False
        try:
            if self.employee_id.expense_manager_id:
                line_manager = self.employee_id.expense_manager_id
            else:
                line_manager =  self.employee_id.parent_id.user_id
        except:
            line_manager = False
        if not line_manager or line_manager !=self.env.user :
                raise UserError("Sorry. Your are not authorized to approve this document!")
        self.write({'state': 'finance'})
        # self.activity_update()
        
#     # finance buttons
    def action_finance_sheets(self):
        for rec in self:
           if rec.emp_type == 'site':
            # old code self.write({'state': 'site'})
            self.write({'state': 'internal_audit'})
            # self.activity_update()
           else:
            self.write({'state': 'internal_audit'})
            # self.activity_update()

#     # site manager buttons
    def action_site_manager_sheets(self):
        self.write({'state': 'approve'})
        # self.activity_update()

#     # internal audit buttons
    def action_internal_audit_sheets(self):
        for rec in self:
            if rec.emp_type == 'site':
                self.write({'state': 'site'})
            else:
                self.write({'state': 'ccso'})
        # self.activity_update()

#     # ccso buttons
    def action_ccso_sheets(self):
        self.write({'state': 'approve'})
        # self.activity_update()
    
class ExpensesCustom(models.Model):
    _inherit  = 'hr.expense'

    @api.model
    def _default_employee_id(self):
        return self.env.user.employee_id

    @api.model
    def _get_employee_id_domain(self):
        res = [('id', '=', 0)] # Nothing accepted by domain, by default
        # Check user groups and set domain accordingly
        if self.env.user.has_group('hr_expense.group_hr_expense_user') or self.env.user.has_group(
                'account.group_account_user'):
            res = []  # Accept everything
        elif self.env.user.has_group('hr_expense.group_hr_expense_team_approver') and self.env.user.employee_ids:
            # Logic when the user is a team approver
            res = []  # Accept all employees, or set specific logic if necessary
        elif self.env.user.employee_id:
            # Logic for users with a specific employee
            employee = self.env.user.employee_id
            res = [('id', '=', employee.id)]  # Optionally restrict to the current employee

        return res



    emp_type = fields.Selection(string='Employee Type', related='employee_id.rida_employee_type')
    employee_id = fields.Many2one('hr.employee', compute='_compute_employee_id', string="Employee",
        store=True, required=False, readonly=False, tracking=True,
        states={'approved': [('readonly', True)], 'done': [('readonly', True)]},
        default=_default_employee_id, domain=lambda self: self._get_employee_id_domain(), check_company=True)


    #######################oveeride function by ekhlas code  to make finance edit the account


    # @api.depends('employee_id')
    # def _compute_is_editable(self):
    #     is_account_manager = (
    #             self.env.user.has_group('account.group_account_user') or
    #             self.env.user.has_group('account.group_account_manager')
    #     )
    #
    #     for expense in self:
    #         if expense.state == 'draft' or (
    #                 expense and expense.state in ['draft', 'submit', 'finance', 'accountant']):
    #             expense.is_editable = True
    #         elif expense and expense.state == 'approve':
    #             expense.is_editable = is_account_manager
    #         else:
    #             expense.is_editable = False


    def write(self, vals):
        if 'state' in vals or 'approval_state' in vals:
            # Avoid user with write access on expense sheet in draft state to bypass the validation process
            valid_states = {'submit', None}
            if (
                not self.env.user.has_group('hr_expense.group_hr_expense_manager')
                and any(state == 'draft' for state in self.mapped('state'))
                and (vals.get('state') not in valid_states or vals.get('approval_state') not in valid_states)
            ):
                pass  # no action
            elif vals.get('state') == 'approve' or vals.get('approval_state') == 'approve':
                self._check_can_approve()
            elif vals.get('state') == 'cancel' or vals.get('approval_state') == 'cancel':
                self._check_can_refuse()
        return super(ExpensesCustom, self).write(vals)

    # Monkey patch the method
    # expense_sheet_custom.HrExpenseSheet.write = write