# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError
import itertools
import psycopg2


class CrossoveredBudget(models.Model):
    _inherit = 'crossovered.budget'

    department_form_count = fields.Integer(compute='_compute_department_form_count')

    state = fields.Selection(selection_add=[
        ('fin_approve', 'Finance Manager Approval'),
        ('dir_approve', 'Finance Director Approval'),
        ('ceo_approve', 'CEO Approval'),
        ('validate',),
    ], ondelete={'fin_approve': 'set default', 'dir_approve': 'set default', 'ceo_approve': 'set default'})


    def action_submit_for_approval(self):
        for rec in self:
            rec.write({'state': 'fin_approve'})

    def action_finance_approve(self):
        for rec in self:
            rec.write({'state': 'dir_approve'})

    def action_director_approve(self):
        for rec in self:
            rec.write({'state': 'ceo_approve'})

    def action_ceo_approve(self):
        for rec in self:
            rec.action_budget_confirm()
            forms = self.env['budget.department.form'].search([
                ('budget_id', '=', rec.id),
                ('state', '=', 'ceo_approve')
            ])
            if forms:
                forms.write({'state': 'confirmed'})


    def write(self, vals):
        """تحديث حالة استمارات الأقسام عند تغيير حالة الموازنة الرئيسية"""
        res = super(CrossoveredBudget, self).write(vals)

        if 'state' in vals:
            new_state = vals['state']

            # تحديد الحالة المقابلة في استمارة القسم
            target_form_state = False
            if new_state == 'done':
                target_form_state = 'done'
            elif new_state == 'fin_approve':
                target_form_state = 'fin_approve'
            elif new_state == 'dir_approve':
                target_form_state = 'dir_approve'
            elif new_state == 'ceo_approve':
                target_form_state = 'ceo_approve'
            elif new_state == 'confirmed':
                target_form_state = 'confirmed'
            elif new_state == 'cancel':
                target_form_state = 'cancel'


            if target_form_state:
                for budget in self:
                    forms = self.env['budget.department.form'].search([
                        ('budget_id', '=', budget.id)
                    ])
                    if forms:
                        forms.write({'state': target_form_state})
        return res

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def _compute_department_form_count(self):
        for budget in self:
            budget.department_form_count = self.env['budget.department.form'].search_count([
                ('budget_id', '=', budget.id)
            ])

    def action_view_department_forms(self):
        """دالة تفتح قائمة الاستمارات المرتبطة بهذه الموازنة فقط"""
        self.ensure_one()
        return {
            'name': _('Department Budget Forms'),
            'type': 'ir.actions.act_window',
            'res_model': 'budget.department.form',
            'view_mode': 'tree,form',
            'domain': [('budget_id', '=', self.id)],
            'context': {'default_budget_id': self.id},
            'target': 'current',
        }


    def action_fill_budget_lines_from_departments(self):
        BudgetLine = self.env['crossovered.budget.lines']

        for budget in self:
            confirmed_forms = self.env['budget.department.form'].search([
                ('budget_id', '=', budget.id),
                ('state', 'in', ['approve', 'fin_approve', 'dir_approve', 'ceo_approve', 'confirmed'])
            ])

            for form in confirmed_forms:
                for f_line in form.line_ids:
                    # تجاهل السطور الصفرية في الميزانية الرئيسية فقط
                    if form.budget_type == 'main' and f_line.planned_amount == 0:
                        continue

                    dept_id = form.department_id.id
                    post_id = f_line.general_budget_id.id
                    analytic_id = f_line.analytic_account_id.id or False
                    date_from = f_line.start_from or budget.date_from
                    date_to = f_line.end_to or budget.date_to

                    custom_amount = f_line.planned_amount

                    standard_amount = custom_amount
                    if budget.custom_currency_id and budget.custom_currency_id != budget.company_id.currency_id:
                        standard_amount = budget.custom_currency_id._convert(
                            custom_amount,
                            budget.company_id.currency_id,
                            budget.company_id,
                            date_from or fields.Date.today()
                        )

                    domain = [
                        ('crossovered_budget_id', '=', budget.id),
                        ('general_budget_id', '=', post_id),
                        ('department_id', '=', dept_id),
                        ('analytic_account_id', '=', analytic_id),
                    ]

                    existing_line = BudgetLine.search(domain, limit=1)

                    # ======================
                    # MAIN BUDGET (إنشاء أو تحديث الموازنة الأصلية)
                    # ======================
                    if form.budget_type == 'main':
                        vals = {
                            'planned_amount': standard_amount,
                            'custom_planned_amount': custom_amount,
                        }
                        if existing_line:
                            existing_line.write(vals)
                        else:
                            vals.update({
                                'crossovered_budget_id': budget.id,
                                'name': f"{form.department_id.name} - {f_line.general_budget_id.name}",
                                'general_budget_id': post_id,
                                'analytic_account_id': analytic_id,
                                'department_id': dept_id,
                                'date_from': date_from,
                                'date_to': date_to,
                                'company_id': budget.company_id.id,
                            })
                            BudgetLine.create(vals)

                    # ======================
                    # AMENDMENT (تعديل بالزيادة أو النقص)
                    # ======================
                    elif form.budget_type == 'amendment':
                        if not existing_line:
                            raise UserError(
                                _("No base budget line found to amend for %s") % f_line.general_budget_id.name)

                        existing_line.write({
                            'planned_amount': existing_line.planned_amount + standard_amount,
                            'amendment_amount': existing_line.amendment_amount + standard_amount,
                            'amendment_amount_custom': existing_line.amendment_amount_custom + custom_amount,
                            'custom_planned_amount': existing_line.custom_planned_amount + custom_amount,
                        })

                    # ======================
                    # TRANSFER (تحويل بين الحسابات)
                    # ======================
                    elif form.budget_type == 'transfer':
                        if not existing_line:
                            raise UserError(
                                _("Cannot transfer from/to a budget line that does not exist:\n%s") % f_line.general_budget_id.display_name)

                        # تحديث المبالغ (سواء كانت سالبة للمحول منه أو موجبة للمحول إليه)
                        existing_line.write({
                            'planned_amount': existing_line.planned_amount + standard_amount,
                            'amendment_amount': existing_line.amendment_amount + standard_amount,
                            'amendment_amount_custom': existing_line.amendment_amount_custom + custom_amount,
                            'custom_planned_amount': existing_line.custom_planned_amount + custom_amount,
                        })

        return True

    def action_create_budgt_forms(self, specific_dept_id=False):
        FormObj = self.env['budget.department.form'].sudo()
        FormLineObj = self.env['budget.department.form.line'].sudo()
        BudgetDeptConfig = self.env['budget.department']

        for budget in self:
            domain = []
            if specific_dept_id:
                domain = [('department_id', '=', specific_dept_id)]

            all_dept_configs = BudgetDeptConfig.search(domain)

            for dept_conf in all_dept_configs:
                existing_form = FormObj.search([
                    ('budget_id', '=', budget.id),
                    ('department_id', '=', dept_conf.department_id.id)
                ], limit=1)

                if not existing_form:
                    form = FormObj.create({
                        'name': f"Budget - {dept_conf.department_id.name} ({budget.name})",
                        'budget_id': budget.id,
                        'department_id': dept_conf.department_id.id,
                        'manager_id': dept_conf.respons_user.id,
                        'date_from': budget.date_from,
                        'date_to': budget.date_to,
                        'currency_id': budget.custom_currency_id.id,
                        'budget_type': 'main',
                        'company_id': budget.company_id.id,
                    })

                    for post in dept_conf.general_budget_id:
                        for analytic in dept_conf.analytic_account_id:
                            FormLineObj.create({
                                'form_id': form.id,
                                'general_budget_id': post.id,
                                'analytic_account_id': analytic.id,
                                'planned_amount': 0.0,
                                'start_from': budget.date_from,
                                'end_to': budget.date_to,
                            })
                else:
                    if existing_form.state == 'draft':
                        if not existing_form.company_id:
                            existing_form.write({'company_id': budget.company_id.id})

                        for post in dept_conf.general_budget_id:
                            for analytic in dept_conf.analytic_account_id:
                                line_exists = FormLineObj.search([
                                    ('form_id', '=', existing_form.id),
                                    ('general_budget_id', '=', post.id),
                                    ('analytic_account_id', '=', analytic.id)
                                ], limit=1)

                                if not line_exists:
                                    FormLineObj.create({
                                        'form_id': existing_form.id,
                                        'general_budget_id': post.id,
                                        'analytic_account_id': analytic.id,
                                        'planned_amount': 0.0,
                                        'start_from': existing_form.date_from,
                                        'end_to': existing_form.date_to,
                                    })
        return True

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")

        return super(CrossoveredBudget, self).unlink()


    @api.depends('name', 'department_id', 'date_from', 'date_to')
    def compute_display_name(self):
        for record in self:
            display_name = record.name or ""

            if record.department_id:
                display_name += " - " + record.department_id.name

            if record.date_from and record.date_to:
                display_name += f" ({record.date_from} - {record.date_to})"

            record.display_name = display_name



class CrossoveredBudgetLines(models.Model):
    _inherit = 'crossovered.budget.lines'

    department_id = fields.Many2one('hr.department', string="Department")
    amendment_amount = fields.Float(string="Amending/Transfer Amount", help="Amending/Transfer Amount")
    amendment_amount_custom = fields.Float(string="Amending/Transfer Amount(Other currency)", help="Amending/Transfer Amount")