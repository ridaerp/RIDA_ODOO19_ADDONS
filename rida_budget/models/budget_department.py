# -*- coding: utf-8 -*-

from odoo import models, fields, api,tools, _

class HrDepartment(models.Model):
    _name = 'budget.department'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'department_id'

    analytic_account_id = fields.Many2many('account.analytic.account', string="Analytic Account", tracking=True)
    # general_budget_id = fields.Many2many('account.budget.post', string="Budgetary Positions", tracking=True)
    account_account_ids = fields.Many2many('account.account', string="Accounts", tracking=True)
    respons_user = fields.Many2one('res.users', string="Responsible Budget", tracking=True)
    department_id = fields.Many2one('hr.department', string="Department", tracking=True)
    budget_id = fields.Many2one('budget.analytic')
    company_id = fields.Many2one('res.company', string='Company')

    def write(self, vals):
        res = super(HrDepartment, self).write(vals)
        self._sync_active_forms()
        return res

    def _sync_active_forms(self):
        """تحديث تلقائي لأي استمارة موازنة مرتبطة بهذا القسم لا تزال مسودة"""
        for record in self:
            open_budgets = self.env['budget.analytic'].search([('state', '=', 'draft')])
            if open_budgets:
                open_budgets.action_create_budgt_forms()