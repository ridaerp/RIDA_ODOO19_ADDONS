from odoo import _, api, fields, models

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    current_leave_id = fields.Many2one(
        'hr.leave.type',
        compute='_compute_current_leave',
        string="Current Time Off Type",
        groups="base.group_user"
    )

    last_attendance_id = fields.Many2one(
        'hr.attendance', compute='_compute_last_attendance_id', store=True,
        groups="base.group_user")