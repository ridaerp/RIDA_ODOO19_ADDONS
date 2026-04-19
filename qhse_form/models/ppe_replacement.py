from odoo import models, fields, api, _
from odoo.exceptions import  UserError


class PPEReplacement(models.Model):
    _name = 'ppe.replacement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'PPE Replacement Document'
    _order = 'name desc'

    name = fields.Char(string='Document Number', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))


    def unlink(self):
        if self.state != 'draft':
            raise UserError("You cannot delete this Blasting Work Permit. Only DRAFT records can be deleted.")
        return super(PPEReplacement, self).unlink()

    name = fields.Char(string='Document Number', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('ppe.replacement') or ' '

        return super(PPEReplacement, self).create(vals)

    doc_no = fields.Char(string="Doc. No.", default="UMC-QHSE-QP-PPE-02", readonly=True)

    requester_id = fields.Many2one('res.users', string='Requester / مقدم الطلب', default=lambda self: self.env.user)
    department_id = fields.Many2one('hr.department', string='القسم / Department',
                                    default=lambda self: self.env.user.employee_id.department_id)
    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        default=lambda self: self.env.company,
        required=True
    )

    line_supervisor_id = fields.Many2one('res.users', string='Line Supervisor',ondelete='set null')
    position_id = fields.Many2one('hr.job', string="Position Title", related='line_supervisor_id.employee_id.job_id',readonly=True,store=True)

    date = fields.Date(string='Date', default=fields.Date.today())
    ppe_line_ids = fields.One2many('ppe.replacement.line', 'replacement_id', string='Details of Damaged PPE')

    # قسم مبررات الطلب (Reasons & Justification)
    justification = fields.Text(string='Reasons & Justification')

    # قسم خاص بإدارة QHSE فقط
    last_distribution_date = fields.Date(string='Last Distribution Date')
    damage_reason = fields.Selection([
        ('intention', 'Intention'),
        ('expired', 'Expired'),
        ('miss_use', 'Miss Use'),
        ('lost', 'Lost'),
        ('negligence', 'Negligence'),
        ('poor_qu', 'Poor Quality'),
        ('others', 'Others')
    ], string='Reason of Damage')
    other = fields.Text(string='Others')

    damage_percentage = fields.Float(string='Percentage of Damage')
    safety_effect = fields.Text(string='Effect of damaged PPE to employee safety')
    recommendation = fields.Text(string='Recommendation')

    responsible_safety_officer_id = fields.Many2one('res.users', string='Responsible Safety Officer')
    qhse_manager_approval = fields.Many2one('res.users', string='QHSE Manager Approval')
    qhse_comment = fields.Text(string='QHSE Manager Comment')
    date_approval = fields.Date(string='Approval Date', default=fields.Date.today())
    state = fields.Selection([
        ('draft', 'Draft'),
        ('wlm_approve', 'Waiting Line Manager'),
        ('officer', 'Safety Officer Review'),
        ('manager', 'Manager Approval'),
        ('done', 'Approved')
    ], default='draft', string='Status', tracking=True)
    reason_reject = fields.Text(string='Reject Reason', tracking=True)
    deduction_count = fields.Integer(compute='_compute_deduction_count')
    receipt_count = fields.Integer(compute='_compute_receipt_count')

    @api.onchange('requester_id')
    def _onchange_requester_id_get_manager(self):
        """ جلب المدير المباشر الخاص بمقدم الطلب من ملف المستخدم """
        for rec in self:
            if rec.requester_id and rec.requester_id.line_manager_id:
                # نأخذ الموظف المرتبط بالمدير المباشر لمقدم الطلب
                rec.line_supervisor_id = rec.requester_id.line_manager_id.id
            else:
                rec.line_supervisor_id = False

    def _compute_receipt_count(self):
        for rec in self:
            rec.receipt_count = self.env['ppe.receipt'].search_count([('name', 'ilike', rec.name)])

    def action_view_receipts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('PPE Receipts'),
            'res_model': 'ppe.receipt',
            'view_mode': 'list,form',
            # البحث في الإيصالات التي تشير إلى هذا المستند في حقل 'other'
            'domain': [('other', 'ilike', self.name)], 
        }

    def make_ppe_receipt_function(self):
        for rec in self:
            if not rec.ppe_line_ids:
                continue

            # تم حذف 'employee_id' من هنا لأنه غير موجود في موديل ppe.receipt
            receipt_vals = {
                'date': fields.Date.today(),
                'reason_type': 'damage_replacement',
                'other': _("Replacement for document: %s") % rec.name,
                'state': 'draft',
                'confirm_training': True,
                'company_id': rec.company_id.id,
            }

            # إنشاء الرأس أولاً
            receipt_rec = self.env['ppe.receipt'].create(receipt_vals)

            receipt_lines = []
            for line in rec.ppe_line_ids:
                # نستخدم الكمية المعتمدة، وإذا كانت 0 نستخدم الكمية المطلوبة
                qty = line.qty_approved if line.qty_approved > 0 else line.quantity
                
                # هنا نضع الموظف في السطر (لأن الحقل موجود في ppe.receipt.line)
                receipt_lines.append((0, 0, {
                    'employee_id': line.employee_id.id, 
                    'ppe_type': line.ppe_type.id,
                    'quantity': qty,
                    'qty_approved': qty,
                    'receipt_id': receipt_rec.id,
                }))

            if receipt_lines:
                receipt_rec.write({'receipt_line_ids': receipt_lines})

        return True

    def _compute_deduction_count(self):
        for rec in self:
            # البحث عن الاستقطاع المرتبط برقم هذا المستند
            rec.deduction_count = self.env['ppe.deduction'].search_count([('justification', 'ilike', rec.name)])

    def action_view_deductions(self):
        """ دالة فتح طلبات الاستقطاع المرتبطة """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Deduction Requests'),
            'res_model': 'ppe.deduction',
            'view_mode': 'list,form',
            'domain': [('justification', 'ilike', self.name)],
            'context': {'default_employee_id': self.ppe_line_ids.employee_id.id},
        }

    def make_deduction_request_function(self):
        for rec in self:
            deduction_reasons = ['intention', 'miss_use', 'negligence', 'others']

            if rec.damage_reason in deduction_reasons:
                lines = []
                for line in rec.ppe_line_ids:
                    # الاعتماد على الكمية المعتمدة في الاستقطاع أيضاً
                    qty = line.qty_approved if line.qty_approved > 0 else line.quantity
                    
                    lines.append((0, 0, {
                        'ppe_type': line.ppe_type.id,
                        'quantity': qty,
                    }))

                if not lines:
                    continue

                deduction_vals = {
                    'employee_id': rec.ppe_line_ids.employee_id.id,
                    'requester_id': rec.env.user.id, # المستخدم الحالي (المدير المعمد)
                    'date': fields.Date.today(),
                    'deduction_reason': rec.damage_reason,
                    'justification': _("Auto-generated from Replacement: %s") % rec.name,
                    'ppe_line_ids': lines,
                    'authorization_confirm': 'True',
                    'state': 'officer',
                }
                deduction_rec = self.env['ppe.deduction'].create(deduction_vals)
                rec.message_post(body=_("System created a Deduction Request: <b>%s</b>") % deduction_rec.name)

    def action_ln(self):
        for rec in self:
            rec.state = 'wlm_approve'

    def action_officer(self):
        for rec in self:
            line_manager = rec.requester_id.line_manager_id

            if not line_manager:
                raise UserError(
                    _("The requester does not have a Line Manager assigned in their profile. Please contact HR."))
            if line_manager.id != self.env.user.id:
                raise UserError(
                    _("Sorry, only the Line Manager (%s) is authorized to approve this document.") % line_manager.name)
            rec.write({
                'state': 'officer',
            })
            rec.action_update_activities()


    def action_manager(self):
        for rec in self:
            rec.write({
                'state': 'manager',
                'responsible_safety_officer_id': self.env.user.id,
            })
            rec.action_update_activities()

    def action_done(self):
        for rec in self:
            rec.write({
                'state': 'done',
                'qhse_manager_approval': self.env.user.id,
                'date_approval': fields.Date.context_today(self)
            })

            # استدعاء الدوال الجديدة
            rec.make_ppe_receipt_function() # بدلاً من issuance
            rec.make_deduction_request_function()
            rec.action_update_activities()

    def action_update_activities(self):
        for rec in self:
            # 1. جلب مجموعات الصلاحيات الخاصة بمسؤولي السلامة
            group_officer = self.env.ref('base_rida.rida_group_safety_officer')
            group_senior = self.env.ref('base_rida.rida_group_senior_officer')
            group_manager = self.env.ref('base_rida.rida_group_qhse_manager')

            to_notify = []
            requester_user = rec.requester_id

            if rec.state == 'officer':
                message = f"New replacement No. {rec.name} is awaiting Safety Officer review."
                for user in group_officer.user_ids:
                    to_notify.append({'user': user, 'note': message})

            
            # حالة: انتظار اعتماد المدير
            elif rec.state == 'manager':
                message = f"Request No. {rec.name} is awaiting QHSE Manager approval."
                for user in group_manager.user_ids:
                    to_notify.append({'user': user, 'note': message})

            elif rec.state == 'done':
                message = f"Your request No. {rec.name} has been officially approved."
                if requester_user:
                    to_notify.append({'user': requester_user, 'note': message})

            model_id = self.env['ir.model']._get('ppe.replacement').id

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


