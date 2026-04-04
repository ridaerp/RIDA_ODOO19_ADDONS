# -*- coding: utf-8 -*-
from odoo import models, fields, tools


class BudgetPivotReport(models.Model):
    _name = 'budget.pivot.report'
    _description = 'Budget Pivot Report'
    _auto = False  # مهم جدا (SQL VIEW)

    # =========================
    # Fields
    # =========================
    budget_id = fields.Many2one('budget.analytic', string="Budget", readonly=True)
    department_id = fields.Many2one('hr.department', string="Department", readonly=True)
    account_id = fields.Many2one('account.account', string="Account", readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", readonly=True)

    date_from = fields.Date(string="Date From", readonly=True)
    date_to = fields.Date(string="Date To", readonly=True)

    # Measures
    budget_amount = fields.Float(string="Budget Amount", readonly=True)
    achieved_amount = fields.Float(string="Achieved", readonly=True)
    committed_amount = fields.Float(string="Committed", readonly=True)
    amendment_amount = fields.Float(string="Amendment", readonly=True)

    # =========================
    # SQL VIEW
    # =========================
    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH achieved_summary AS (
                    -- تجميع الحركات المحاسبية مسبقاً
                    SELECT 
                        account_id, 
                        date,
                        SUM(balance) as total_balance
                    FROM account_move_line
                    GROUP BY account_id, date
                ),
                committed_summary AS (
                    -- تجميع الالتزامات من المشتريات مسبقاً
                    -- ملاحظة: التعامل مع analytic_distribution كـ text يتطلب حذراً
                    SELECT 
                        key as analytic_account_id,
                        SUM(price_subtotal) as total_committed
                    FROM purchase_order_line,
                         jsonb_each_text(analytic_distribution) -- الطريقة الحديثة لفك التوزيع التحليلي في Odoo
                    GROUP BY key
                )

                SELECT
                    bl.id AS id,
                    bl.budget_analytic_id AS budget_id,
                    bl.department_id,
                    bl.account_account_id AS account_id,
                    bl.account_id AS analytic_account_id,
                    bl.date_from,
                    bl.date_to,
                    bl.budget_amount,
                    bl.amendment_amount,
                    COALESCE(ach.total_balance, 0) AS achieved_amount,
                    COALESCE(com.total_committed, 0) AS committed_amount

                FROM budget_line bl
                LEFT JOIN achieved_summary ach ON (
                    ach.account_id = bl.account_account_id
                    AND ach.date BETWEEN bl.date_from AND bl.date_to
                )
                LEFT JOIN committed_summary com ON (
                    com.analytic_account_id = bl.account_id::text
                )
            )
        """ % self._table)