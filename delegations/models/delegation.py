# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    old_mang = fields.Many2one('hr.delegation')


class Delegation(models.Model):
    _name = "hr.delegation"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Delegation"
    _rec_name = "display_name"
    _order = "create_date desc"

    state = fields.Selection([
        ('draft', 'Draft'),
        ('department', 'Line Manager'),
        ('w_ict', 'Waiting ICT Verfiy'),
        ('confirm', 'Access Granted'),
        ('revoked', 'Access Revoked'),
    ], string='Status', required=True, default='draft', track_visibility='onchange')

    display_name = fields.Char(compute='compute_display_name', string="Name", store=False)
    employee_id = fields.Many2one('hr.employee', string='Delegation Of', required=True,
                                  default=lambda self: self.get_employee(), track_visibility='always')
    employee_grant_id = fields.Many2one('hr.employee', string="Delegated Employee", required=True,
                                        track_visibility='always')
    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.today(), track_visibility='always')
    date_to = fields.Date(string='End Date', required=True, track_visibility='always')
    date_revoke_after2_days = fields.Date(string='Date revoke after2 days',compute='_compute_revoke_Date')
    justification = fields.Text("Justificatoion")
    remarks = fields.Text("Remarks")
    requester_id = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
    hr_access = fields.Boolean("have hr access?", compute="compute_hr_access")

    groups_id = fields.Many2many('res.groups', relation="group_user", copy=False)
    old_dept_mang_ids = fields.Many2many(comodel_name="res.users", relation="dept_mang_ids_user_del", copy=False)
    old_time_mang_ids = fields.Many2many(comodel_name="hr.employee", relation="old_time_mang_ids_del", copy=False)
    old_expense_mang_ids = fields.Many2many(comodel_name="hr.employee", relation="old_expense_mang_ids_del", copy=False)
    is_manager = fields.Boolean(compute='check_manager')


    @api.depends('employee_id')
    def compute_display_name(self):
        for rec in self:
            display_name = ""
            if rec.employee_id and rec.employee_grant_id:
                display_name = str(rec.employee_id.name) + " -> " + str(rec.employee_grant_id.name)
            rec.display_name = display_name


    @api.depends('date_to')
    def _compute_revoke_Date(self):
        for rec in self:
            if rec.date_to:
                rec.date_revoke_after2_days = rec.date_to + timedelta(days=2)

    @api.model
    def create(self, values):
        for val in values:
            if val['employee_id']:
                emp_id = val['employee_id']
            emp_id = self.env['hr.employee'].sudo().search([('id', '=', emp_id)])
            if emp_id.user_id:
                res = super(Delegation, self).create(val)
                res._update_related_fields()
                if (
                        depart := self.env['res.users'].sudo().search([('line_manager_id', '=', emp_id.user_id.id)]).ids
                ):
                    old_dept_ids = [(6, 0, depart)]
                    res.write({'old_dept_mang_ids': old_dept_ids})
                emp_id_timeoff = self.env['hr.employee'].sudo().search([('leave_manager_id', '=', emp_id.user_id.id)]).ids
                if emp_id_timeoff:
                    old_dept_ids = [(6, 0, emp_id_timeoff)]
                    res.write({'old_time_mang_ids': old_dept_ids})
                old_expense_mang_ids_var = self.env['hr.employee'].sudo().search(
                    [('expense_manager_id', '=', emp_id.user_id.id)]).ids
                if old_expense_mang_ids_var:
                    old_dept_ids = [(6, 0, old_expense_mang_ids_var)]
                    res.write({'old_expense_mang_ids': old_dept_ids})
                return res

    @api.depends('employee_id')
    def check_manager(self):
        for rec in self:
            if rec.employee_id:
                rec.is_manager = False
                if rec.employee_id.sudo().user_id.sudo().line_manager_id.id == self.env.user.id:
                    rec.is_manager = True
                else:
                    rec.is_manager = False
            else:
                rec.is_manager = False

    def submit(self):
        for rec in self:
            rec.state = 'department'

    def submit_ict(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                pass
            else:
                self.ensure_one()
                try:
                    line_manager = self.employee_id.user_id.line_manager_id
                except:
                    line_manager = False
                # comment by ekhlas
                # if not line_manager or not self.user_has_groups('material_request.group_department_manager'):
                #     raise UserError("Sorry. Your are not authorized to approve this document!")
                if not line_manager or line_manager != rec.env.user:
                    raise UserError("Sorry. Your are not authorized to approve this document!")
        rec.state = 'w_ict'

    @api.depends('requester_id')
    def compute_hr_access(self):
        for rec in self:
            if rec.sudo().requester_id.sudo().has_group('hr.group_hr_manager'):
                rec.hr_access = True
            else:
                rec.hr_access = False

    def _update_related_fields(self):
        """Reusable method to update related fields based on employee_id and employee_grant_id."""
        for rec in self:
            # If employee_id is present
            if rec.employee_id:
                user_id = rec.employee_id.user_id
                if user_id:
                    # Update groups_id
                    groups = user_id.sudo().group_ids.ids
                    rec.groups_id = [(6, 0, groups)]

                    # Update old_dept_mang_ids
                    depart = self.env['res.users'].sudo().search([('line_manager_id', '=', user_id.id)]).ids
                    rec.old_dept_mang_ids = [(6, 0, depart)] if depart else []

                    # Update old_time_mang_ids
                    emp_id_timeoff = self.env['hr.employee'].sudo().search(
                        [('leave_manager_id', '=', user_id.id)]).ids
                    rec.old_time_mang_ids = [(6, 0, emp_id_timeoff)] if emp_id_timeoff else []

                    # Update old_expense_mang_ids
                    old_expense_mang_ids_var = self.env['hr.employee'].sudo().search(
                        [('expense_manager_id', '=', user_id.id)]).ids
                    rec.old_expense_mang_ids = [(6, 0, old_expense_mang_ids_var)] if old_expense_mang_ids_var else []

            # If employee_grant_id is present
            if rec.employee_grant_id:
                user_id = rec.employee_id.user_id
                grant_user_id = rec.employee_grant_id.user_id
                if user_id and grant_user_id:
                    all_groups = user_id.sudo().group_ids.ids
                    grant_employee_groups = grant_user_id.sudo().group_ids.ids
                    shared_groups = list(set(all_groups).intersection(grant_employee_groups))
                    new_groups = list(set(all_groups) - set(shared_groups))
                    rec.groups_id = [(6, 0, new_groups)]

    @api.onchange('employee_id', 'employee_grant_id')
    def onchange_employee_or_grant(self):
        """Calls _update_related_fields when employee_id or employee_grant_id changes."""
        self._update_related_fields()




    def get_employee(self):
        user = self.env.user
        is_admin = user.has_group('base.group_erp_manager')
        if not is_admin:
            employee_ids = self.env.user.employee_ids
            if employee_ids:
                return employee_ids[0].id
            raise UserError('Current user is not linked to an employee!')


    @api.onchange('employee_grant_id')
    def onchange_employee_grant_id(self):
        for rec in self:
            if not rec.employee_grant_id or not rec.employee_id:
                return
            user_id = rec.employee_id.user_id
            all_groups = user_id.sudo().group_ids.sudo().ids
            grant_employee_groups = rec.sudo().employee_grant_id.user_id.sudo().group_ids.ids
            shared_groups = [value for value in all_groups if value in grant_employee_groups]

            new_groups = list(set(all_groups) - set(shared_groups))

            rec.update({
                'groups_id': [(6, 0, new_groups)]
            })

            return {
                'domain': {'group_ids': [('id', 'in', new_groups)]}
            }

    @api.constrains('date_from', 'date_to')
    def check_dates(self):
        for rec in self:
            if rec.date_from > rec.date_to:
                raise ValidationError("End date should be after start date!")

            domain = [
                ('date_from', '<=', rec.date_to),
                ('date_to', '>', rec.date_from),
                ('employee_grant_id', '=', rec.employee_grant_id.id),
                ('state', 'not in', ['revoked']),
                ('id', '!=', rec.id)
            ]

            ndelegations = rec.search_count(domain)

            if ndelegations:
                raise UserError(
                    _('You can not have 2 delegations that overlaps on the same day for the same employee.'))

    @api.constrains('employee_id', 'employee_grant_id')
    def check_users(self):
        for rec in self:
            if not rec.employee_id.user_id or not rec.employee_grant_id.user_id:
                raise UserError('One of the selected employees is not linked to a user.'
                                ' \n Please contact system administrator.')
            if rec.employee_id == rec.employee_grant_id:
                raise UserError('Please choose a different employee!')

    def action_confirm(self):
        for rec in self:
            # Ensure employee_grant_id has a linked user
            if not rec.employee_grant_id.user_id:
                raise UserError(_(f"{rec.employee_grant_id.name} does not have a linked user."))

            # Ensure groups are available to grant
            if not rec.groups_id:
                raise UserError(_("No access groups to grant!"))

            # Validate the end date
            today = fields.Date.today()
            if today > rec.date_to:
                raise UserError(_("End date cannot be in the past."))

            # Update line managers for old department managers
            for dep in rec.old_dept_mang_ids:
                dep.sudo().write({'line_manager_id': rec.employee_grant_id.user_id.id})

            # Update leave managers for old time-off managers
            for emp in rec.old_time_mang_ids:
                emp.sudo().write({'leave_manager_id': rec.employee_grant_id.user_id.id})

            # Update expense managers for old expense managers
            for emp in rec.old_expense_mang_ids:
                emp.sudo().write({'expense_manager_id': rec.employee_grant_id.user_id.id})

            # Grant new groups to the delegated user
            rec.employee_grant_id.user_id.sudo().write({
                'group_ids': [(4, group_id) for group_id in rec.groups_id.ids]
            })

            # Change the state to 'confirm'
            rec.state = 'confirm'

    def action_cancel(self):
        for rec in self:
            # revoke access rec.employee_grant_id.user_id.id
            if rec.employee_id.user_id.id:
                for dep in rec.old_dept_mang_ids:
                    if rec.employee_id.user_id.id:
                        dep.line_manager_id = rec.employee_id.user_id.id
                for dep in rec.old_time_mang_ids:
                    if rec.employee_id.id:
                        dep.leave_manager_id = rec.employee_id.user_id.id
                for dep in rec.old_expense_mang_ids:
                    if rec.employee_id.id:
                        dep.expense_manager_id = rec.employee_id.user_id.id
                to_remove = [group for group in rec.groups_id.ids]
                groups = rec.sudo().employee_grant_id.user_id.group_ids.ids
                new_groups = list(set(groups) - set(to_remove))
                new_groups = self.env['res.groups'].search([('id', 'in', new_groups)])
                rec.sudo().employee_grant_id.user_id.group_ids = new_groups
                rec.state = 'revoked'
            else:
                raise UserError(_(f"{rec.employee_id} Dose Not Have User"))

    def action_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Only draft records can be deleted!")
        super(Delegation, self).unlink()

    @api.model
    def _cron_update_delegations(self):
        today = fields.Date.today()
        delegations = self.search(
            ['|', '&', ('date_from', '<=', today), ('date_to', '<=', today), ('state', '!=', 'revoked')])

        to_grant = delegations.filtered(lambda d: d.state == 'w_ict' and d.date_from == today)
        to_revoke = delegations.filtered(lambda d: d.state == 'confirm' and d.date_revoke_after2_days == today)
        if to_grant:
            for rec in to_grant:
                rec.action_confirm()
        if to_revoke:
            for rec in to_revoke:
                rec.action_cancel()

        print('finish')
        return True