class PPEReplacementLine(models.Model):
    _name = 'ppe.replacement.line'
    _description = 'PPE Replacement Line'

    replacement_id = fields.Many2one('ppe.replacement')
    ppe_type = fields.Many2one('product.product', string='Type of PPE', required=True)
    brand_sn = fields.Char(string="Brand or S/N", related='ppe_type.brand')
    quantity = fields.Float(string='Quantity', default=1.0)
    employee_id = fields.Many2one('hr.employee', string="Employee Name")
    job_id = fields.Many2one('hr.job', string="Position Title", related='employee_id.job_id', readonly=True)
    emp_code = fields.Char(readonly=True, string="Staff No", store=True, related='employee_id.emp_code')
    emp_department_id = fields.Many2one(related="employee_id.department_id", string="Department/Section")
    qty_approved = fields.Float(string='Quantity Approved')
    last_data = fields.Date(string='Last Distribution date', compute='_compute_last_distribution', store=True)
    qty_hand = fields.Float(string='Quantity On Hand', compute='_compute_qty_hand', store=False)

    @api.depends('ppe_type')
    def _compute_qty_hand(self):
        for line in self:
            if line.ppe_type:
                line.qty_hand = line.ppe_type.qty_available
            else:
                line.qty_hand = 0.0

    @api.depends('employee_id', 'ppe_type')
    def _compute_last_distribution(self):
        for line in self:
            last_date = False
            if line.employee_id and line.ppe_type:
                # البحث عن آخر إيصال مستلم لهذا الموظف وهذا المنتج تحديداً
                last_receipt_line = self.env['ppe.receipt.line'].search([
                    ('employee_id', '=', line.employee_id.id),
                    ('ppe_type', '=', line.ppe_type.id),
                    ('receipt_id.state', '=', 'done') # فقط الإيصالات المعتمدة
                ], order='create_date desc', limit=1)
                
                if last_receipt_line:
                    last_date = last_receipt_line.receipt_id.date
            
            line.last_data = last_date