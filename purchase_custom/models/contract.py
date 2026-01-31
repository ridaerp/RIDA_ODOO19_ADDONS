from email.policy import default
from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class Contract(models.Model):
    _name = 'contract.contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'External Service Management'

    name = fields.Char('Reference', required=True, index=True, copy=False, default='New')
    requested_by = fields.Many2one('res.users', 'Requested by', track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True, readonly=True)
    date = fields.Date(string='Issue date', default=datetime.today())
    eff_date = fields.Date(string='Effective date', default=datetime.today())
    department_id = fields.Many2one('hr.department', string='Department',
                                    default=lambda self: self._get_default_department())
    vendor_id = fields.Many2one(comodel_name='res.partner', string='Contractor', )
    buyer_assigned = fields.Many2one(comodel_name='res.users', string='Buyer Assigned', )
    contract_number = fields.Char(string='Title')
    job_description = fields.Text(string='Job Description')
    estimated_cost = fields.Float(string='Contract Amount', related='work_ids.estimated_cost')
    duration = fields.Char(string='Contract Duration', compute='compute_contract_duration')
    start_date = fields.Date(string='Signed Date')
    finish_date = fields.Date(string='Expiry date')
    state = fields.Selection(string='Status', selection=[('draft', 'Draft'),
                                                         ('contract_send', 'Contract Send'),
                                                         ('contract_specialist', 'Contract Specialist'),
                                                         ('supply_chain_manager', 'Supply Chain Manager'),
                                                         ('general_manager', 'Grneral Manager'),
                                                         ('running', 'Running'),
                                                         ('reject', 'Rejected')], default='draft')
    inherit_po = fields.Many2one(comodel_name='purchase.order')
    attatchment = fields.Binary(string='Attatchment')
    work_ids = fields.One2many(comodel_name='contract.contract.lines', inverse_name='work_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, )
    pr_type = fields.Selection(string='Pr type', selection=[('material', 'Material'), ('service', 'Service'), ],
                               default='service')
    source_document = fields.Char(string='Source Document')
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.company)
    invoice_count = fields.Integer(string="Count", compute='compute_invoice_count')
    store_invoice = fields.Many2one(comodel_name='account.move')
    # original_contract_sum = fields.Monetary(string='Original contract sum')
    this_claim = fields.Float(string='This clame')
    address = fields.Char(string='Address')
    fax_number = fields.Integer(string='Fax number')
    telephone_number = fields.Char(string='Telephone No.')
    email = fields.Char(string='Email')
    # clicked = fields.Boolean(string='', default=False)
    # inherit_logistic = fields.Many2one(comodel_name='logistics.logistics')
    # rida new fields
    location_type = fields.Char('Location Type')
    project_no = fields.Integer(string='Project No')
    project_description = fields.Text(string='Project Description')
    company_signatory = fields.Char(string='Company Signatory')
    company_signatory_title = fields.Char(string='Company Signatory Title',
                                          default=lambda self: self.env.user.company_id.name)
    contract_amount = fields.Integer(string='Contract Values')
    contract_type = fields.Selection(string='Type of contract', selection=[('opex', 'OPEX')
        , ('capex', 'CAPEX')
        , ('capex', 'CAPEX')
        , ('reveny', 'Reveny share')
        , ('draft', 'Under Drafting')
                                                                           ], )
    contract_level = fields.Selection(string='Contract Level', selection=[('corporate', 'Corporate'),
                                                                          ('operation', 'Operation')], readonly=True,
                                      compute='get_contract_level')
    t_c = fields.Text(string='Contract  Conditions')
    t_c_attatchment = fields.Binary(string='Contract Conditions Attatchment')
    scope_work = fields.Text('Scope of work')
    scope_doc = fields.Binary()
    remarks = fields.Text('Remarks And Notes')
    signature = fields.Image('Signature', copy=False, attachment=True, max_width=1024, max_height=1024)
    signed_by = fields.Char('Signed By', help='Name of the person that signed the contract.', copy=False)
    signed_on = fields.Datetime('Signed On', help='Date of the signature.', copy=False)

    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Terms', check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    contract_count = fields.Integer(string='Contract Count', compute='compute_contract_count')
    contract_status = fields.Char(string='Contract State', compute='_get_contract_state')
    store_contract = fields.Many2one(comodel_name='change.contract')
    payment_count = fields.Integer(string='Payment Count', compute='compute_payment_count')
    store_payment = fields.Many2one(comodel_name='payment.request')

    @api.constrains('start_date', 'finish_date')
    def _check_dates(self):
        for date in self:
            if date.finish_date < date.start_date:
                raise ValidationError('The finishing date cannot be earlier than the starting date .')

    def compute_contract_duration(self):
        self.duration = self.finish_date - self.start_date

    def compute_invoice_count(self):
        self.ensure_one()
        self.invoice_count = self.env['account.move'].search_count([('wo_account_id', '=', self.id)])

    @api.depends('contract_amount')
    def get_contract_level(self):
        self.ensure_one()
        if self.contract_amount < self.company_id.maximum_contract_amount:
            self.contract_level = 'operation'
        else:
            self.contract_level = 'corporate'

    def button_create_invoice(self):
        # self.clicked = True
        create_invoice = {
            'partner_id': self.vendor_id,
            'wo_account_id': self.id,
            'move_type': 'in_invoice',
            'payment_reference': self.name,
            # 'original_contract_sum': self.original_contract_sum,
            'this_claim': self.this_claim,
            'address': self.address,
            'fax_number': self.fax_number,
            'telephone_number': self.telephone_number,
            'email': self.email,

        }
        invoice = self.env['account.move'].create(create_invoice)
        self.store_invoice = invoice.id

        for line in self.work_ids:
            vals = []
            vals.append((0, 0, {
                'quantity': line.quantity,
                'product_id': line.product_id.id,
                # 'analytic_account_id': line.analytic_account_account,
                'price_subtotal': line.total,
                'price_unit': line.estimated_cost,
                'account_id': line.account_id,
                'name': 'name',
            }))
            invoice.update({'invoice_line_ids': vals})
            # self.store_invoice = invoice.id
        return self.action_view_invoice()

    def action_view_invoice(self):
        return {
            'name': "Bills",
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('wo_account_id', '=', self.id)],
        }

    # Rida workflow
    def button_contract_submit(self):
        for rec in self:
            rec.write({'state': 'contract_send'})

    def button_contract_send(self):
        for rec in self:
            rec.write({'state': 'contract_specialist'})

    def button_contract_specialist(self):
        for rec in self:
            rec.write({'state': 'supply_chain_manager'})

    def button_supply_chain_manager(self):
        for rec in self:
            rec.write({'state': 'general_manager'})

    def button_general_manager_approve(self):
        for rec in self:
            rec.write({'state': 'running'})

    def get_requested_by(self):
        user = self.env.user.id
        return user

    def _get_default_department(self):
        return self.env.user.department_id.id if self.env.user.department_id else False

    def action_reject(self):
        self.write({'state': 'reject'})

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('Contract.sequence') or _('/')
        result = super(Contract, self).create(vals)
        return result

    def button_change_contract(self):
        view_id = self.env.ref('purchase_custom.change_contract_view_form')
        create_change_contract = {
            'vendor_id': self.vendor_id.id,
            # 'contract_value': self.contract_value,
            # 'contract_refrence': self.contract_refrence,
            # 'scope_work': self.scope_work,
            # 'terms_doc': self.terms_doc,
            # 'remarks': self.remarks,
            # 'terms': self.terms,
            'contract_status': self.contract_status,
            'scope_work': self.scope_work,
            'scope_doc': self.scope_doc,
            'remarks': self.remarks,
            'start_date': self.start_date,
            'end_date': self.finish_date,
            'contract_duration': self.duration,
            # 'portion_of_agreement_affected': self.portion_of_agreement_affected,
            'contracts': self.id,
        }
        for line in self.work_ids:
            lines = [(0, 0, {
                # 'name': line.name,
                'product_id': line.product_id.id,
                # 'product_uom_qty': line.product_uom_qty,
                'quantity': line.quantity,
                'rate': line.rate,
                # 'price_subtotal': line.price_subtotal,
                'unit_price': line.unit_price,
            })]
        create_change_contract.update({'contract_ids': lines})
        ctr = self.env['change.contract'].create(create_change_contract)
        self.store_contract = ctr
        return self.action_view_contracts()

    def action_view_contracts(self):
        return {
            'name': "Change in Contracts",
            'type': 'ir.actions.act_window',
            'res_model': 'change.contract',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('contracts', '=', self.id)],
        }

    def button_payment_request(self):
        view_id = self.env.ref('purchase_custom.payment_request_view_form')
        create_payment_request = {
            'vendor_id': self.vendor_id.id,
            'contract_number': self.id,
            'date': self.start_date,
            # 'end_date': self.finish_date,
            # 'contract_duration': self.duration,

        }

        payment = self.env['payment.request'].create(create_payment_request)
        self.store_payment = payment
        return self.action_view_payments_requests()

    def action_view_payments_requests(self):
        return {
            'name': "Payments Requests",
            'type': 'ir.actions.act_window',
            'res_model': 'payment.request',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('contract_number', '=', self.id)],
        }

    def compute_contract_count(self):
        self.ensure_one()
        self.contract_count = self.env['change.contract'].search_count(
            [('inherit_po', '=', self.id)])

    def compute_payment_count(self):
        self.ensure_one()
        self.payment_count = self.env['payment.request'].search_count(
            [('contract_number', '=', self.id)])

    def _get_contract_state(self):
        self.ensure_one()
        self.contract_status = self.state


