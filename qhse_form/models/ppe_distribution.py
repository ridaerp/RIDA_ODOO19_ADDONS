from odoo import models, fields, api, _
from odoo.exceptions import  UserError


class PPERoutineDistribution(models.Model):
    _name = 'ppe.distribution'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Routine PPE Distribution Form'
    _order = 'name desc'

    def unlink(self):
        if self.state != 'draft':
            raise UserError("You cannot delete this Blasting Work Permit. Only DRAFT records can be deleted.")
        return super(PPERoutineDistribution, self).unlink()

    # معلومات المستند الأساسية
    name = fields.Char(string='Permit Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('ppe.distribution') or ' '

        return super(PPERoutineDistribution, self).create(vals)

    doc_no = fields.Char(string="Doc. No.", default="UMC-QHSE-QP-PPE/07", readonly=True)
    date = fields.Date(string='Date', default=fields.Date.today())
    department_id = fields.Many2one('hr.department', string='Department/Section/Unit')

    # معلومات منشئ الطلب
    originator_id = fields.Many2one('res.users', string='Originated By')
    originator_position = fields.Char(string='Position')

    # تفاصيل المعدات
    line_ids = fields.One2many('ppe.distribution.line', 'distribution_id', string='Details of PPE')

    justification = fields.Text(string='Justification (if more than Routine Qty.)')

    # قسم QHSE (Review & Approval)
    junior_safety_executive_id = fields.Many2one('res.users', string='Safety Officer Executive')
    junior_comment = fields.Text(string='Officer Comment')
    junior_voucher_sn = fields.Char(string='Issuance voucher S/N (Officer)')

    senior_safety_executive_id = fields.Many2one('res.users', string='Senior Safety Executive')
    senior_comment = fields.Text(string='Senior Comment')
    senior_voucher_sn = fields.Char(string='Issuance voucher S/N (Senior)')
    issuance_count = fields.Integer(compute='_compute_issuance_count')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('junior_approve', 'Safety Officer Approval'),
        ('senior_approve', 'Senior Safety Approval'),
        ('done', 'Issued'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected')
    ], default='draft', tracking=True)
    reason_reject = fields.Text(string='Reject Reason', tracking=True)

    # دوال الأزرار (Actions)
    def action_junior_approve(self):
        for rec in self:
            rec.write({
                'state': 'junior_approve',
                'junior_safety_executive_id': self.env.user.id
            })
            rec.action_update_activities()

    def action_senior_approve(self):
        for rec in self:
            rec.write({
                'state': 'senior_approve',
                'senior_safety_executive_id': self.env.user.id
            })
            rec.action_update_activities()

    def action_done(self):
        for rec in self:
            rec.write({'state': 'done'})
            # استدعاء دالة إنشاء طلب الصرف من المخزن آلياً
            rec.make_issuance_request_function()
            rec.action_update_activities()

    def action_cancel(self):
        self.write({'state': 'cancel'})

    # دالة الأنشطة والاشعارات
    def action_update_activities(self):
        for rec in self:
            # تنظيف الأنشطة السابقة

            users_to_notify = self.env['res.users']
            message = ""

            if rec.state == 'junior_approve':
                group = self.env.ref('base_rida.rida_group_safety_officer', raise_if_not_found=False)
                users_to_notify = group.user_ids if group else users_to_notify
                message = _("New Routine PPE Distribution No. %s awaits Junior Safety review.") % rec.name

            elif rec.state == 'senior_approve':
                group = self.env.ref('base_rida.rida_group_senior_officer', raise_if_not_found=False)
                users_to_notify = group.user_ids if group else users_to_notify
                message = _("Routine PPE Distribution No. %s awaits Senior Safety review.") % rec.name

            elif rec.state == 'done':
                # إشعار لمنشئ الطلب
                users_to_notify = rec.originator_id or rec.create_uid
                message = _("Your Routine PPE Request No. %s has been approved and issued.") % rec.name

            for user in users_to_notify:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    summary=message,
                    note=message
                )

    def _compute_issuance_count(self):
        for rec in self:
            rec.issuance_count = self.env['issuance.request'].search_count([('origin', '=', rec.name)])

    def action_view_issuance_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Issuance Requests'),
            'res_model': 'issuance.request',
            'view_mode': 'list,form',
            'domain': [('origin', '=', self.name)],
            'context': {'default_origin': self.name},
        }

    def make_issuance_request_function(self):
        for rec in self:
            if not rec.line_ids:
                continue

            issuance_vals = {
                'title': _("Routine PPE Issuance: %s") % rec.name,
                'state': 'draft',
                'origin': rec.name,
                'company_id': self.env.company.id,
                'requested_by': rec.senior_safety_executive_id.id or self.env.user.id,
                'issuance_type': 'internal_issuance',
            }
            issuance_rec = self.env['issuance.request'].create(issuance_vals)

            lines = []
            for line in rec.line_ids:
                lines.append((0, 0, {
                    'product_id': line.ppe_type.id,
                    'product_uom_id': line.ppe_type.uom_id.id,
                    'qty_requested': line.qty_approved,
                    'name': rec.name,
                }))
            issuance_rec.write({'line_ids': lines})


class PPERoutineDistributionLine(models.Model):
    _name = 'ppe.distribution.line'
    _description = 'PPE Routine Distribution Line'

    distribution_id = fields.Many2one('ppe.distribution')
    ppe_type = fields.Many2one('product.product', string='Type of PPE', required=True)
    brand_sn = fields.Char(string="Brand or S/N", related='ppe_type.brand')
    unit = fields.Char(string='Unit', related='ppe_type.uom_id.name')
    quantity = fields.Float(string='QTY')
    qty_approved = fields.Float(string='Quantity Approved', default=1.0)
    last_distributed_date = fields.Date(
        string='Last Date (Dept)', 
        compute='_compute_last_issuance_per_product', 
        store=True
    )
    last_distributed_qty = fields.Float(
        string='Last Qty (Dept)', 
        compute='_compute_last_issuance_per_product', 
        store=True
    )
    size = fields.Char(string='Size/Specification')
    color = fields.Char(string='Color')


    @api.depends('ppe_type', 'distribution_id.department_id')
    def _compute_last_issuance_per_product(self):
        for line in self:
            line.last_distributed_date = False
            line.last_distributed_qty = 0.0
            
            if line.ppe_type and line.distribution_id.department_id:
                # Search in PPE Receipt Lines for the same product and same department
                last_receipt = self.env['ppe.receipt.line'].search([
                    ('ppe_type', '=', line.ppe_type.id),
                    ('receipt_id.department_id', '=', line.distribution_id.department_id.id),
                    ('receipt_id.state', '=', 'done')
                ], order='create_date desc', limit=1)

                if last_receipt:
                    line.last_distributed_date = last_receipt.receipt_id.date
                    line.last_distributed_qty = last_receipt.qty_approved

    @api.onchange('quantity')
    def _onchange_quantity_warning(self):
        """ Visual warning when user enters a higher quantity """
        if self.last_distributed_qty > 0 and self.quantity > self.last_distributed_qty:
            return {
                'warning': {
                    'title': _("Quantity Increase Detected"),
                    'message': _("The requested quantity for %s is higher than the last distribution (%s). "
                                 "Please ensure you provide a reason in the Justification field.") % 
                                 (self.ppe_type.name, self.last_distributed_qty),
                }
            }
