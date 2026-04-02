from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PPEReceipt(models.Model):
    _name = 'ppe.receipt'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'PPE Receipt Document'
    _order = 'name desc'

    # =========================
    # CRUD
    # =========================
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("You can only delete draft records."))
        return super().unlink()

    
    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('ppe.receipt') or ' '

        return super(PPEReceipt, self).create(val)


    # =========================
    # Fields
    # =========================
    name = fields.Char(string='Permit Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    doc_no = fields.Char(string="Doc. No.", default="UMC-QHSE-QP-PPE/06", readonly=True)
    date = fields.Date(string="Date", default=fields.Date.context_today)

    requester_id = fields.Many2one('res.users', string='Requester', default=lambda self: self.env.user)
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        default=lambda self: self.env.user.employee_id.department_id
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )

    receipt_line_ids = fields.One2many('ppe.receipt.line', 'receipt_id', string='Details')

    reason_type = fields.Selection([
        ('new_employee', 'New Employee'),
        ('annual_quota', 'Annual Quota'),
        ('damage_replacement', 'Damage Replacement'),
        ('jsa', 'JSA'),
        ('others', 'Others')
    ], string='Reason')
    other = fields.Text(string='Others')

    confirm_training = fields.Boolean(string='Confirmed Training', required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('officer', 'Safety Officer'),
        ('senior', 'Senior EX'),
        ('done', 'Approved'),
        ('reject', 'Rejected'),
    ], default='draft', tracking=True)

    reason_reject = fields.Text(string='Reject Reason', tracking=True)

    officer_user_id = fields.Many2one('res.users', readonly=True)
    senior_user_id = fields.Many2one('res.users', readonly=True)
    done_user_id = fields.Many2one('res.users', readonly=True)

    date_of_safety = fields.Date()
    date_senior = fields.Date()

    issuance_count = fields.Integer(compute='_compute_issuance_count')
    deduction_count = fields.Integer(compute='_compute_deduction_count')

    # =========================
    # Compute
    # =========================
    def _compute_deduction_count(self):
        for rec in self:
            rec.deduction_count = self.env['ppe.deduction'].search_count([
                ('justification', 'ilike', rec.name)
            ])

    def _compute_issuance_count(self):
        for rec in self:
            rec.issuance_count = self.env['issuance.request'].search_count([
                ('origin', '=', rec.name)
            ])

    # =========================
    # Actions
    # =========================
    def action_view_deductions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Deduction Requests'),
            'res_model': 'ppe.deduction',
            'view_mode': 'list,form',
            'domain': [('justification', 'ilike', self.name)],
        }

    def action_view_issuance_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Issuance Requests'),
            'res_model': 'issuance.request',
            'view_mode': 'list,form',
            'domain': [('origin', '=', self.name)],
        }

    # =========================
    # Business Logic
    # =========================
    def make_issuance_request_function(self):
        for rec in self:
            if not rec.receipt_line_ids:
                raise UserError(_("Please add PPE items first."))

            existing = self.env['issuance.request'].search([
                ('origin', '=', rec.name)
            ], limit=1)
            if existing:
                continue

            issuance = self.env['issuance.request'].create({
                'title': _("PPE Receipt: %s") % rec.name,
                'origin': rec.name,
                'company_id': rec.company_id.id,
                'requested_by': rec.senior_user_id.id or self.env.user.id,
                'issuance_type': 'internal_issuance',
                'request_date': fields.Date.today(),
            })

            product_map = {}

            for line in rec.receipt_line_ids:
                if not line.qty_approved:
                    continue

                product_id = line.ppe_type.id

                if product_id not in product_map:
                    product_map[product_id] = {
                        'product_id': product_id,
                        'product_uom_id': line.ppe_type.uom_id.id,
                        'qty_requested': 0,
                        'name': rec.name,
                    }

                product_map[product_id]['qty_requested'] += line.qty_approved

            issuance_lines = [
                (0, 0, vals)
                for vals in product_map.values()
            ]

            if issuance_lines:
                issuance.write({'line_ids': issuance_lines})

    def make_deduction_request_function(self):
        for rec in self:

            existing = self.env['ppe.deduction'].search([
                ('justification', 'ilike', rec.name)
            ], limit=1)
            if existing:
                continue

            employee_lines_map = {}

            for line in rec.receipt_line_ids:

                if line.damage_reason not in ['intention', 'miss_use', 'negligence', 'others']:
                    continue

                if not line.employee_id:
                    continue

                emp = line.employee_id

                if emp.id not in employee_lines_map:
                    employee_lines_map[emp.id] = []

                qty = line.qty_approved or line.quantity

                employee_lines_map[emp.id].append((0, 0, {
                    'ppe_type': line.ppe_type.id,
                    'quantity': qty,
                }))

            if not employee_lines_map:
                continue

            for emp_id, lines in employee_lines_map.items():

                deduction = self.env['ppe.deduction'].create({
                    'employee_id': emp_id,
                    'requester_id': self.env.user.id,
                    'date': fields.Date.today(),
                    'deduction_reason': 'others',  # ممكن تطوره لاحقاً
                    'justification': _("Auto-generated from PPE Receipt: %s") % rec.name,
                    'ppe_line_ids': lines,
                    'authorization_confirm': True,
                    'state': 'officer',
                })

                rec.message_post(
                    body=_("Deduction created for %s: <b>%s</b>") % (
                        deduction.employee_id.name,
                        deduction.name
                    )
                )

    # =========================
    # Workflow
    # =========================
    def action_officer(self):
        for rec in self:
            if not rec.confirm_training:
                raise UserError(
                    "يجب عليك الموافقة على صحة البيانات وإرشادات السلامة قبل إرسال الطلب! / You must confirm that all information is correct before submitting.")
            rec.write({
                'state': 'officer',
                'done_user_id': self.env.user.id,
            })
            rec._update_activities()

    def action_senior(self):
        for rec in self:
            rec.write({
                'state': 'senior',
                'officer_user_id': self.env.user.id,
                'date_of_safety': fields.Date.today(),
            })
            rec._update_activities()

    def action_done(self):
        for rec in self:
            rec.write({
                'state': 'done',
                'senior_user_id': self.env.user.id,
                'date_senior': fields.Date.today(),
            })
            rec.make_issuance_request_function()
            rec.make_deduction_request_function()
            rec._update_activities()

    # =========================
    # Activities
    # =========================
    def _update_activities(self):
        for rec in self:
            users = self.env['res.users']
            message = ""

            if rec.state == 'officer':
                group = self.env.ref('base_rida.rida_group_safety_officer', False)
                users = group.user_ids if group else users
                message = _("Waiting Safety Officer approval: %s") % rec.name

            elif rec.state == 'senior':
                group = self.env.ref('base_rida.rida_group_senior_officer', False)
                users = group.user_ids if group else users
                message = _("Waiting Senior approval: %s") % rec.name

            elif rec.state == 'done':
                users = rec.requester_id
                message = _("Approved: %s") % rec.name

            for user in users:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    summary=message,
                    note=message
                )


