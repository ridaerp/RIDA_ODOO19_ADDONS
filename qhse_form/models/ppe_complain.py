from odoo import models, fields,api, _
from odoo.exceptions import  UserError



class PPEComplaint(models.Model):
    _name = 'ppe.complaint'
    _description = 'PPE Complain/Suggestion Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'


    def unlink(self):
        if self.state != 'draft':
            raise UserError("You cannot delete this Blasting Work Permit. Only DRAFT records can be deleted.")
        return super(PPEComplaint, self).unlink()

    name = fields.Char(string='Permit Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('ppe.complaint') or ' '

        return super(PPEComplaint, self).create(vals)

    doc_no = fields.Char(string="Doc. No.", default="UMC-QHSE-QP-PPE/01", readonly=True)
    date = fields.Date(string="Date", default=fields.Date.context_today)

    requester_id = fields.Many2one('res.users', string='Requester / مقدم الطلب', default=lambda self: self.env.user)

    employee_id = fields.Many2one('hr.employee', string="Employee Name")
    job_id = fields.Many2one('hr.job', string="Position Title", related='employee_id.job_id', readonly=True)
    emp_code = fields.Char(readonly=True, string="Staff No", store=True, related='employee_id.emp_code')
    emp_department_id = fields.Many2one(related="employee_id.department_id", string="Department/Section")

    reason = fields.Text(string="Reasons of complains/suggestion")
    special_conditions = fields.Text(string="Special Consideration/Condition")
    recommendation = fields.Text(string="Recommendation")

    find_of = fields.Text(string="Finding of investigation")
    comment_of_safety = fields.Text(string="Comment of safety officer")
    date_of_safety = fields.Date(string="Date", default=fields.Date.context_today)

    review = fields.Text(string="Review the finding of investigation")
    recommendation_senior = fields.Text(string="Recommendations")
    date_senior = fields.Date(string="Date", default=fields.Date.context_today)

    recommendation_manager = fields.Text(string="Recommendation &approval")
    action_to_take = fields.Text(string="Action to be taken")
    date_qhse_manager = fields.Date(string="Date", default=fields.Date.context_today)

    update_risk_register = fields.Boolean(string="Update the Risk Register")
    update_jsa = fields.Boolean(string="Update the JSA")
    training_staff = fields.Boolean(string="Training the staff")
    complaint_line_ids = fields.One2many('ppe.complaint.line','complaint_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('officer', 'Safety Officer Review'),
        ('senior', 'Senior EX Review'),
        ('manager', 'Manager Approval'),
        ('done', 'Approved')
    ], default='draft', string='Status', tracking=True)
    reason_reject = fields.Text(string='Reject Reason', tracking=True)


    def action_officer(self):
        for rec in self:
            rec.write({
                'state': 'officer',
                'date_of_safety': fields.Date.context_today(self)
            })
            rec.action_update_activities()

    def action_senior(self):
        for rec in self:
            rec.write({
                'state': 'senior',
                'date_senior': fields.Date.context_today(self)
            })
            rec.action_update_activities()

    def action_manager(self):
        for rec in self:
            rec.write({
                'state': 'manager',
                'date_qhse_manager': fields.Date.context_today(self)
            })
            rec.action_update_activities()

    def action_done(self):
        for rec in self:
            rec.state = 'done'
            rec.action_update_activities()

    def action_update_activities(self):
        for rec in self:
            # 1. جلب مجموعات الصلاحيات الخاصة بمسؤولي السلامة
            group_officer = self.env.ref('base_rida.rida_group_safety_officer')
            group_senior = self.env.ref('base_rida.rida_group_senior_officer')
            group_manager = self.env.ref('base_rida.rida_group_qhse_manager')  # إضافة مجموعة المدير

            to_notify = []
            requester_user = rec.requester_id

            # حالة: المراجعة من قبل ضابط السلامة
            if rec.state == 'officer':
                message = f"New Complaint/Suggestion No. {rec.name} is awaiting Safety Officer review."
                for user in group_officer.user_ids:
                    to_notify.append({'user': user, 'note': message})

            # حالة: المراجعة من قبل Senior EX
            elif rec.state == 'senior':
                message = f"Request No. {rec.name} is awaiting Senior EX review."
                for user in group_senior.user_ids:
                    to_notify.append({'user': user, 'note': message})

            # حالة: انتظار اعتماد المدير
            elif rec.state == 'manager':
                message = f"Request No. {rec.name} is awaiting QHSE Manager approval."
                for user in group_manager.user_ids:
                    to_notify.append({'user': user, 'note': message})

            # حالة: تم الاعتماد النهائي (إشعار لمقدم الطلب)
            elif rec.state == 'done':
                message = f"Your request No. {rec.name} has been officially approved."
                if requester_user:
                    to_notify.append({'user': requester_user, 'note': message})

            # 2. تنفيذ إنشاء الأنشطة (Activity)
            # تأكد من أن 'ppe.complaint' هو الاسم الصحيح للموديل في قاعدة البيانات
            model_id = self.env['ir.model']._get('ppe.complaint').id

            for item in to_notify:
                # التحقق من عدم تكرار نفس النشاط لنفس المستخدم
                existing_activity = self.env['mail.activity'].search([
                    ('res_id', '=', rec.id),
                    ('res_model_id', '=', model_id),
                    ('user_id', '=', item['user'].id),
                    ('summary', '=', item['note'])
                ], limit=1)

                if not existing_activity:
                    rec.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=item['user'].id,
                        note=item['note'],
                        summary=item['note']
                    )
class PPEReceiptLine(models.Model):
    _name = 'ppe.complaint.line'
    _description = 'PPE Complaint Line'

    complaint_id = fields.Many2one('ppe.complaint')
    ppe_type = fields.Many2one('product.product', string='Type of PPE', required=True)
    brand_sn = fields.Char(string="Brand or S/N", related='ppe_type.brand')
    purpose = fields.Text(string="Purpose of PPE")