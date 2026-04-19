from odoo import models, fields, api, _
from odoo.exceptions import  UserError


class PPEReceipt(models.Model):
    _name = 'ppe.receipt'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'PPE Receipt Document'
    _order = 'name desc'

    def unlink(self):
        if self.state != 'draft':
            raise UserError("You cannot delete this Blasting Work Permit. Only DRAFT records can be deleted.")
        return super(PPEReceipt, self).unlink()

    # معلومات المستند الأساسية
    name = fields.Char(string='Permit Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('ppe.receipt') or ' '

        return super(PPEReceipt, self).create(vals)

    doc_no = fields.Char(string="Doc. No.", default="UMC-QHSE-QP-PPE/06", readonly=True)
    date = fields.Date(string="Date", default=fields.Date.context_today)

    # معلومات الموظف
    requester_id = fields.Many2one('res.users', string='Requester / مقدم الطلب', default=lambda self: self.env.user)
    department_id = fields.Many2one('hr.department', string='القسم / Department',
                                    default=lambda self: self.env.user.employee_id.department_id)
    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        default=lambda self: self.env.company,
        required=True
    )

    # تفاصيل المعدات المستلمة
    receipt_line_ids = fields.One2many('ppe.receipt.line', 'receipt_id', string='Details of PPE Received')

    reason_type = fields.Selection([
        ('new_employee', 'New Employee'),
        ('annual_quota', 'Annual Quota'),
        ('damage_replacement', 'Damage Replacement'),
        ('jsa', 'JSA'),
        ('others', 'Others')
    ], string='Reasons & Justification')
    other = fields.Text(string='Others')

    # الإقرارات القانونية (Confirmations)
    confirm_training = fields.Boolean(string='Confirmed Training & Instructions received', required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('officer', 'Safety Officer'),
        ('senior', 'Senior EX'),
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

    def make_issuance_request_function(self):
        for rec in self:
            if not rec.receipt_line_ids:
                raise UserError(_("Please add PPE items before creating issuance request."))

            # إنشاء رأس طلب الصرف
            issuance_vals = {
                'title': _("PPE Receipt: %s") % rec.name,
                'state': 'draft',
                'origin': rec.name,
                'company_id': rec.env.company.id,
                'requested_by': self.env.user.id,
                'issuance_type': 'internal_issuance',
                'request_date': fields.Date.today(),
            }

            issuance_rec = self.env['issuance.request'].create(issuance_vals)

            issuance_lines = []
            for line in rec.receipt_line_ids:
                # تجهيز الوصف ليشمل اسم الموظف ورقمه
                emp_info = ""
                if line.employee_id:
                    emp_info = " - Employee: %s (%s)" % (line.employee_id.name, line.emp_code or 'N/A')
                
                description = "%s %s" % (rec.name, emp_info)

                issuance_lines.append((0, 0, {
                    'product_id': line.ppe_type.id,
                    'product_uom_id': line.ppe_type.uom_id.id,
                    'qty_requested': line.qty_approved, 
                    'name': description, 
                }))

            if issuance_lines:
                issuance_rec.write({'line_ids': issuance_lines})
        return True

    def action_officer(self):
        for rec in self:
            rec.write({
                'state': 'officer',
                'done_user_id': self.env.user.id,
            })
            rec.action_update_activities()

    def action_senior(self):
        for rec in self:
            rec.write({
                'state': 'senior',
                'officer_user_id': self.env.user.id,
                'date_of_safety': fields.Date.context_today(self),
            })
            rec.action_update_activities()

    def action_done(self):
        for rec in self:
            rec.write({
                'state': 'done',
                'senior_user_id': self.env.user.id,
                'date_of_safety': fields.Date.context_today(self),
            })
            rec.make_issuance_request_function()
            rec.action_update_activities()

    def action_update_activities(self):
        for rec in self:
            users_to_notify = self.env['res.users']
            message = ""

            if rec.state == 'officer':
                group = self.env.ref('base_rida.rida_group_safety_officer', raise_if_not_found=False)
                users_to_notify = group.user_ids if group else users_to_notify
                message = _("New PPE Receipt No. %s awaits Safety Officer review.") % rec.name

            elif rec.state == 'senior':
                group = self.env.ref('base_rida.rida_group_senior_officer', raise_if_not_found=False)
                users_to_notify = group.user_ids if group else users_to_notify
                message = _("PPE Receipt No. %s awaits Senior EX review.") % rec.name

            elif rec.state == 'done':
                users_to_notify = rec.requester_id
                message = _("Your PPE Receipt No. %s has been officially approved.") % rec.name

            for user in users_to_notify:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    summary=message,
                    note=message
                )

class PPEReceiptLine(models.Model):
    _name = 'ppe.receipt.line'
    _description = 'PPE Receipt Line'

    receipt_id = fields.Many2one('ppe.receipt')
    ppe_type = fields.Many2one('product.product', string='Type of PPE', required=True)
    brand_sn = fields.Char(string="Brand or S/N", related='ppe_type.brand')
    quantity = fields.Float(string='Quantity', default=1.0)
    qty_approved = fields.Float(string='Quantity Approved', default=1.0)
    reason_type = fields.Selection(related='receipt_id.reason_type', store=False)
    employee_id = fields.Many2one('hr.employee', string="Employee Name")
    job_id = fields.Many2one('hr.job', string="Position Title", related='employee_id.job_id', readonly=True)
    emp_code = fields.Char(readonly=True, string="Staff No", store=True, related='employee_id.emp_code')
    emp_department_id = fields.Many2one(related="employee_id.department_id", string="Department/Section")
    qty_hand = fields.Float(string='Quantity On Hand', compute='_compute_qty_hand', store=False)

    @api.depends('ppe_type')
    def _compute_qty_hand(self):
        for line in self:
            if line.ppe_type:
                line.qty_hand = line.ppe_type.qty_available
            else:
                line.qty_hand = 0.0
