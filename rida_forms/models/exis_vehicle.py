# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class ExitVehicle(models.Model):
    _name = 'exit.vehicle'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Reference', readonly=True, default=lambda self: 'NEW')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('security_approve', 'Under Supervision'),
         ('reject', 'Rejected'),
         ('approved', 'Closed/Done')],
        string='Status', default='draft', tracking=True)

    drive_name = fields.Char(string="Driver Name", tracking=True)
    vehicle_num = fields.Char(string="Vehicle Number", tracking=True)
    destination = fields.Char(string="Destination", tracking=True)
    reason_for_exit = fields.Text(string="Purpose", tracking=True)
    items = fields.Text(string="Items transported", tracking=True)

    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True)

    department_id = fields.Many2one('hr.department', string="Department", compute='_compute_department', store=True)

    date = fields.Date(default=fields.Date.context_today, string='Request Date')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    reason_reject = fields.Text(string='Reject Reason', tracking=True)

    @api.depends('req_id')
    def _compute_department(self):
        for rec in self:
            if rec.req_id:
                employee = self.env['hr.employee'].sudo().search([('user_id', '=', rec.req_id.id)], limit=1)
                rec.department_id = employee.department_id.id if employee else False
            else:
                rec.department_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'NEW') == 'NEW':
                vals['name'] = self.env['ir.sequence'].next_by_code('exit.vehicle') or 'NEW'
        return super(ExitVehicle, self).create(vals_list)

    def action_submit(self):
        self.state = 'security_approve'

    def action_approve_by_security(self):
        for rec in self:
            rec.state = 'approved'

    def action_draft(self):
        for rec in self:
            rec.state = "draft"