class ContractLine(models.Model):
    _name = 'contract.contract.lines'

    work_id = fields.Many2one(comodel_name='contract.contract')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity', required=True)
    unit_price = fields.Monetary(string='Price subtotal')
    total = fields.Monetary(string='Total')
    currency_id = fields.Many2one(comodel_name='res.currency',
                                  default=lambda self: self.env.user.company_id.currency_id.id, )
    estimated_cost = fields.Float('Estimated Cost', )
    account_id = fields.Many2one(comodel_name='account.move', string="Account")
    analytic_account_account = fields.Many2one('account.analytic.account', string='Cost center', readonly=True)
    rate = fields.Integer(string='Rate')


class Company(models.Model):
    _inherit = 'res.company'
    current_location = fields.Many2one(comodel_name='stock.location', string='Current Location', store=True)
    new_location = fields.Many2one(comodel_name='stock.location', string='New Location', store=True)
    collection_point = fields.Many2one(comodel_name='stock.location', string='Collection point', store=True)
    delivery_point = fields.Many2one(comodel_name='stock.location', string='Delivery point', store=True)
    # rida configuration field
    maximum_contract_amount = fields.Integer(string='maximum contract amount', store='True')


class ESMConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    maximum_contract_amount = fields.Integer(related='company_id.maximum_contract_amount',
                                             string='maximum contract amount', readonly=False)
