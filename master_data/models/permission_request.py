# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date
from odoo.exceptions import UserError


class PermissionRequest(models.Model):
    _name = "permission.request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Permission Request"

    name = fields.Char(string="Reference", readonly=True, copy=False, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('manager', 'Waiting Manager'),
        ('ict', 'Waiting ICT Verify'),
        ('approved', 'Access Granted'),
        ('reject', 'Rejected'),
        ('expired', 'Expired'),
    ], string='Status', default='draft', tracking=True)

    request_type = fields.Selection([
        ('existing', 'Existing Employee'),
        ('new', 'New User')
    ], string="Request Type", default='existing', required=True)

    # بيانات الطلب
    requester_id = fields.Many2one('res.users', string="Requester", default=lambda self: self.env.user, readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", tracking=True)
    user_id = fields.Many2one('res.users', related='employee_id.user_id', string="Related User", store=True)

    requested_access_description = fields.Text("Required Access Description", required=True,
                                               help="Write here what permissions you need (e.g., Access to Sales, Accounting, etc.)", tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)

    requested_company_ids = fields.Many2many('res.company', 'rel_permission_companies', string="Requested Companies",
                                             tracking=True)
    reason = fields.Text("Justification", required=True, tracking=True)
    is_temporary = fields.Boolean("Temporary Access?")
    date_to = fields.Date("Expiry Date",tracking=True)
    reason_reject = fields.Text(string='Reject Reason', tracking=True)
    # حقل تقني لتخزين المجموعات الحالية للموظف
    existing_group_ids = fields.Many2many('res.groups', compute='_compute_existing_groups')
    employee_name = fields.Char("Employee Name", tracking=True)
    employee_email = fields.Char("Employee Email", tracking=True)

    user_type = fields.Selection([
        ('internal', 'Internal User'),
        ('portal', 'Portal User')
    ], string="New User Type", default='internal', help="Define if the new user is internal staff or portal access.")
    group_ids = fields.Many2many('res.groups', 'rel_group_add', string="Groups to Add", tracking=True)
    groups_to_remove_ids = fields.Many2many('res.groups', 'rel_group_remove', string="Groups to Remove", tracking=True)

    def action_ict_approve(self):
        self.ensure_one()
        # 1. التحقق من صلاحيات القائم بالاعتماد
        if not self.env.user.has_group('base.group_system') and not self.env.user.has_group(
                'base_rida.rida_group_master_data_manager'):
            raise UserError(_("Only ICT Administrators can grant permissions!"))

        target_user = False

        # 2. معالجة حالة المستخدم الجديد
        if self.request_type == 'new':
            if not self.employee_name or not self.employee_email:
                raise UserError(_("Employee Name and Email are required for new users."))

            user_vals = {
                'name': self.employee_name,
                'login': self.employee_email,
                'email': self.employee_email,
                'company_id': self.company_id.id,
                'company_ids': [(6, 0, self.requested_company_ids.ids)],
                'group_ids': [(6, 0, self.group_ids.ids)],
            }

            # إذا كان النوع Portal يتم استبدال المجموعات بمجموعة البوابة فقط
            if self.user_type == 'portal':
                user_vals['group_ids'] = [(6, 0, [self.env.ref('base.group_portal').id])]

            target_user = self.env['res.users'].sudo().create(user_vals)

            # إنشاء سجل موظف وربطه بالمستخدم الجديد
            new_emp = self.env['hr.employee'].sudo().create({
                'name': self.employee_name,
                'work_email': self.employee_email,
                'user_id': target_user.id,
            })
            self.employee_id = new_emp.id
        else:
            # 3. معالجة حالة المستخدم الحالي
            target_user = self.user_id

        # 4. تنفيذ التعديلات وتسجيلها في الـ Chatter
        if target_user:
            log_msg = "<b>Access Changes Applied:</b><br/>"
            changes = False

            # أ. إضافة الشركات المطلوبة
            if self.requested_company_ids:
                target_user.sudo().write({'company_ids': [(4, c.id) for c in self.requested_company_ids]})
                log_msg += "🏢 Companies Added: %s<br/>" % ", ".join(self.requested_company_ids.mapped('name'))
                changes = True

            # ب. إضافة المجموعات البرمجية
            if self.group_ids:
                target_user.sudo().write({'group_ids': [(4, g.id) for g in self.group_ids]})
                log_msg += "➕ Groups Added: %s<br/>" % ", ".join(self.group_ids.mapped('full_name'))
                changes = True

            # ج. حذف المجموعات (إذا تم تحديدها)
            if self.groups_to_remove_ids:
                target_user.sudo().write({'group_ids': [(3, g.id) for g in self.groups_to_remove_ids]})
                log_msg += "➖ Groups Removed: %s<br/>" % ", ".join(self.groups_to_remove_ids.mapped('full_name'))
                changes = True

            if changes:
                # كتابة التغييرات في سجل الطلب وسجل المستخدم
                self.message_post(body=log_msg)

        self.write({'state': 'approved'})

    # دالة جلب البيانات تلقائياً عند اختيار موظف موجود
    @api.onchange('employee_id', 'request_type')
    def _onchange_employee_id(self):
        if self.request_type == 'existing' and self.employee_id:
            self.employee_name = self.employee_id.name
            self.employee_email = self.employee_id.work_email or self.employee_id.user_id.login
        elif self.request_type == 'new':
            self.employee_name = ""
            self.employee_email = ""



    @api.depends('employee_id')
    def _compute_existing_groups(self):
        for rec in self:
            if rec.employee_id and rec.employee_id.user_id:
                rec.existing_group_ids = rec.employee_id.user_id.group_ids
            else:
                rec.existing_group_ids = False



    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('name', _('New')) == _('New'):
                val['name'] = self.env['ir.sequence'].next_by_code('permission.request') or _('New')
        return super(PermissionRequest, self).create(vals)

    def action_submit(self):
        self.state = 'manager'

    def action_manager_approve(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                pass
            else:
                self.ensure_one()
                try:
                    line_manager = self.requester_id.line_manager_id
                except:
                    line_manager = False

                if not line_manager or line_manager != rec.env.user:
                    raise UserError("Sorry. Your are not authorized to approve this document!")
        self.state = 'ict'

    def action_reject(self):
        self.state = 'rejected'

    def _cron_revoke_expired_permissions(self):
        today = date.today()
        expired_requests = self.search([
            ('state', '=', 'approved'),
            ('is_temporary', '=', True),
            ('date_to', '<', today)
        ])

        for request in expired_requests:
            if request.user_id:
                vals = {}
                log_msg = "<b>Expired Access Revoked Automatically:</b><br/>"

                # إزالة المجموعات التي تمت إضافتها في هذا الطلب
                if request.group_ids:
                    vals['group_ids'] = [(3, group.id) for group in request.group_ids]
                    log_msg += "➖ Groups Removed: %s<br/>" % ", ".join(request.group_ids.mapped('full_name'))

                # إزالة الشركات التي تمت إضافتها في هذا الطلب
                if hasattr(request, 'requested_company_ids') and request.requested_company_ids:
                    vals['company_ids'] = [(3, comp.id) for comp in request.requested_company_ids]
                    log_msg += "🏢 Companies Removed: %s<br/>" % ", ".join(request.requested_company_ids.mapped('name'))

                if vals:
                    # تحديث المستخدم وسحب الصلاحيات (sudo ضروري هنا)
                    request.user_id.sudo().write(vals)
                    request.user_id.message_post(body=log_msg)

                # تحديث حالة الطلب إلى منتهي
                request.write({'state': 'expired'})
                request.message_post(body=_("Status changed to Expired and permissions revoked."))