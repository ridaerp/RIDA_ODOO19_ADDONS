from odoo import models, fields, api, _
from odoo.exceptions import  UserError


class PPEDeduction(models.Model):
    _name = 'ppe.deduction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'PPE Deduction Document'
    _order = 'name desc'

    def unlink(self):
        if self.state != 'draft':
            raise UserError("You cannot delete this Blasting Work Permit. Only DRAFT records can be deleted.")
        return super(PPEDeduction, self).unlink()

    name = fields.Char(string='Document Number', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('ppe.deduction') or ' '

        records = super(PPEDeduction, self).create(val)

        for rec in records:
            rec.action_update_activities()

        return records

    doc_no = fields.Char(string="Doc. No.", default="UMC-QHSE-QP-PPE-03", readonly=True)

    requester_id = fields.Many2one('res.users', string='Requester / مقدم الطلب', default=lambda self: self.env.user)

    employee_id = fields.Many2one('hr.employee', string="Employee Name")
    job_id = fields.Many2one('hr.job', string="Position Title", related='employee_id.job_id', readonly=True)
    emp_code = fields.Char(readonly=True, string="Staff No", store=True, related='employee_id.emp_code')
    emp_department_id = fields.Many2one(related="employee_id.department_id", string="Department/Section")
    line_supervisor_id = fields.Many2one('hr.employee', string='Line Supervisor')
    position_id = fields.Many2one('hr.job', string="Position Title", related='line_supervisor_id.job_id', readonly=True)
    contract_number = fields.Char(string='Contract Number')
    hosting_dep = fields.Char(string='Hosting Dep.')
    date = fields.Date(string='Date', default=fields.Date.today())

    # جدول المعدات مع خانة السعر
    ppe_line_ids = fields.One2many('ppe.deduction.line', 'deduction_id', string='Details of PPE')
    total_deduction = fields.Float(string='Total Price', compute='_compute_total')

    # أسباب الاستقطاع (QHSE Use Only)
    deduction_reason = fields.Selection([
        ('intention', 'Intention'),
        ('lost', 'Lost'),
        ('miss_use', 'Miss Use'),
        ('contract', 'Contract'),
        ('negligence', 'Negligence'),
        ('others', 'Others')
    ], string='Probable Reasons of Deduction')
    other = fields.Text(string='Others')

    justification = fields.Text(string='Reasons & Justification')
    recommendation = fields.Text(string='Recommendation')
    responsible_safety_officer_id = fields.Many2one('res.users', string='Responsible Safety Officer')

    # الإقرار القانوني
    authorization_confirm = fields.Boolean(string='Authorize HR/Finance to deduct value', required=True)  #

    state = fields.Selection([
        ('draft', 'Draft'),
        ('officer', 'Safety Officer Review'),
        ('manager', 'Manager Approval'),
        ('hr', 'HR/Hosting Approval'),
        ('finance', 'Finance Approval'),
        ('done', 'Deducted')
    ], default='officer', string='Status', tracking=True)
    reason_reject = fields.Text(string='Reject Reason', tracking=True)


    @api.depends('ppe_line_ids.price')
    def _compute_total(self):
        for rec in self:
            rec.total_deduction = sum(rec.ppe_line_ids.mapped('price'))


    def action_officer(self):
        for rec in self:
            rec.state = 'officer'
            rec.action_update_activities()

    def action_manager(self):
        for rec in self:
            rec.write({
                'state': 'manager',
                'responsible_safety_officer_id': self.env.user.id,
            })
            rec.action_update_activities()

    def action_hr(self):
        for rec in self:
            rec.state = 'hr'
            rec.action_update_activities()

    def action_finance(self):
        for rec in self:
            rec.state = 'finance'
            rec.action_update_activities()

    def action_done(self):
        for rec in self:
            rec.state = 'done'
            rec.action_update_activities()

    def action_update_activities(self):
        for rec in self:
            # جلب المجموعات البرمجية
            group_officer = self.env.ref('base_rida.rida_group_safety_officer')
            group_manager = self.env.ref('base_rida.rida_group_qhse_manager')
            group_hr = self.env.ref('base_rida.rida_hr_manager_notify')
            group_finance = self.env.ref('base_rida.rida_finance_manager')

            users_to_notify = []
            message = ""

            if rec.state == 'officer':
                message = _("New PPE Deduction No. %s is awaiting Safety Officer review.") % rec.name
                users_to_notify = group_officer.user_ids
            elif rec.state == 'manager':
                message = _("Deduction Request No. %s is awaiting QHSE Manager approval.") % rec.name
                users_to_notify = group_manager.user_ids
            elif rec.state == 'hr':
                message = _("Deduction Request No. %s is awaiting HR Approval.") % rec.name
                users_to_notify = group_hr.user_ids
            elif rec.state == 'finance':
                message = _("Deduction Request No. %s is awaiting Finance Approval.") % rec.name
                users_to_notify = group_finance.user_ids
            elif rec.state == 'done':
                message = _("Your PPE Deduction No. %s has been completed.") % rec.name
                users_to_notify = rec.requester_id

            if users_to_notify and message:
                model_id = self.env['ir.model']._get('ppe.deduction').id
                for user in users_to_notify:
                    existing = self.env['mail.activity'].search([
                        ('res_id', '=', rec.id),
                        ('res_model_id', '=', model_id),
                        ('user_id', '=', user.id),
                        ('summary', '=', message)
                    ])
                    if not existing:
                        rec.activity_schedule(
                            'mail.mail_activity_data_todo',
                            user_id=user.id,
                            note=message,
                            summary=message
                        )


class PPEDeductionLine(models.Model):
    _name = 'ppe.deduction.line'
    _description = 'PPE Deduction Line'

    deduction_id = fields.Many2one('ppe.deduction')
    ppe_type = fields.Many2one('product.product', string='Type of PPE', required=True)
    brand_sn = fields.Char(string="Brand or S/N", related='ppe_type.brand')
    quantity = fields.Float(string='Quantity', default=1.0)
    price = fields.Float(string='Price', digits='Price')
    last_data = fields.Date(string='Last Distribution Date', compute='_compute_last_distribution', store=True)

    @api.depends('ppe_type', 'deduction_id.employee_id')
    def _compute_last_distribution(self):
        for line in self:
            last_date = False
            # نأخذ الموظف من الرأس (deduction_id.employee_id) والمنتج من السطر الحالي
            if line.deduction_id.employee_id and line.ppe_type:
                last_receipt_line = self.env['ppe.receipt.line'].search([
                    ('employee_id', '=', line.deduction_id.employee_id.id),
                    ('ppe_type', '=', line.ppe_type.id),
                    ('receipt_id.state', '=', 'done')
                ], order='create_date desc', limit=1)
                
                if last_receipt_line:
                    last_date = last_receipt_line.receipt_id.date
            
            line.last_data = last_date

    @api.onchange('ppe_type')
    def _onchange_ppe_type(self):
        if self.ppe_type:
            self.price = self.ppe_type.standard_price