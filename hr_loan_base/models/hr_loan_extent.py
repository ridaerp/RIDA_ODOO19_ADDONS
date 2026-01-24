from odoo import api, fields, models


class Loan(models.Model):
    _inherit = 'hr.loan'

    start_date = fields.Date(string='Contract Start Date', related="employee_id.contract_id.date_start")
    expiry_date = fields.Date(string='Contract Expiry Date', related="employee_id.contract_id.date_end")
