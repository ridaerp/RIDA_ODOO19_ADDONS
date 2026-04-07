import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class BudgetTransferWizard(models.TransientModel):
    _name = 'budget.transfer.wizard'
    _description = 'Budget Transfer between lines'

    request_id = fields.Many2one('material.request', readonly=True)
    source_master_line_id = fields.Many2one('crossovered.budget.lines', string="Source Budget Line", required=True
                                           , domain="[('planned_amount','!=',0)]")
    department_id = fields.Many2one('hr.department', string="Department")
    dest_budget_post_id = fields.Many2one('account.budget.post', string="Destination Budget Post", readonly=True)
    transfer_amount = fields.Float(string="Amount to Transfer", required=True)
    available_amount = fields.Float(
        string="Available in Source",
        compute="_compute_available_amount",
        readonly=True
    )
    source_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string="Source Analytic Account",
        readonly=True
    )

    dest_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string="Destination Analytic Account",
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Budget Currency",
        compute="_compute_currency"
    )

    @api.depends('source_master_line_id')
    def _compute_currency(self):
        for rec in self:
            rec.currency_id = rec.source_master_line_id.crossovered_budget_id.custom_currency_id or rec.env.company.currency_id

    @api.onchange('source_master_line_id')
    def _onchange_source_master_line_id(self):
        for rec in self:
            if rec.source_master_line_id:
                rec.source_analytic_account_id = rec.source_master_line_id.analytic_account_id
            else:
                rec.source_analytic_account_id = False

    @api.onchange('request_id')
    def _onchange_request_id(self):
        for rec in self:
            if rec.request_id:
                rec.dest_analytic_account_id = rec.request_id.analytic_account_id
            else:
                rec.dest_analytic_account_id = False

    # @api.depends('source_master_line_id')
    # def _compute_available_amount(self):
    #     for rec in self:
    #         if rec.source_master_line_id:
    #             planned = abs(rec.source_master_line_id.planned_amount)
    #             practical = abs(rec.source_master_line_id.practical_amount)
    #             rec.available_amount = planned - practical
    #         else:
    #             rec.available_amount = 0.0
    @api.depends('source_master_line_id', 'currency_id')
    def _compute_available_amount(self):
        for rec in self:
            if rec.source_master_line_id:
                # الحساب الأساسي بعملة الشركة (كما هو مخزن في أودو)
                planned = abs(rec.source_master_line_id.planned_amount)
                practical = abs(rec.source_master_line_id.practical_amount)
                company_amount = planned - practical

                # التحويل إلى عملة الموازنة المخصصة
                if rec.currency_id and rec.currency_id != rec.env.company.currency_id:
                    rec.available_amount = rec.env.company.currency_id._convert(
                        company_amount,
                        rec.currency_id,
                        rec.env.company,
                        fields.Date.today()
                    )
                else:
                    rec.available_amount = company_amount
            else:
                rec.available_amount = 0.0

    def action_confirm_transfer(self):
        self.ensure_one()

        if self.transfer_amount <= 0:
            raise UserError(_("Transfer amount must be greater than zero."))

        if self.transfer_amount > self.available_amount:
            raise UserError(_("Invalid transfer amount. Not enough available budget."))

        if not self.dest_budget_post_id:
            raise UserError(_("Please select a destination budget post."))

        # if self.source_master_line_id.general_budget_id.id == self.dest_budget_post_id.id:
        #     raise UserError(_("Source and destination budget posts must be different."))

        master_budget = self.source_master_line_id.crossovered_budget_id
        if not self.source_analytic_account_id or not self.dest_analytic_account_id:
            raise UserError(_("Analytic accounts must be defined."))

        source_analytic_id = self.source_analytic_account_id.id
        dest_analytic_id = self.dest_analytic_account_id.id

        # إنشاء استمارة تحويل
        dept_form = self.env['budget.department.form'].create({
            'name': f"Transfer for {self.request_id.department_id.name}",
            'budget_id': master_budget.id,
            'department_id': self.request_id.department_id.id,
            'date_from': master_budget.date_from,
            'date_to': master_budget.date_to,
            'currency_id': master_budget.custom_currency_id.id,
            'budget_type': 'transfer',  # ✅ مهم جدًا
            'state': 'draft',
        })

        # 1️⃣ سطر الخصم (SOURCE → موجب)
        # سطر الخصم (من المصدر)
        self.env['budget.department.form.line'].create({
            'form_id': dept_form.id,
            'general_budget_id': self.source_master_line_id.general_budget_id.id,
            'analytic_account_id': self.source_master_line_id.analytic_account_id.id,
            'planned_amount': self.transfer_amount,  # موجب = خصم
            'start_from': master_budget.date_from,
            'end_to': master_budget.date_to,
        })

        # سطر الإضافة (إلى الوجهة)
        self.env['budget.department.form.line'].create({
            'form_id': dept_form.id,
            'general_budget_id': self.dest_budget_post_id.id,
            'analytic_account_id': self.request_id.analytic_account_id.id,  # الوجهة
            'planned_amount': -self.transfer_amount,  # سالب = زيادة
            'start_from': master_budget.date_from,
            'end_to': master_budget.date_to,
        })

        return {
            'name': _('Department Budget Transfer'),
            'type': 'ir.actions.act_window',
            'res_model': 'budget.department.form',
            'res_id': dept_form.id,
            'view_mode': 'form',
            'target': 'current',
        }

