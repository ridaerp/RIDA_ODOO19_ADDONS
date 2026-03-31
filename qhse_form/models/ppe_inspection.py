from odoo import models, fields, api, _
from odoo.exceptions import  UserError


class PPEInspection(models.Model):
    _name = 'ppe.inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'PPE Inspection Document'
    _order = 'name desc'

    def unlink(self):
        if self.state != 'draft':
            raise UserError("You cannot delete this Blasting Work Permit. Only DRAFT records can be deleted.")
        return super(PPEInspection, self).unlink()

    name = fields.Char(string='Permit Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('ppe.complaint') or ' '

        return super(PPEInspection, self).create(vals)

    doc_no = fields.Char(string="Doc. No.", default="UMC-QHSE-QP-PPE/05", readonly=True)
    date = fields.Date(string="Date", default=fields.Date.context_today)

    requester_id = fields.Many2one('res.users', string='Requester / مقدم الطلب', default=lambda self: self.env.user)

    plant_unit = fields.Many2one('hr.department',string="Plant/Unit")

    # تفاصيل الفحص (الجدول الأول)
    inspection_line_ids = fields.One2many('ppe.inspection.line', 'inspection_id',
                                          string='Details of Inspected PPE')

    # ملخص المعدات التالفة (الجدول الثاني)
    defect_line_ids = fields.One2many('ppe.inspection.defect.line', 'inspection_id',
                                      string='Summary of Defected PPE')

    # بيانات الفحص والاعتماد
    inspected_by_id = fields.Many2one('res.users', string='Inspected By')
    inspected_position = fields.Char(related='inspected_by_id.job_title', string='Position')

    approved_by_id = fields.Many2one('res.users', string='Reviewed & Approved By')
    approved_position = fields.Char(related='approved_by_id.job_title', string='Position')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('officer', 'Safety Officer Review'),
        ('senior', 'Senior EX Review'),
        ('done', 'Approved')
    ], default='draft', string='Status', tracking=True)
    reason_reject = fields.Text(string='Reject Reason', tracking=True)

    officer_user_id = fields.Many2one('res.users', string='Officer Reviewer', readonly=True)
    senior_user_id = fields.Many2one('res.users', string='Senior Reviewer', readonly=True)
    done_user_id = fields.Many2one('res.users', string='Requester Approver', readonly=True)

    date_of_safety = fields.Date(string="Safety Review Date")
    date_senior = fields.Date(string="Senior Review Date")
    issuance_count = fields.Integer(compute='_compute_issuance_count')

    def _compute_issuance_count(self):
        for rec in self:
            rec.issuance_count = self.env['issuance.request'].search_count([('origin', '=', rec.name)])

    def action_view_issuance_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Issuance Requests'),
            'res_model': 'issuance.request',
            'view_mode': 'list,form',
            'domain': [('origin', '=', self.name)],
            'context': {'default_origin': self.name},
        }

    def action_officer(self):
        for rec in self:
            rec.write({
                'state': 'officer',
                'done_user_id': self.env.user.id,
            })
            rec.action_update_activities()

    def action_senior(self):
        for rec in self:
            rec.defect_line_ids.unlink()

            defect_vals = []
            for line in rec.inspection_line_ids:
                if line.condition < 50:
                    defect_vals.append((0, 0, {
                        'ppe_product_id': line.ppe_type.id,
                        'brand_sn': line.brand_sn,
                        'comment': _("Condition is %.2f%%") % line.condition,
                        'action_required': 'replace',
                    }))

            # تحديث الحالة ونقل البيانات
            rec.write({
                'state': 'senior',
                'officer_user_id': self.env.user.id,
                'date_of_safety': fields.Date.context_today(self),
                'defect_line_ids': defect_vals,
            })
            rec.action_update_activities()

    def action_done(self):
        for rec in self:
            rec.write({
                'state': 'done',
                'senior_user_id': self.env.user.id,
                'date_senior': fields.Date.context_today(self)
            })
            # استدعاء دالة إنشاء طلب الصرف
            rec.make_issuance_request_function()
            rec.action_update_activities()

    def action_update_activities(self):
        for rec in self:

            users_to_notify = self.env['res.users']
            message = ""

            if rec.state == 'officer':
                group = self.env.ref('base_rida.rida_group_safety_officer', raise_if_not_found=False)
                users_to_notify = group.user_ids if group else users_to_notify
                message = _("New Inspection No. %s awaits Safety Officer review.") % rec.name

            elif rec.state == 'senior':
                group = self.env.ref('base_rida.rida_group_senior_officer', raise_if_not_found=False)
                users_to_notify = group.user_ids if group else users_to_notify
                message = _("Inspection No. %s awaits Senior EX review.") % rec.name

            elif rec.state == 'done':
                users_to_notify = rec.requester_id
                message = _("Your Inspection No. %s has been approved.") % rec.name

            for user in users_to_notify:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    summary=message,
                    note=message
                )

    def make_issuance_request_function(self):
        valid_defect_lines = self.defect_line_ids.filtered(
            lambda l: l.action_required in ['replace', 'service', 'others'] and l.ppe_product_id
        )

        if not valid_defect_lines:
            return False

        # تجهيز بيانات الطلب الرئيسي
        issuance_vals = {
            'title': _("PPE Issuance for %s") % self.name,
            'state': 'draft',
            'origin': self.name,
            'company_id': self.env.company.id,
            'requested_by': self.senior_user_id.id,
            'issuance_type': 'internal_issuance',
            'request_date': fields.Date.today(),

        }

        issuance_rec = self.env['issuance.request'].create(issuance_vals)

        # تجهيز سطور الطلب
        issuance_lines = []
        for line in valid_defect_lines:
            issuance_lines.append((0, 0, {
                'product_id': line.ppe_product_id.id,
                'product_uom_id': line.ppe_product_id.uom_id.id,
                'qty_requested': 1.0,
                'name': line.comment or line.ppe_product_id.display_name,
            }))

        if issuance_lines:
            issuance_rec.write({'line_ids': issuance_lines})

        return issuance_rec


class PPEInspectionLine(models.Model):
    _name = 'ppe.inspection.line'
    _description = 'PPE Inspection Detail Line'

    inspection_id = fields.Many2one('ppe.inspection', ondelete='cascade')
    ppe_type = fields.Many2one('product.product', string='Type of PPE', required=True)
    brand_sn = fields.Char(string="Brand or S/N", related='ppe_type.brand', store=True)
    sub_location = fields.Char(string='Sub-Location')
    condition = fields.Float(string='Condition (%)')



class PPEInspectionDefectLine(models.Model):
    _name = 'ppe.inspection.defect.line'
    _description = 'PPE Defect Summary Line'

    inspection_id = fields.Many2one('ppe.inspection', ondelete='cascade')
    # تغيير الحقل ليكون مرتبطاً بالمنتج لضمان صحة البيانات
    ppe_product_id = fields.Many2one('product.product', string='Type of PPE')
    brand_sn = fields.Char(string='Brand or S/N')

    action_required = fields.Selection([
        ('service', 'Service'),
        ('maintenance', 'Maintenance'),
        ('replace', 'Replace'),
        ('cleaning', 'Cleaning'),
        ('others', 'Others')
    ], string='Action Required', default='replace')

    comment = fields.Text(string='Comment/Further Action')
    other = fields.Text(string='Others')