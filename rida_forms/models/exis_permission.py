# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date, timedelta, datetime
from odoo.exceptions import UserError, ValidationError


class ExitPermission(models.Model):
    _name = 'exit.permission'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('wlm_approve', 'Waiting Line Manager'),
         ('w_hr_off', 'Waiting HR Officer'),
         ('security_approve', 'Waiting Security Approval'),
         ('reject', 'reject'),
         ('approved', 'Approved')],
        string='Status', default='draft', tracking=True)

    exit_date = fields.Date(string="Exit Date", tracking=True, copy=False)
    exit_time = fields.Float(string="Exit Time", tracking=True, copy=False)
    return_date = fields.Date(string="Return Date", tracking=True, copy=False)
    return_time = fields.Float(string="Return Time", tracking=True, copy=False)
    destination = fields.Char(string="Destination", tracking=True)

    reason_for_exit = fields.Text(string="Reason for Exit", tracking=True)

    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True)
    date = fields.Datetime(default=fields.Datetime.now(), string='Request Date')
    department_id = fields.Many2one('hr.department', string="Department")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    employees_line_ids = fields.One2many(comodel_name="exit.permission.line", inverse_name="request_id",
                                         string="Employees", copy=1)
    employee_id = fields.Many2one('hr.employee', related='employees_line_ids.employee_id', string='Employees',
                                  readonly=False)
    approved_employees_ids = fields.Many2many(
        'hr.employee',
        string="Approved Exit Employees",
    )

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('exit.permission') or ' '

        return super(ExitPermission, self).create(vals)

    def action_submit(self):
        self.state = 'wlm_approve'

    def action_approve_by_manager(self):
        line_manager = False
        try:
            line_manager = self.req_id.line_manager_id
        except:
            line_manager = False
        if not line_manager or line_manager != self.env.user:
            raise UserError("Sorry. You are not authorized to approve this document!")

        self.state = 'w_hr_off'

    def action_approve_by_hr(self):
        self.state = 'security_approve'

    def action_approve_by_security(self):
        for rec in self:
            rec.state = 'approved'
            rec.approved_employees_ids = rec.employees_line_ids.mapped('employee_id')

    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(ExitPermission, self).unlink()


class ExitPermissionLine(models.Model):
    _name = 'exit.permission.line'
    _order = "create_date desc"

    request_id = fields.Many2one("exit.permission", string="Request")
    employee_id = fields.Many2one("hr.employee", string="Employee")
    job_id = fields.Many2one(comodel_name="hr.job", related='employee_id.job_id', string="Job Title")
