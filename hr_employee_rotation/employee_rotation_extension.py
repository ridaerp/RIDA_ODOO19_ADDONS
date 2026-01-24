from odoo import fields , api , models , _

class hr_employee_extended(models.Model):
    _inherit = 'employee.rotation'

    analytic_account_id_related = fields.Many2one(comodel_name='account.analytic.account', string='Cost Center', related='employee_id.analytic_account_id',store=True)
    project_analytic_account_id_related = fields.Many2one(comodel_name='account.analytic.account', string='Analytic Account', related='employee_id.project_analytic_account_id')   
    contract_start_date_related = fields.Date(string='Contract Start Date', related='employee_id.contract_start_date',readonly=True,store=True)
    contract_end_date_related = fields.Date(string='Contract end Date', related='employee_id.contract_end_date',readonly=True,store=True)

