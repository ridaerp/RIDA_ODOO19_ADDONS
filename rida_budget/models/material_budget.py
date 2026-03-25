# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class MaterialRequest(models.Model):
    _inherit = "material.request"

    has_budget_overrun = fields.Boolean(compute="_compute_has_budget_overrun")
    has_reject = fields.Boolean(string='Has Been Reject', default=False)
    state = fields.Selection(
        selection_add=[('cost_control', 'Waiting Cost Control Approval')],
        ondelete={'cost_control': 'set default'}
    )


    def button_to_transfer(self):
        self.ensure_one()

        failed_line = self.line_ids.filtered(lambda l: l.budget_remaining < (l.product_qty * l.unit_price))[:1]

        if not failed_line:
            raise UserError(_("No budget overrun detected. You don't need a transfer."))

        return {
            'name': _('Budget Transfer Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'budget.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_dest_budget_post_id': failed_line.budget_post_id.id,
                'default_department_id': self.department_id.id,
                'default_budget_type': 'transfer',
            }
        }

    def button_to_amendment(self):
        self.ensure_one()
        today = fields.Date.today()
        master_budget = self.env['crossovered.budget'].search([
            ('date_from', '<=', self.date_start),
            ('date_to', '>=', self.date_start),
            ('state', '=', 'validate')
        ], limit=1)

        if not master_budget:
            raise UserError(_("There is no approved Master Budget for the current period."))

        dept_form = self.env['budget.department.form'].search([
            ('budget_id', '=', master_budget.id),
            ('department_id', '=', self.department_id.id),
            ('state', '=', 'draft')
        ], limit=1)

        if not dept_form:
            dept_form = self.env['budget.department.form'].create({
                'name': f"Budget Amendment for {self.department_id.name}",
                'budget_id': master_budget.id,
                'currency_id': master_budget.custom_currency_id.id,
                'department_id': self.department_id.id,
                'date_from': master_budget.date_from,
                'date_to': master_budget.date_to,
                'manager_id': self.env.user.id,
                'budget_type': 'amendment',
            })

        failed_line = self.line_ids.filtered(lambda l: l.budget_remaining < (l.product_qty * l.unit_price))[:1]

        if failed_line:
            existing_line = dept_form.line_ids.filtered(
                lambda l: l.general_budget_id == failed_line.budget_post_id and \
                          l.analytic_account_id == self.analytic_account_id
            )
            if not existing_line:
                self.env['budget.department.form.line'].create({
                    'form_id': dept_form.id,
                    'general_budget_id': failed_line.budget_post_id.id,
                    'analytic_account_id': self.analytic_account_id.id,
                    'start_from': master_budget.date_from,
                    'end_to': master_budget.date_to,
                    'planned_amount': 0.0,
                })

        return {
            'name': _('Department Budget Amendment'),
            'type': 'ir.actions.act_window',
            'res_model': 'budget.department.form',
            'res_id': dept_form.id,
            'view_mode': 'form',
            'target': 'current',
        }


    @api.depends('line_ids.budget_remaining', 'line_ids.product_qty', 'line_ids.unit_price')
    def _compute_has_budget_overrun(self):
        for rec in self:
            overrun = False
            for line in rec.line_ids:
                current_cost = line.product_qty * line.unit_price
                if current_cost > line.budget_remaining:
                    overrun = True
                    break
            rec.has_budget_overrun = overrun


    @api.constrains('line_ids')
    def _check_lines_unit_price(self):
        for request in self:
            for line in request.line_ids:
                if line.unit_price <= 0:
                    raise ValidationError(
                        _("Line for (%s): Error, the Estimated Cost must be greater than zero!") % line.product_id.display_name
                    )

    def action_cost_control_reject(self):
        for rec in self:
            rec.has_reject = True
            rec.state = 'line_line_approve'

    def button_to_line_manager(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                rec.write({'approve_by': rec.env.user.id})
                pass

            else:
                rec.write({'approve_by': rec.env.user.id})
                self.ensure_one()
                line_managers = []
                today = fields.Date.today()
                line_manager = False
                try:
                    line_manager = self.requested_by.line_manager_id
                except:
                    line_manager = False
                if not line_manager or line_manager != rec.env.user:
                    raise UserError("Sorry. Your are not authorized to approve this document!")

                rec.write({'state': 'line_line_approve'})

    # cost center
    def action_send_to_cost_control(self):
        for rec in self:
            # تحديث من قام بالاعتماد
            rec.approve_by = self.env.user.id

            # إذا كان مدير نظام، يمر مباشرة
            if self.env.user.has_group('base.group_system'):
                rec.write({'state': 'cost_control'})
                continue

            # منطق الصلاحيات
            line_manager = rec.requested_by.line_manager_id
            line_line_manager = rec.requested_by.line_line_manager_id

            if not line_manager:
                raise UserError(_("No Line Manager assigned to the requester."))

            authorized_users = [line_manager.user_id.id]
            if line_line_manager:
                authorized_users.append(line_line_manager.user_id.id)

            if self.env.user.id not in authorized_users:
                raise UserError(
                    _("Sorry, you are not authorized to approve this document! Only %s or %s can approve.") %
                    (line_manager.name, line_line_manager.name if line_line_manager else 'N/A'))

            rec.write({'state': 'cost_control'})
        return True

    # manager to warehouse
    def button_to_warehouse_supervisor(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                rec.write({'approve_by': rec.env.user.id})
                pass

            else:
                rec.write({'approve_by': rec.env.user.id})
                self.ensure_one()
                line_managers = []
                today = fields.Date.today()
                line_manager = False
                line_line_manager = False
                try:
                    line_manager = self.requested_by.line_manager_id
                    line_line_manager = self.requested_by.line_line_manager_id
                except:
                    line_manager_id = False
                    line_line_manager_id = False
                    pass
            if rec.requested_by.user_type == 'site' and rec.item_type == 'service':
                return rec.write({'state': 'site_approve'})

            if rec.requested_by.user_type == 'fleet' and rec.item_type == 'service':
                return rec.write({'state': 'fleet_director_approve'})

            if rec.item_type == 'service':
                # return rec.write({'state': 'supply_approve'})
                return rec.write({'state': 'supply_service_approve'})

            if rec.requested_by.user_type == 'fleet' and rec.item_type == 'material':
                return rec.write({'state': 'warehouse_sup'})

            if rec.requested_by.user_type == 'site' and rec.item_type == 'material':
                return rec.write({'state': 'warehouse_sup'})

            else:
                return rec.write({'state': 'supply_approve'})


class MaterialRequestLine(models.Model):
    _inherit = "material.request.line"

    budget_planned = fields.Monetary(string="Planned Budget", compute="_compute_line_budget",
                                     currency_field='company_currency_id')
    budget_spent = fields.Monetary(string="Actual Spent", compute="_compute_line_budget",
                                   currency_field='company_currency_id')
    budget_reserved = fields.Monetary(string="Reserved (Other Requests)", compute="_compute_line_budget",
                                      currency_field='company_currency_id')
    budget_remaining = fields.Monetary(string="Available Budget", compute="_compute_line_budget",
                                       currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', related='request_id.company_id.currency_id')
    expense_account_id = fields.Many2one('account.account', string="Expense Account", compute="_compute_line_budget",
                                         store=False)
    budget_post_id = fields.Many2one('account.budget.post', string="Budget Post", compute="_compute_line_budget",
                                     store=False)

    @api.depends(
        'product_id',
        'product_qty',
        'unit_price',
        'budget_post_id',
        'request_id.analytic_account_id',
        'request_id.department_id',
        'request_id.date_start'
    )
    def _compute_line_budget(self):
        for line in self:
            line.budget_planned = 0.0
            line.budget_spent = 0.0
            line.budget_reserved = 0.0
            line.budget_remaining = 0.0
            line.expense_account_id = False
            line.budget_post_id = line.budget_post_id or False

            budget_post = line.budget_post_id
            expense_account = False

            if line.product_id:
                expense_account = (
                        line.product_id.property_account_expense_id
                        or line.product_id.categ_id.property_account_expense_categ_id
                )
                if expense_account:
                    line.expense_account_id = expense_account.id
                    if not budget_post:
                        budget_post = self.env['account.budget.post'].search([
                            ('account_ids', 'in', expense_account.ids)
                        ], limit=1)

            # إذا لم يوجد بند موازنة (لا يدوياً ولا من المنتج)، ننتقل للسطر التالي
            if not budget_post:
                continue

            line.budget_post_id = budget_post

            date = line.request_id.date_start or fields.Date.today()
            budget_domain = [
                ('general_budget_id', '=', budget_post.id),
                ('date_from', '<=', date),
                ('date_to', '>=', date),
                ('crossovered_budget_id.state', '=', 'validate'),
            ]

            # الفلترة بالحساب التحليلي والقسم (اختياري)
            if line.request_id.analytic_account_id:
                budget_domain.append(('analytic_account_id', '=', line.request_id.analytic_account_id.id))

            # ملاحظة: التحقق من وجود الحقل في الموديل لتجنب أخطاء النظام
            if hasattr(self.env['crossovered.budget.lines'], 'department_id') and line.request_id.department_id:
                budget_domain.append(('department_id', '=', line.request_id.department_id.id))

            budget_line = self.env['crossovered.budget.lines'].search(budget_domain, limit=1)

            if budget_line:
                currency = line.company_currency_id
                company = line.request_id.company_id
                planned = abs(budget_line.planned_amount)
                spent = abs(budget_line.practical_amount)

                if budget_line.company_id.currency_id != currency:
                    planned = budget_line.company_id.currency_id._convert(planned, currency, company, date)
                    spent = budget_line.company_id.currency_id._convert(spent, currency, company, date)

                line.budget_planned = planned
                line.budget_spent = spent

            # 4. حساب المبالغ المحجوزة (Reserved)
            reserved_domain = [
                ('budget_post_id', '=', budget_post.id),
                ('request_id.state', 'not in', ['draft', 'reject', 'cancel']),
            ]

            if line.request_id.analytic_account_id:
                reserved_domain.append(('request_id.analytic_account_id', '=', line.request_id.analytic_account_id.id))

            if line.request_id.department_id:
                reserved_domain.append(('request_id.department_id', '=', line.request_id.department_id.id))

            if line._origin.id:
                reserved_domain.append(('id', '!=', line._origin.id))

            other_lines = self.env['material.request.line'].search(reserved_domain)
            reserved_total = sum(ol.product_qty * ol.unit_price for ol in other_lines)

            line.budget_reserved = reserved_total
            line.budget_remaining = line.budget_planned - (line.budget_spent + line.budget_reserved)

