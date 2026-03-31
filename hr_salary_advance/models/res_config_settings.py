from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_hr_salary_advance_accounting = fields.Boolean(string="Advance Salary with Accounting")
