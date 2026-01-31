# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_o_employee_rotation_multicompany = fields.Boolean(string="Transfer Employee")
    module_o_employee_cost_center  = fields.Boolean(string='Cost Center')
    module_o_employee_restrict_access  = fields.Boolean(string='Employee Restrict Access')
    module_o_employee_documents_expiry  = fields.Boolean(string='Enable Employee Documents')
    module_o_employee_check_list = fields.Boolean(string='Enable Employee Checklist')
