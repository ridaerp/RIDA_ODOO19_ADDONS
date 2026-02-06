from odoo import api, fields, models, tools


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    id_expiry_date = fields.Date(readonly=True)
    passport_expiry_date = fields.Date(readonly=True)
    age = fields.Integer(readonly=True)