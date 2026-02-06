from odoo import fields, models, api
from odoo.exceptions import UserError


class MedicareIssuanceRequest(models.Model):
    _name = 'medicare.issuance.request'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True,
                             readonly=True)
    date = fields.Date(default=fields.Date.today(), string='Request Date')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Cost Center')
    age = fields.Integer(string="Age", compute='_compute_fields')
    doctor_visitor_id = fields.Many2one('doctor.visit', string="Clinic Visit")
    lab_id = fields.Many2one('lab.request', string="Lab Request")
    minor_id = fields.Many2one('minor.room', string="Minor Request")
    product_ids = fields.One2many(comodel_name="medicare.issuance.request.line", inverse_name="request_id",
                                  string="Products", copy=1)
    type_product = fields.Selection(
        [('pharmacy', 'pharmacy'), ('minor_room', 'minor_room'),
         ('lab', 'lab')],
        string='type of product')
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done'),
         ('reject', 'Rejected')],
        string='Status', default='draft', track_visibility='onchange', copy=False)
    type = fields.Selection(string="Type Of Patient",
                            selection=[('employee', 'Employee'), ('contractor', 'Contractor'), ('quest', 'Guest'), ],
                            default='employee', required=1)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    p_contractor = fields.Many2one('patient.contractors', string="Patient")
    p_employee = fields.Many2one('hr.employee', string="Patient")
    p_quest = fields.Many2one('patient.quset', string="Patient")
    patient = fields.Char(string="Patient")
    description = fields.Text('Description')
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")

    def action_correct_ticket(self):
        x = self.env['medicare.issuance.request.line'].search([])
        for rec in x:
            rec.price = rec.product_id.price

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(MedicareIssuanceRequest, self).unlink()

    @api.onchange('type')
    def _onchange_type(self):
        self.p_contractor = False
        self.p_employee = False
        self.p_quest = False
        self.patient = False
        self.account_analytic_id = False

    @api.depends("p_employee", "p_contractor", "p_quest")
    def _compute_fields(self):
        for rec in self:
            if rec.p_employee:
                if rec.p_employee.company_id:
                    rec.company_id = rec.p_employee.company_id.id
                rec.age = rec.p_employee.age
            elif rec.p_contractor:
                rec.age = rec.p_contractor.age
                if rec.p_contractor.department_id.sudo().analytic_account_id:
                    rec.account_analytic_id = rec.p_contractor.department_id.sudo().analytic_account_id
                else:
                    rec.account_analytic_id = False
            elif rec.p_quest:
                rec.age = rec.p_quest.age
            else:
                rec.age = 0

    @api.onchange('p_employee', 'p_contractor', 'p_quest')
    def _onchange_employee(self):
        for rec in self:
            if rec.p_employee.sudo().contract_id:
                rec.account_analytic_id = rec.p_employee.sudo().contract_id.sudo().analytic_account_id
            else:
                rec.account_analytic_id = False
            if rec.p_employee:
                rec.patient = rec.p_employee.name
            if rec.p_contractor:
                rec.patient = rec.p_contractor.name
                if rec.p_contractor.department_id.sudo().analytic_account_id:
                    rec.account_analytic_id = rec.p_contractor.department_id.sudo().analytic_account_id
                else:
                    rec.account_analytic_id = False
            if rec.p_quest:
                rec.patient = rec.p_quest.name

    def action_draft(self):
        return self.write({'state': 'draft'})

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_code_by('med.issuance.request') or ' '

        return super(MedicareIssuanceRequest, self).create(vals)

    def set_approve(self):
        for rec in self.product_ids:
            if rec.qty:
                rec.product_id.qty -= rec.qty
        self.state = 'done'


class MedicareIssuanceRequestLine(models.Model):
    _name = 'medicare.issuance.request.line'

    product_id = fields.Many2one('product.medicare', string='Product')
    default_code = fields.Char('Item Code', related='product_id.default_code')
    description = fields.Text(
        'Description', related='product_id.description')
    qty_available = fields.Float("Available Qty", compute='get_qty_available')
    qty = fields.Float(
        'Quantity')
    total_price = fields.Float(compute='get_qty_available')
    price = fields.Float()
    uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure', related='product_id.uom_id')
    request_id = fields.Many2one("medicare.issuance.request")

    @api.constrains('price')
    def _check_price(self):
        for rec in self:
            if rec.price != rec.product_id.price:
                raise UserError(f"You cann't change price for product [ {rec.product_id.name} ]")

    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id and self.product_id.price:
            self.price = self.product_id.price

    @api.depends('product_id', 'qty', 'price')
    def get_qty_available(self):
        for rec in self:
            if rec.price:
                rec.total_price = rec.price * rec.qty
            else:
                rec.total_price = 0
            rec.qty_available = rec.product_id.qty

    @api.constrains('qty')
    def _constrains_qty(self):
        for rec in self:
            if rec.qty > rec.qty_available:
                raise UserError("The Requested Quantity Must be Equal or smaller than available QTY")
