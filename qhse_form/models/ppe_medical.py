from odoo import models, fields, api, _
from odoo.exceptions import  UserError

class PPEMedicalCase(models.Model):
    _name = 'ppe.medical'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'PPE Replacement Document - Medical Case'
    _order = 'name desc'

    def unlink(self):
        if self.state != 'draft':
            raise UserError("You cannot delete this Blasting Work Permit. Only DRAFT records can be deleted.")
        return super(PPEMedicalCase, self).unlink()

    name = fields.Char(string='Permit Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('ppe.medical') or ' '

        return super(PPEMedicalCase, self).create(vals)

    doc_no = fields.Char(string="Doc. No.", default="UMC-QHSE-QP-PPE/04", readonly=True)

    requester_id = fields.Many2one('res.users', string='Requester / مقدم الطلب', default=lambda self: self.env.user)

    employee_id = fields.Many2one('hr.employee', string="Employee Name")
    job_id = fields.Many2one('hr.job', string="Position Title", related='employee_id.job_id', readonly=True)
    emp_code = fields.Char(readonly=True, string="Staff No", store=True, related='employee_id.emp_code')
    emp_department_id = fields.Many2one(related="employee_id.department_id", string="Department/Section")
    line_supervisor_id = fields.Many2one('hr.employee', string='Line Supervisor')
    position_id = fields.Many2one('hr.job', string="Position Title", related='line_supervisor_id.job_id', readonly=True)
    date = fields.Date(string='Date', default=fields.Date.today())

    # تفاصيل الحالة العمالية
    affected_body_part = fields.Char(string='Affected part of the body')
    concerned_ppe = fields.Char(string='Concerned PPE')
    job_nature = fields.Text(string='Employee job nature')

    # قسم الطبيب المعتمد (Authorized Physician Use Only)
    diagnoses_results = fields.Text(string='Diagnoses & test Result')
    medical_condition = fields.Text(string='Employee medical condition')
    current_ppe_effect = fields.Text(string='Effect of current PPE to medical condition')
    physician_recommendation = fields.Binary(string='Physician Report')
    # physician_signature_date = fields.Date(string='Physician Signature Date')

    # قسم إدارة الصحة والسلامة (QHSE Department Use Only)
    new_ppe_safety_eval = fields.Text(string='Employee safety with new PPE')
    risk_rating_new_ppe = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string='Risk rating (New PPE)')

    final_decision = fields.Selection([
        ('new_ppe', 'New PPE'),
        ('transfer', 'Transfer to other Job'),
        ('terminate', 'Terminate')
    ], string='Recommendation and Final decision')

    # حقول التوقيعات / الاعتمادات
    line_supervisor_user_id = fields.Many2one('res.users', string='Approved By (Supervisor)', readonly=True)
    senior_health_user_id = fields.Many2one('res.users', string='Approved By (Senior Health)', readonly=True)
    senior_safety_user_id = fields.Many2one('res.users', string='Approved By (Senior Safety)', readonly=True)
    manager_user_id = fields.Many2one('res.users', string='Approved By (Manager)', readonly=True)
    hr_action_user_id = fields.Many2one('res.users', string='Approved By (HR)', readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('line_supervisor', 'Line Supervisor'),
        ('senior_health', 'Senior Health EX'),
        ('senior_safety', 'Senior Safety EX'),
        ('manager', 'Manager Approval'),
        ('hr_action', 'HR Action'),
        ('done', 'Completed'),
        ('cancel', 'Cancelled'),
    ], default='draft', string='Status', tracking=True)
    # حقل الربط مع طلب المنتج
    product_request_ids = fields.One2many('request.product', 'medical_case_id', string='Product Requests')
    product_request_count = fields.Integer(compute='_compute_product_request_count')
    is_product_done = fields.Boolean(compute='_compute_is_product_done', store=False)
    mr_count = fields.Integer(compute='_compute_mr_count')
    update_risk_register = fields.Boolean(string="Update the Risk Register")
    update_jsa = fields.Boolean(string="Update the JSA")
    training_staff = fields.Boolean(string="Training the staff")

    def action_create_mr_from_medical(self):
        self.ensure_one()

        # جلب معرف الواجهة (View ID) لنموذج طلب المواد
        view_id = self.env.ref('material_request.view_material_request_form')

        # البحث عن آخر طلب منتج مكتمل لجلب بيانات الصنف منه (اختياري)
        last_product = self.product_request_ids.filtered(lambda r: r.state == 'done')[:1]

        return {
            'name': _('New Material Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'material.request',
            'view_mode': 'form',
            'target': 'current',
            'view_id': view_id.id,
            'context': {
                'default_medical_case_id': self.id,  # لربط الـ MR بالحالة الطبية
                'default_title': _("PPE Replacement: %s") % self.name,
                'default_employee_id': self.employee_id.id,
                'default_company_id': self.env.company.id,
                # إذا أردت تمرير المنتج الذي تم إنشاؤه تلقائياً في السطور:
                'default_request_line_ids': [(0, 0, {'product_id': last_product.prod_id.id, 'product_uom_qty': 1})]
            }
        }

    def action_view_mrs(self):
        """ يفتح قائمة طلبات المواد (Material Requests) المرتبطة بهذه الحالة """
        self.ensure_one()
        return {
            'name': _('Material Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'material.request',  # تأكد أن هذا هو الاسم التقني لموديل طلب المواد لديك
            'view_mode': 'list,form',
            'domain': [('medical_case_id', '=', self.id)],
            'context': {'default_medical_case_id': self.id},
        }

    def _compute_is_product_done(self):
        for rec in self:
            done_requests = rec.product_request_ids.filtered(lambda r: r.state == 'done')
            rec.is_product_done = True if done_requests else False

    def _compute_mr_count(self):
        for rec in self:
            rec.mr_count = self.env['material.request'].search_count([('medical_case_id', '=', rec.id)])

    def _compute_product_request_count(self):
        for rec in self:
            rec.product_request_count = len(rec.product_request_ids)

    def action_create_product_request(self):
        self.ensure_one()
        return {
            'name': _('Create Product Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'request.product',
            'view_mode': 'form',
            'context': {
                'default_medical_case_id': self.id,
                'default_product_name': self.concerned_ppe,
                'default_description': _('Replacement for Medical Case: %s') % self.name,
            },
            'target': 'new',
        }

    def action_view_product_requests(self):
        """ يفتح قائمة طلبات المنتجات المرتبطة بهذا الملف """
        self.ensure_one()
        return {
            'name': _('Product Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'request.product',
            'view_mode': 'list,form',
            'domain': [('medical_case_id', '=', self.id)],
            'context': {'default_medical_case_id': self.id},
        }

    def action_submit(self):
        self.write({'state': 'line_supervisor'})
        self.action_update_activities()

    def action_approve_supervisor(self):
        for rec in self:
            is_admin = self.env.user.has_group('base.group_system')


            line_manager_user = rec.employee_id.parent_id.user_id

            if not is_admin:
                if not line_manager_user or line_manager_user != self.env.user:
                    raise UserError(_("Sorry! You are not authorized to approve this document. "
                                      "Only the assigned Line Manager can approve this."))

            rec.write({
                'state': 'senior_health',
                'line_supervisor_user_id': self.env.user.id
            })

            rec.action_update_activities()

    def action_approve_health(self):
        self.write({
            'state': 'senior_safety',
            'senior_health_user_id': self.env.user.id
        })
        self.action_update_activities()

    def action_approve_safety(self):
        self.write({
            'state': 'manager',
            'senior_safety_user_id': self.env.user.id
        })
        self.action_update_activities()

    def action_approve_manager(self):
        self.write({
            'state': 'hr_action',
            'manager_user_id': self.env.user.id
        })
        self.action_update_activities()

    def action_complete_hr(self):
        self.write({
            'state': 'done',
            'hr_action_user_id': self.env.user.id
        })
        self.action_update_activities()

    def action_update_activities(self):
        for rec in self:

            users_to_notify = self.env['res.users']
            message = ""

            if rec.state == 'line_supervisor':
                message = _("Medical Case %s: Awaiting Supervisor Approval.") % rec.name
                users_to_notify = rec.line_supervisor_id.user_id  # إرسال للمشرف المباشر المحدد في الحقل

            elif rec.state == 'senior_health':
                message = _("Medical Case %s: Awaiting Senior Health Review.") % rec.name
                group = self.env.ref('base_rida.rida_group_senior_health', raise_if_not_found=False)
                if group: users_to_notify = group.user_ids

            elif rec.state == 'senior_safety':
                message = _("Medical Case %s: Awaiting Senior Safety Review.") % rec.name
                group = self.env.ref('base_rida.rida_group_senior_safety', raise_if_not_found=False)
                if group: users_to_notify = group.user_ids

            elif rec.state == 'manager':
                message = _("Medical Case %s: Awaiting QHSE Manager Approval.") % rec.name
                group = self.env.ref('base_rida.rida_group_qhse_manager', raise_if_not_found=False)
                if group: users_to_notify = group.user_ids

            elif rec.state == 'hr_action':
                message = _("Medical Case %s: Awaiting HR Action.") % rec.name
                group = self.env.ref('base_rida.rida_hr_manager_notify', raise_if_not_found=False)
                if group: users_to_notify = group.user_ids

            elif rec.state == 'done':
                message = _("Medical Case %s has been completed.") % rec.name
                users_to_notify = rec.requester_id

            # إنشاء النشاط
            if users_to_notify and message:
                model_id = self.env['ir.model']._get('ppe.medical').id
                for user in users_to_notify:
                    rec.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=user.id,
                        note=message,
                        summary=message
                    )

class RequestProduct(models.Model):
    _inherit = 'request.product'

    medical_case_id = fields.Many2one('ppe.medical', string='Related Medical Case')

class MaterialRequest(models.Model):
    _inherit = 'material.request'

    medical_case_id = fields.Many2one('ppe.medical', string='Related Medical Case')
