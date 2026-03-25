# -*- coding: utf-8 -*-

from odoo import models, fields, api,tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero
from datetime import date
import datetime

class BudgetDepartmentForm(models.Model):
    _name = 'budget.department.form'
    _description = 'Department Budget Entry Form'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default=lambda self: _('New'))
    budget_id = fields.Many2one('budget.analytic', string="Master Budget", readonly=True)
    department_id = fields.Many2one('hr.department', string="Department", readonly=True)
    manager_id = fields.Many2one('res.users', string="Responsible", readonly=True, tracking=True)
    date_from = fields.Date(string="Start Date", readonly=True, tracking=True)
    date_to = fields.Date(string="End Date", readonly=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Department Manager'),
        ('approve', 'Budget Officer'),
        ('fin_approve', 'Finance Manager approval'),
        ('dir_approve', 'Finance Director approval'),
        ('ceo_approve', 'CEO approval'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Canceled'),
    ], default='draft', string="Status", tracking=True)
    currency_id = fields.Many2one('res.currency',string="Currency", tracking=True,
                                  help="All amounts in the lines below should be entered in this currency.")
    line_ids = fields.One2many('budget.department.form.line', 'form_id', string="Budget Lines")
    budget_type = fields.Selection([
        ('main', 'Main Budget'),
        ('amendment', 'amendment Budget'),
        ('transfer', 'Transfer Budget'),
    ], default='main', string="Budget Type", tracking=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
    )

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")

        return super(BudgetDepartmentForm, self).unlink()


    def _send_notification_to_approvers(self, group_xml_id, message):
        group = self.env.ref(group_xml_id)
        users = group.user_ids

        for rec in self:
            for user in users:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    note=message,
                    summary=_("Budget Approval Required")
                )


    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_submit(self):
        for rec in self:
            rec.state = 'submit'
            line_manager = rec.manager_id.line_manager_id if rec.manager_id.line_manager_id else None
            if line_manager:
                message = "A new budget form  is waiting for your review"
                self.activity_schedule('master_data.mail_act_master_data_approval', user_id=line_manager.id, note=message)


    def action_approve(self):
        for rec in self:
            if not rec.department_id:
                raise UserError(_("Please define a department for this budget."))

            if self.env.user.has_group('base.group_system'):
                pass
            else:
                self.ensure_one()
                try:
                    line_manager = self.manager_id.line_manager_id
                except:
                    line_manager = False
                if not line_manager or line_manager != rec.env.user:
                    raise ValidationError(
                        _("Only the Manager of the parent department %s (%s) is authorized to approve this budget.") %
                        (rec.department_id.parent_id.name, line_manager.name))

            rec.state = 'approve'
            if rec.budget_type == 'amendment':
                rec._send_notification_to_approvers(
                    'base_rida.budget_costing_manager',
                    _("Budget %s has been approved by the Department Manager and needs your check.") % rec.name
                )
            else:
                pass

    def action_budget(self):
        for rec in self:
            zero_lines = rec.line_ids.filtered(
                lambda l: float_is_zero(l.planned_amount, precision_digits=rec.currency_id.decimal_places or 2)
            )
            zero_lines.unlink()

            if rec.budget_type == 'transfer':
                rec.write({'state': 'confirmed'})
                if rec.budget_id:
                    rec.budget_id.action_fill_budget_lines_from_departments()
            else:
                rec.state = 'fin_approve'
                rec.budget_id.action_fill_budget_lines_from_departments()
                rec._send_notification_to_approvers(
                    'base_rida.rida_finance_manager',
                    _("Budget %s is pending Finance Manager Approval.") % rec.name
                )

    def action_fin_approve(self):
        for rec in self:
            rec.state = 'dir_approve'
            rec._send_notification_to_approvers(
                'base_rida.group_finance_director',
                _("Budget %s Needs Finance Director Approval.") % rec.name
            )

    def action_dir_approve(self):
        for rec in self:
            rec.state = 'ceo_approve'
            rec._send_notification_to_approvers(
                'base_rida.rida_group_COO',
                _("Budget %s Needs CEO Approval.") % rec.name
            )

    def action_ceo_approve(self):
	    self.write({'state': 'confirmed'})
	    if self.budget_id:
	        self.budget_id.action_fill_budget_lines_from_departments()


class BudgetDepartmentFormLine(models.Model):
    _name = 'budget.department.form.line'
    _description = 'Department Budget Line'

    form_id = fields.Many2one('budget.department.form')
    # general_budget_id = fields.Many2one('account.budget.post', string="Budgetary Position")
    account_account_id = fields.Many2one('account.account', string="Account")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    planned_amount = fields.Float(string="Planned Amount", digits='Account')
    start_from = fields.Date(string="Start Date", tracking=True)
    end_to = fields.Date(string="End Date", tracking=True)

    practical_amount = fields.Float(string="Practical Amount", compute='_compute_amounts', digits='Account')
    theoretical_amount = fields.Float(string="Theoretical Amount", compute='_compute_amounts', digits='Account')
    percentage = fields.Float(string="Achievement", compute='_compute_amounts')
    amendment_amount = fields.Float(string="Amending/Transfer Amount", compute='_compute_amounts', digits='Account')

    custom_practical_amount = fields.Float(string="Practical Amount (Other Currency)", compute='_compute_amounts',
                                           digits='Account')
    custom_theoretical_amount = fields.Float(string="Theoretical Amount (Other Currency)", compute='_compute_amounts',
                                             digits='Account')
    amendment_amount_custom = fields.Float(string="Amending/Transfer Amount (Other Currency)",
                                           compute='_compute_amounts', digits='Account')

    @api.depends('form_id.budget_id', 'account_account_id', 'analytic_account_id', 'form_id.department_id')
    def _compute_amounts(self):
        for line in self:
            # البحث عن السطر المقابل
            domain = [
                ('budget_analytic_id', '=', line.form_id.budget_id.id),
                ('account_account_id', '=', line.account_account_id.id),
                ('department_id', '=', line.form_id.department_id.id),
            ]

            # استخدام .with_context(active_test=False) لتجنب بعض مشاكل الكاش
            master_line = self.env['budget.line'].sudo().search(domain, limit=1)

            if master_line:
                try:
                    # محاولة جلب القيم
                    line.practical_amount = master_line.achieved_amount
                    line.theoretical_amount = master_line.theoritical_amount
                except Exception:
                    # في حال استمر خطأ SQL، نضع قيمة صفرية مؤقتاً لتجنب توقف النظام
                    line.practical_amount = 0.0
                    line.theoretical_amount = 0.0

                line.percentage = master_line.percentage
                line.amendment_amount = master_line.amendment_amount
                line.custom_practical_amount = getattr(master_line, 'custom_practical_amount', 0.0)
                line.custom_theoretical_amount = getattr(master_line, 'custom_theoritical_amount', 0.0)
                line.amendment_amount_custom = getattr(master_line, 'amendment_amount_custom', 0.0)

            else:
                # في حال لم يتم العثور على سطر مطابق في الموازنة الرئيسية، نصفر القيم
                line.practical_amount = 0.0
                line.theoretical_amount = 0.0
                line.percentage = 0.0
                line.amendment_amount = 0.0
                line.custom_practical_amount = 0.0
                line.custom_theoretical_amount = 0.0
                line.amendment_amount_custom = 0.0