# =========================================
# LINES
# =========================================
class PPEReceiptLine(models.Model):
    _name = 'ppe.receipt.line'
    _description = 'PPE Receipt Line'

    receipt_id = fields.Many2one('ppe.receipt')
    ppe_type = fields.Many2one('product.product', required=True)

    quantity = fields.Float(default=1.0)
    qty_approved = fields.Float(default=1.0)

    employee_id = fields.Many2one('hr.employee')
    emp_code = fields.Char(related='employee_id.emp_code', store=True)
    brand_sn = fields.Char(string="Brand or S/N", related='ppe_type.brand')
    unit = fields.Char(string='Unit', related='ppe_type.uom_id.name')
    size = fields.Char(string='Size/Specification')
    color = fields.Char(string='Color')
    other = fields.Text(string='Other Damage Reason')

    damage_reason = fields.Selection([
        ('intention', 'Intention'),
        ('expired', 'Expired'),
        ('miss_use', 'Miss Use'),
        ('lost', 'Lost'),
        ('negligence', 'Negligence'),
        ('poor_qu', 'Poor Quality'),
        ('others', 'Others')
    ])
    last_distributed_date = fields.Date(
    string='Last Issuance Date',
    compute='_compute_last_issuance',
    store=False
)

    last_distributed_qty = fields.Float(
    string='Last Issuance Qty',
    compute='_compute_last_issuance',
    store=False
    )

    qty_hand = fields.Float(compute='_compute_qty_hand')

    @api.depends('ppe_type')
    def _compute_qty_hand(self):
        for rec in self:
            rec.qty_hand = rec.ppe_type.qty_available if rec.ppe_type else 0

    @api.depends('ppe_type')
    def _compute_last_issuance(self):
        for line in self:
            line.last_distributed_date = False
            line.last_distributed_qty = 0.0

            if not line.ppe_type:
                continue

            # البحث عن آخر طلب صرف لهذا المنتج
            last_line = self.env['issuance.request.line'].search([
                ('product_id', '=', line.ppe_type.id),
                ('request_id.state', '=', 'done')  # أو approved حسب النظام
            ], order='create_date desc', limit=1)

            if last_line:
                line.last_distributed_qty = last_line.qty_requested
                line.last_distributed_date = last_line.request_id.request_date