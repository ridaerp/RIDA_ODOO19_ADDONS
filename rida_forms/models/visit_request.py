
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

# visit site Workflow (IF visit type: personal ) from requester → hr_approve → c_level_approval or site manager → adm_man_approve → done
# visit site Workflow (IF visit site type: work ) from requester → Department Approval → hr_approve → c_level_approval or site manager → adm_man_approve → done
_STATES = [
    ('draft', 'Draft'),
    ('dep_approve', 'Waiting Department Approval'),
    ('hr_approve', 'Waiting HR/Admin Manager Approval'),
    ('c_level_approval', 'Waiting Site Manager Approval'),
    ('adm_man_approve', 'Admin Affirm'),
    ('reject', 'Rejected'),
    ('cancel', 'Cancelled'),
    ('approve', 'Approved'),
]

class VisitRequest(models.Model):
    _name = 'visit.request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Visit Request'
    _order = 'id desc'
    _rec_name = 'name_seq'


    def _get_employee(self):
        if len(self.env.user.employee_ids) > 0:
            employee = self.env.user.employee_ids[0].id
            return employee or False

    name_seq = fields.Char("Number", required=True, index=True, default=lambda self: _('New'), copy=False)
    date_request = fields.Date("Request Date", default=fields.Date.context_today, required=True)
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    num_of_days = fields.Integer(string='Number Of Days', compute='_compute_num_of_days', store=True)
    purpose = fields.Html('Purpose', required=True)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    visit_type = fields.Selection([('personal', 'Personal'),
                                     ('work', 'Work'),],
                                    required=True, default='work')
    activity = fields.Selection([('personality', 'Personality'),
                                     ('work', 'Work'),
                                    ('field_visit', 'Visited Field'),
                                    ('meeting','Meeting'),
                                    ('other', 'Other')],
                                    required=True,string='Activites' ,default='work')
    other = fields.Char(string='Other')
    requested_by = fields.Many2one("res.users", readonly=True, string="Requested Employee", track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", default=lambda  self: self._get_employee())
    department_id = fields.Many2one('hr.department', string='Department',
                                    related="requested_by.employee_ids.department_id", readonly=True)
    job_id = fields.Many2one('hr.job', related="requested_by.employee_ids.job_id", string='Job Title', readonly=True)
    company_id = fields.Many2one('res.company', string='Company')
    
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", required=True)


    state = fields.Selection(selection=_STATES, string='Status', index=True, track_visibility='onchange', readonly=True,
                             required=True, copy=False, default='draft')
    visit_line_ids = fields.One2many('visit.request.line', 'visit_id', string='Visit Lines')
    department_involved = fields.Many2many('hr.department', string='Departments Involved', required=True)

    ugrently=fields.Boolean("ugrent")


    @api.onchange('employee_id')
    def _onchange_employee_id_update_company(self):
        for rec in self:
            rec.company_id = rec.employee_id.company_id.id if rec.employee_id else False


    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Only draft records can be deleted!")

        return super(VisitRequest, self).unlink()


    @api.depends('date_from', 'date_to')
    def _compute_num_of_days(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                delta = (rec.date_to - rec.date_from).days + 1
                rec.num_of_days = delta if delta > 0 else 0
            else:
                rec.num_of_days = 0

    # @api.constrains('date_request', 'date_from')
    # def _check_date_from_after_request(self):
    #     for rec in self:
    #         if self.ugrently:
    #             return True
    #         else:
    #             if rec.date_request and rec.date_from:
    #                 min_allowed = rec.date_request + timedelta(hours=72)
    #                 if rec.date_from < min_allowed:
    #                     raise ValidationError(
    #                         _("The 'Date From' must be at least 72 hours (3 days) after the 'Request Date'."))


    @api.constrains('date_request', 'date_from', 'ugrently')
    def _check_date_from_after_request(self):
        for rec in self:
            # Skip validation if marked as urgent
            if rec.ugrently:
                continue

            if rec.date_request and rec.date_from:
                min_allowed = rec.date_request + timedelta(hours=72)

                if rec.date_from < min_allowed:
                    raise ValidationError(
                        _("The 'Date From' must be at least 72 hours (3 days) after the 'Request Date' unless marked as urgent.")
                    )
                
    def get_requested_by(self):
        user = self.env.user.id
        return user

    @api.model
    def create(self, vals):
        if vals.get('name_seq', 'New') == 'New':
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('visit.request') or 'New'
        result = super(VisitRequest, self).create(vals)

        return result

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError(_("Date To cannot be earlier than Date From."))

    def action_submit(self):
        for rec in self:
            if rec.visit_type == 'work':
                rec.state = 'dep_approve'
            else:
                rec.state = 'hr_approve'
        # self.activity_update()

    def action_dep_approve(self):
        line_manager = False
        try:
            line_manager = self.requested_by.line_manager_id
        except:
            line_manager = False
        if not line_manager or line_manager != self.env.user:
            raise UserError("Sorry. Your are not authorized to approve this document!")
        return self.write({'state': 'hr_approve'})
        # for rec in self:
        #     rec.state = 'hr_approve'
        # self.activity_update()

    def action_hr_approve(self):
        for rec in self:
            rec.state = 'c_level_approval'
        self.activity_update()

    def action_site_manager_approve(self):
        # c_level_id = False
        # try:
        #     c_level_id = self.employee_id.department_id.c_level_id
        # except:
        #     c_level_id = False
        # if not c_level_id or c_level_id != self.env.user:
        #     raise UserError("Sorry. Your are not authorized to approve this document!")
        return self.write({'state': 'adm_man_approve'})


    def action_done(self):
        for rec in self:
            rec.state = 'approve'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_reject(self):
        for rec in self:
            rec.state = 'reject'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def activity_update(self):
        for rec in self:
            rec.activity_unlink(['master_data.mail_act_master_data_approval'])

            users = []
            message = ""

            if rec.state == 'dep_approve':
                users = self.env.ref('base_rida.rida_group_line_manager', raise_if_not_found=False).users
                message = "Request waiting for Department Approval."

            elif rec.state == 'hr_approve':
                users = self.env.ref('base_rida.rida_hr_manager_notify', raise_if_not_found=False).users
                message = "Request waiting for HR/Admin Manager approval."

            elif rec.state == 'c_level_approval':
                users = self.env.ref('base_rida.rida_group_site_manager', raise_if_not_found=False).users
                message = "Request waiting for Site Manager approval."

            elif rec.state == 'adm_man_approve':
                # users = self.env.ref('base_rida.rida_group_admin_affirm', raise_if_not_found=False).users
                message = "Admin affirmation required."

            else:
                continue

            for user in users:
                rec.activity_schedule(
                    'master_data.mail_act_master_data_approval',
                    user_id=user.id,
                    note=message,
                )


class VisitRequestLine(models.Model):
    _name = 'visit.request.line'

    visit_id = fields.Many2one('visit.request', string='Visit Request', ondelete='cascade')
    visit_name = fields.Char('Name / الاسم', required=True)
    degree = fields.Char('Degree / الدرجة')
    job = fields.Char('Job Position / الوظيفة')
    disease = fields.Char(string='الامراض المزمنه ان وجدت / Chronic disease if any')


