# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def _get_employees(self):
        return []