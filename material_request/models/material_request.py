# -*- coding: utf-8 -*-
# Copyright 2016 Eficent Business and IT Consulting Services S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl-3.0).
from email.policy import default
from docutils.nodes import field
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta

_STATES = [
    ('draft', 'Draft'),
    ('line_line_approve', 'Waiting  Line Manager Approval'),
    ('line_approve', 'Waiting Department Manager Approval'),
    ('warehouse_sup', 'Waiting Warehouse Supervisor Approval'),
    ('site_approve', 'Waiting Operation Director  Approval'),
    ('fleet_director_approve', 'Waiting Fleet Director  Approval'),
    ('store_approve', 'Waiting Warehouse Manager Approval'),
    ('supply_approve', 'Waiting Procurement Manager Processing'),
    ('supply_service_approve', 'Waiting Contract Manager Processing'),
    ('purchase_approve', 'Purchase user'),
    ('reject', 'Rejected'),
    ('cancel', 'Cancelled'),
    # comment by ekhlas ('done', 'Done'),
    ################## change string by ekhlas ##########
    ('done', 'RFQ Sourcing'),
    ('w_te', 'Waiting Tehc-Eval'),
    ('w_ce', 'Waiting Comm-Eval'),
    ########################## ekhlas code##################
    ('waiting_po', 'Wating PO Confirm'),
    ('purchased', 'Purchase Order'),
    ('delivered', 'Delivered'),
    ('part_deliverd', 'Partially Delivered'),
    ('invoiced', 'Waiting Payment'),
    ('paid', 'Paid'),
    ('to_delivery', 'To Deliver'),
    # ('done', 'Procurement Officer'),
    # ('purchase', 'Purchase Order'),
    ('close', 'Closed'),
]


class OverseasPaymentWizard(models.TransientModel):
    _name = 'overseas.payment.wizard'
    _description = 'Overseas Payment Wizard'
    amount_to_pay = fields.Float(string='Amount to Pay', required=True)



    def confirm_payment(self):
        active_id = self.env.context.get('active_id')
        purchase_order = self.env['purchase.order'].browse(active_id)
        if not purchase_order:
            raise UserError("No Purchase Order found.")


        if purchase_order.request_id.purchase_type != 'overseas' and purchase_order.purchase_type !='overseas':
            raise UserError("This purchase is not marked as Overseas.")

        # existing_payment = self.env['overseas.payment'].search(
        #     [('purchase_order_id', '=', purchase_order.id)], limit=1)
        # if existing_payment :
        #     raise UserError("The Overseas Payment is already created.")
        if self.amount_to_pay >purchase_order.amount_total:
            raise UserError("you cannot pay the amount greater than PO total.")


        overseas_payment = self.env['overseas.payment'].create({
            'title': purchase_order.request_id.title,
            'request_id': purchase_order.request_id.id,
            'purchase_order_id': purchase_order.id,
            'purchase_order': purchase_order.name,
            'amount_to_pay': self.amount_to_pay,
            'amount_total': purchase_order.amount_total,
            # 'department_id': purchase_order.department_id.id,
            # 'contract_id': purchase_order.contract_id.id,
            # 'material_request_id': purchase_order.request_id.id,
        })

        purchase_order.ovearseas_id.state = 'scd'
        

class PaymentRequest(models.Model):
    _name='overseas.payment'
    _description = 'Overseas Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'


    name = fields.Char('Ovs-Pay No.', required=False, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    date_start = fields.Date('Request Date', help="Date when the user initiated the request.",
                             default=fields.Date.context_today, track_visibility='onchange')
    title = fields.Char()
    note = fields.Text()
    reason_reject = fields.Text("Rejection Reason", track_visibility="onchange")

    state = fields.Selection([('draft', 'Draft'),
        ('scd', 'Waiting Supply Chain Director'),
        ('fm', 'Waiting Finance Director'),
        ('ceo', 'Waiting CEO Approval'),
        ('reject', 'Rejected'),
        ('cancel', 'Cancelled'),            
        ('close', 'Waiting Payment'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ], string='Status', index=True, track_visibility='onchange', readonly=True,
                             required=True, copy=False, default='draft')


    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id)

    amount_total = fields.Monetary('Total')
    amount_to_pay = fields.Monetary('Amount to be Pay')
    amount_due = fields.Monetary('Amount Due', compute='_compute_amount_due', store=True)

    purchase_order=fields.Char("Purchase Order No.")
    purchase_order_id=fields.Many2one("purchase.order","Purchase Order No.")
    request_id=fields.Many2one("material.request","MR/SR No.")
    partner_id=fields.Many2one(related="purchase_order_id.partner_id",string="Supplier")


    scd_date=fields.Datetime("SCD Approval Date",readonly=True)
    ceo_date=fields.Datetime("CEO Approval Date",readonly=True)
    fm_date=fields.Datetime("Finance Manager Approval Date",readonly=True)
    scd_approved_by = fields.Many2one('res.users', 'Supply Chain Director', track_visibility='onchange'
                                   , store=True, readonly=True)
    ceo_approved_by = fields.Many2one('res.users', 'CEO', track_visibility='onchange'
                                   , store=True, readonly=True)
    fm_approved_by = fields.Many2one('res.users', 'Finance Manager', track_visibility='onchange'
                                   , store=True, readonly=True)
    
    computed_payment_status = fields.Char(compute='_compute_payment_status', store=True)

    is_contract=fields.Boolean("Is Overseas Contract Payment")
    contract_id=fields.Many2one("purchase.contract","Purchase Contract")
    department_id=fields.Many2one("hr.department","Department")
    material_request_id=fields.Many2one("material.request","Material Request MR/SR")
    payment_company_id = fields.Many2one(
        "res.company",
        string="Paying Subsidiary",
    )
    company_id = fields.Many2one('res.company',"Company")

    # Journal entry created in the paying Subsidiary
    subsidiary_payment_id = fields.Many2one('account.payment', string="Subsidiary Payment Entry")
    subsidiary_payment_move_id = fields.Many2one('account.move', string="Subsidiary Journal Entry")

    # Journal entry created in the company (PO owner)
    company_move_id = fields.Many2one('account.move', string="Company Intercompany Entry")
    register_payment = fields.Boolean(default=False)
    sub_journal_id = fields.Many2one('account.journal', string='Journal')

    intercompany_misc_journal_id = fields.Many2one(
        'account.journal', 
        string="Intercompany Misc Journal",
    )

    is_subsidery_user = fields.Boolean(
        string=" Subsidiary User",
        compute="_compute_is_subsidiary_user",
        store=False
    )



    def create_subsidiary_payment(self):
        for rec in self:
            if not rec.sub_journal_id:
                raise UserError("You must enter Journal to register the payment")

            create_payment = {
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': self.company_id.partner_id.id,
                'company_id': self.payment_company_id.id,
                'amount': self.amount_total,
                'currency_id': rec.currency_id.id,
                'ref':str(self.name+self.partner_id.name),
                'journal_id': rec.sub_journal_id.id,
                'ovearseas_id':rec.id,
            }
            payment = self.env['account.payment'].create(create_payment)
            rec.subsidiary_payment_id = payment.id
            rec.subsidiary_payment_move_id = payment.move_id.id
            rec.register_payment = True
            payment.action_post()


            rec.state = "paid"

            # 🚀 trigger system-level job
            rec._trigger_intercompany_creation()
            return payment


    def _trigger_intercompany_creation(self):
        """System trigger – no user permissions required"""
        for rec in self:
            if not rec.is_contract:
                continue
            if rec.company_move_id:
                continue

            # run as system user + force company
            rec.with_company(rec.company_id.id).sudo()._create_intercompany_entry()


    def _create_intercompany_entry(self):
        self.ensure_one()

        if not self.is_contract:
            return

        company = self.company_id          # PO owner
        paying_company = self.payment_company_id
        partner = self.partner_id

        po_ic_account = paying_company.partner_id.property_account_payable_id
        if not po_ic_account:
            raise UserError(
                f"Set intercompany receivable on {paying_company.name}"
            )

        journal = self.intercompany_misc_journal_id or self.env['account.journal'].search([
            ('company_id', '=', company.id),
            ('type', '=', 'general')
        ], limit=1)

        move_vals = {
            'company_id': company.id,
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': f'Intercompany Payment {self.name}',
            'line_ids': [
                (0, 0, {
                    'account_id': partner.property_account_payable_id.id,
                    'partner_id': partner.id,
                    'debit': self.amount_total,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': po_ic_account.id,
                    'partner_id': paying_company.partner_id.id,
                    'debit': 0.0,
                    'credit': self.amount_total,
                }),
            ]
        }

        move = self.env['account.move'].create(move_vals)
        move.action_post()
        self.company_move_id = move.id
      

    # def create_intercompany_payment(self):
    #     self.ensure_one()

    #     if self.is_contract ==True and self.state =='close':

    #         company = self.company_id  # PO company (Umdurman Mining)
    #         paying_company = self.payment_company_id  # Subsidiary (Rohax)
    #         partner = self.partner_id

    #         # -------------------
    #         # Intercompany Accounts & Journal from Company
    #         # -------------------
    #         po_ic_account = paying_company.partner_id.property_account_receivable_id
    #         if not po_ic_account:
    #             raise UserError(f"Please set Intercompany Receivable account on {company.name}")

    #         po_journal = self.env['account.journal'].search([
    #             ('company_id', '=', company.id),
    #             ('type', '=', 'general')
    #         ], limit=1)

    #         if not po_journal:
    #             raise UserError(f"No general journal found for {company.name}")
    #         if not self.intercompany_misc_journal_id:
    #             self.intercompany_misc_journal_id=po_journal

    #         # -------------------
    #         # Create journal entry in PO company
    #         # -------------------
    #         move_vals = {
    #             'journal_id': po_journal.id,
    #             'date': fields.Date.today(),
    #             'ref': f'Intercompany Payment {self.name}',
    #             'company_id': company.id,
    #             'line_ids': [
    #                 # Debit: Supplier account in PO company
    #                 (0, 0, {
    #                     'account_id': partner.property_account_payable_id.id,
    #                     'partner_id': partner.id,
    #                     'debit': self.amount_to_pay,
    #                     'credit': 0.0,
    #                     'name': f'Intercompany payment to {company.name}',
    #                     'currency_id': self.currency_id.id,
    #                     'amount_currency': self.amount_to_pay,
    #                 }),
    #                 # Credit: Intercompany Receivable (from paying company)
    #                 (0, 0, {
    #                     'account_id': po_ic_account.id,
    #                     'partner_id': paying_company.partner_id.id,
    #                     'debit': 0.0,
    #                     'credit': self.amount_to_pay,
    #                     'name': f'Intercompany payment from {paying_company.name}',
    #                     'currency_id': self.currency_id.id,
    #                     'amount_currency': -self.amount_to_pay,
    #                 }),
    #             ]
    #         }
    #         move = self.env['account.move'].create(move_vals)
    #         move.action_post()
    #         self.company_move_id = move.id



 


    @api.depends('purchase_order_id.invoice_ids.payment_state')
    def _compute_payment_status(self):
        for rec in self:
            rec.check_payment_status()



    @api.depends()
    def _compute_is_subsidiary_user(self):
        for rec in self:
            rec.is_subsidery_user = (
                self.env.user.user_type == 'rohax'
            )


    @api.model
    def _get_default_name(self):
        return self.env['ir.sequence'].next_by_code('paymentrequest.sequence')

    @api.depends('amount_total', 'amount_to_pay')
    def _compute_amount_due(self):
        for record in self:
            record.amount_due = record.amount_total - record.amount_to_pay


    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Only draft records can be deleted!")
        return super(PaymentRequest, self).unlink()



    @api.model
    def create(self, vals):

        s_seq = self.env['ir.sequence'].next_by_code('paymentrequest.sequence')
        vals['name'] = s_seq
        request = super(PaymentRequest, self).create(vals)
        return request


    def fm(self):
        for rec in self:
            rec.fm_date=datetime.today()
            rec.fm_approved_by=rec.env.user.id

            return rec.write({'state': 'ceo'})

    def  ceo(self):
        for rec in self:
            rec.ceo_date=datetime.today()
            rec.ceo_approved_by=rec.env.user.id

            return rec.write({'state': 'close'})



    def scd(self):
        for rec in self:
            rec.scd_date=datetime.today()
            rec.scd_approved_by=rec.env.user.id

            return rec.write({'state': 'fm'})


    def contract_manager(self):
        for rec in self:
            rec.scd_date=datetime.today()
            rec.scd_approved_by=rec.env.user.id

            return rec.write({'state': 'scd'})




    def check_payment_status(self):

        for rec in self:    

            po = rec.purchase_order_id
            invoices = po.invoice_ids.filtered(
                lambda inv: inv.move_type == 'in_invoice' and inv.state == 'posted'
            )
            payment_states = set(inv.payment_state for inv in invoices)

            if payment_states == {'paid'}:
                rec.state = 'paid'
            elif payment_states =={'partial'} and  rec.state=='close':

                rec.state = 'paid'

            else:
                print ("")








    def button_payment(self):
        return {
            'name': _('Payment'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('ovearseas_id', '=', self.id)],
        }







class MaterialRequest(models.Model):
    _name = 'material.request'
    _description = 'Material Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _rec_name = 'name'
    # _order = 'name desc'
    _order = 'date_start desc'

    def _default_analytic_account_id(self):
        if self.env.user.default_analytic_account_id.id:
            return self.env.user.default_analytic_account_id.id


    ##############comment by ekhlas
    # name = fields.Char(compute='get_name', default='NEW',index=True)
    ########################### un comment by ekhlas ##################################
    name = fields.Char('MR Number', required=False, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    equipment_id = fields.Many2one(comodel_name="maintenance.equipment", string="Equipment", required=False, )
    date_start = fields.Date('Request Date', help="Date when the user initiated the request.",
                             default=fields.Date.context_today, track_visibility='onchange')
    end_start = fields.Date('End date', default=fields.Date.context_today, track_visibility='onchange')
    schedule_date = fields.Date('Expected date',track_visibility='onchange')
    requested_by = fields.Many2one('res.users', 'Requested by', track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True, readonly=True)
    assigned_to = fields.Many2one('res.users', 'Approver', track_visibility='onchange')
    assigned_to_supply = fields.Many2one('res.users', 'Assign To', track_visibility='onchange' , domain= lambda self: [("groups_id", "=", self.env.ref("material_request.group_buyers").id)] )
    
    ##########################add by ekhlas #######################
    assigned_date=fields.Datetime("Date of assigned",readonly=True)

    description = fields.Html('Description')
    title = fields.Char()
    line_ids = fields.One2many('material.request.line', 'request_id', 'Products to Purchase', readonly=False, copy=True,
                               track_visibility='onchange')
    state = fields.Selection(selection=_STATES, string='Status', index=True, track_visibility='onchange', readonly=True,
                             required=True, copy=False, default='draft')
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', domain=[('code', '=', 'internal')])
    issuance_count = fields.Integer(string="Count", compute='compute_issuance_count')
    service_count = fields.Integer(string="Count", compute='compute_picking_count')
    agreement_count = fields.Integer(string="Count", compute='compute_agreement_count')
    purchase_count = fields.Integer(string="Count", compute='compute_purchase_count')
    po_count = fields.Integer(string="Count", compute='compute_po_count')
    ############################################ekhlas code #############################
    ########################################add contract ################################
    contract_count = fields.Integer(string="Count", compute='compute_contract_count')
    #########################################################################################
    item_type = fields.Selection([('material', 'Material'), ('service', 'Service')], default="material",
                                 string='Item Type')
    categ_id = fields.Many2one('product.category', string="Category", required=1)
    department_id = fields.Many2one('hr.department', string='Department',
                                    default=lambda self: self._get_default_department())
    section = fields.Many2one('hr.department', string='Section')
    # , default=lambda self: self._get_default_section())
    branch_id = fields.Char('res.branch', )
    # default=lambda self: self._get_default_branch())
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account",default=_default_analytic_account_id, required=True)
    # default=lambda self: self._get_default_analytic_account())
    is_editable = fields.Boolean(string="Is editable", compute="_compute_is_editable", readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id)
    amount_total = fields.Monetary('Total', compute='compute_totals', store=True)
    subtotal = fields.Monetary('SubTotal', compute='compute_totals', store=True)
    amount_total_purchase = fields.Monetary('Purchase Total', compute="compute_totals", store=True)
    priority = fields.Selection([('normal', 'Normal'), ('urgent', 'Urgent'), ('Critical', 'Critical')],
                                string='Priority', required=False, default='normal')
    reason_reject = fields.Text("Rejection Reason", track_visibility="onchange")
    line_manager_user_id = fields.Many2one('res.users', "Line Manager", copy=False)
    stock_user_id = fields.Many2one('res.users', "Stock Manager", copy=False)
    finance_user_id = fields.Many2one('res.users', "Finance Manager", copy=False)
    # emails = fields.Char(compute='compute_approval_emails', store=True)
    edit_analytic_account = fields.Boolean(compute='compute_edit_cost_center')
    line_manager_id = fields.Many2one('res.users', string="Line Manager", related="requested_by.line_manager_id")
    line_line_manager_id = fields.Many2one('res.users', string="Line Manager", related="requested_by.line_line_manager_id")
    # Special Dates
    inventory_check_date = fields.Date()
    lm_approval_date = fields.Date("LM Approval Date")
    emp = fields.Many2one('hr.employee', track_visibility='onchange', default=lambda self: self.env.user.employee_id,
                          store=True, readonly=True)

    emp_type = fields.Selection(string='Employee type', related="emp.rida_employee_type")
    attachment = fields.Binary('Attachment')

    # nus
    source_type = fields.Selection(string='Source Type',
                                   selection=[('single', 'Single Source'), ('multiple', 'Multiple Sources'), ])

    requester_description = fields.Text(string='Description')
    check_user = fields.Boolean('Check', compute='get_user')

    # Fleet fields eliam (
    eq_fleet = fields.Many2one('model.equipment',"Equipment")
    code = fields.Char(string='Code', related='eq_fleet.code')
    brand = fields.Char('Brand', related='eq_fleet.brand')
    model = fields.Char('Model', related='eq_fleet.model')
    year = fields.Integer('Year', related='eq_fleet.year')
    plate = fields.Char('Plate', related='eq_fleet.plate')
    is_fleet = fields.Boolean('Is Fleet')
    fleet = fields.Boolean(related='requested_by.fleet')
    type = fields.Char('Type', related='eq_fleet.type')
    category = fields.Selection(string='Category' ,related='eq_fleet.category')
    vin = fields.Char('VIN.#',related='eq_fleet.vin')
    engine = fields.Char('Engine model',related='eq_fleet.engine')
    engine_serial = fields.Char('Engine serial No',related='eq_fleet.engine_serial')

    product_id = fields.Many2one('product.product', related='line_ids.product_id', string='Product', readonly=False)


    approve_by = fields.Many2one('res.users', 'Approve by', track_visibility='onchange'
                                   , store=True, readonly=True)

    user_type=fields.Selection(related="requested_by.user_type",string="Type")
    scm_approved_by = fields.Many2one('res.users', 'Purchase Manager', track_visibility='onchange'
                                   , store=True, readonly=True)
    
    #
    # analytic_tag_ids = fields.Char(
    #     "account.analytic.tag", string="Analytic Tags", tracking=True
    # )
    weight_score_count = fields.Integer(string="Count", compute='compute_weight_score_count')
    lowest_price_count = fields.Integer(string="Count", compute='compute_lowest_price_count')
    purchase_type = fields.Selection(
        [('local', 'Local Payment'), ('overseas', 'Overseas Payment')],
        string="Purchase Payment",
        required=True,
        default='local'
    )

    # main_po_id = fields.Many2one("purchase.order", string="Selected Purchase Order", readonly=True)
    is_selected = fields.Boolean(related='x_studio_purchase_order.is_selected', string="Is Select", readonly=True)
    # STATE_LABELS = {
    #     ('draft', 'RFQ'),
    #     ('sent', 'RFQ Sent'),
    #     ('prm', 'Waiting Purchase Manager Approval'),
    #     ('sum', 'Waiting Procurement Manager Approval'),
    #     ('sud', 'Waiting Supply Chain Director Approval'),
    #     ('contract_manager', 'Waiting Contract Manager Approval'),
    #     ('ccso', 'CCSO Approval'),
    #     ('fleet_director', 'Fleet Director Approval'),
    #     ('fm', 'Finance Manager Approval'),
    #     ('weight', 'Grading and Analysis'),
    #     ('site', 'Operation Director Approval'),
    #     ('line_approve', 'Waiting Line Manager Approval'),
    #     ('service_done', 'Service Completed'),
    #     # ('approve', 'Approved'),
    #     # ('to approve', 'To Approve'),
    #     ('purchase', 'Purchase Order'),
    #     ('done', 'Locked'),
    #     ('reject', 'Rejected'),
    #     ('cancel', 'Cancelled')
    # }

    # @api.onchange('x_studio_purchase_order')
    # def _onchange_po_state(self):
    #     for rec in self:
    #         selected_po = rec.x_studio_purchase_order.filtered(lambda po: po.is_selected)
    #         if selected_po:
    #             rec.main_po_state = selected_po[0].state
    #         else:
    #             rec.main_po_state = False

    mai_po_state = fields.Char(string="Purchase Status", compute="_compute_purchase_status", store=True)

    @api.depends("x_studio_purchase_order.state")
    def _compute_purchase_status(self):
        for rec in self:
            if rec.x_studio_purchase_order:
                states = rec.mapped("x_studio_purchase_order.state")
                labels = []
                for state in states:

                    field = rec.x_studio_purchase_order._fields['state']
                    selection = dict(field.selection)
                    labels.append(selection.get(state, state))
                rec.mai_po_state = ", ".join(sorted(set(labels)))
            else:
                rec.mai_po_state = "No Purchase Orders"





    def compute_weight_score_count(self):
        self.weight_score_count = self.env['weight.scoring.evaluation'].search_count(
            [('material_request_id.id', '=', self.id)])

    def compute_lowest_price_count(self):
        self.lowest_price_count = self.env['lowest.price.evaluation'].search_count(
            [('material_request_id.id', '=', self.id)])

    def set_weight_score(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Weighted Scoring Evaluation',
            'view_mode': 'tree,form',
            'res_model': 'weight.scoring.evaluation',
            'domain': [('material_request_id.id', '=', self.id)],
            'context': "{'create': False}"
        }

    def set_lowest_price(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lowest Price Evaluation',
            'view_mode': 'tree,form',
            'res_model': 'lowest.price.evaluation',
            'domain': [('material_request_id.id', '=', self.id)],
            'context': "{'create': False}"
        }

  # ('id', 'in', [c.id for c in user.analytic_account_ids])

    # def _search_no(self,operator,value):
    #     if operator=='like':
    #         operator=='like'
    #     return [('name',operator,value)]




    #
    # def get_equip(self):
    #     eq = self.env['model.equipment'].search([])
    #

    def action_open_evaluation_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'evaluation.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_material_request_id': self.id,  # Pass the current material request ID
            },
        }

    def get_user(self):
        if self.requested_by.id == self.env.user.id:
            self.check_user = True
        else:
            self.check_user = False

    # @api.depends('branch_id', 'section', 'department_id')
    # def get_line_manager(self):
    #     if self.branch_id:
    #         self.line_manager_id = self.branch_id.manager_id.user_id
    #     elif self.section:
    #         self.line_manager_id = self.section.manager_id.user_id
    #     elif self.department_id:
    #         self.line_manager_id = self.department_id.manager_id.user_id

    def _get_default_department(self):
        return self.env.user.department_id.id if self.env.user.department_id else False





    def _get_default_section(self):
        return self.env.user.section.id if self.env.user.section else False

    def _get_default_branch(self):
        return self.env.user.branch_id.id if self.env.user.branch_id else False

    def get_requested_by(self):
        user = self.env.user.id
        return user

    @api.depends('requested_by')
    def compute_edit_cost_center(self):
        self.edit_analytic_account = self.env.user.has_group('base_op.group_edit_cost_center')

    # Workflow
    def check_product(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Please add material lines!")

    # user submit
    def button_to_department_manger(self):
        for rec in self:

            if self.analytic_account_id.company_id  and self.analytic_account_id.company_id != self.company_id:
                raise UserError('the Cost Center Incompatible for the Company')
            ############################################ekhlas code##################
            ######################add equipment #####################################
            if rec.requested_by.user_type=='fleet':
                eq_fleet=self.env['model.equipment'].search([('analytic_account_id','=',rec.analytic_account_id.id)],limit=1)
                rec.eq_fleet=eq_fleet


            # if self.env.user.has_group('base.group_system'):
            #     return
            # else:
            if not self.requested_by.id == self.env.user.id:
                raise UserError('Sorry, Only requester can submit this document!')
            line_manager = False
            line_line_manager = False
            try:
                line_manager = self.requested_by.line_manager_id
                line_line_manager = self.requested_by.line_line_manager_id
            except:
                line_manager = False
                line_line_manager = False
            if not line_manager:
                raise UserError("Line manger is not set!")

            # if rec.requested_by.user_type=='hq':
                # if not rec.requested_by.line_line_manager_id:
                #     rec.write({'state': 'line_line_approve'})
                #     print ("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
                # elif rec.requested_by.line_manager_id!=rec.requested_by.line_line_manager_id:
                #     rec.write({'state': 'line_approve'})
                # else:
                #     rec.write({'state': 'line_line_approve'})
            # else:


            rec.write({'state': 'line_line_approve'})
            self.activity_update_line_manager()
            rec.check_product()




    def activity_update_line_manager(self):
        for rec in self:
            message = ""
            if rec.state == 'line_line_approve':
                # Get the line manager of the current user
                line_manager = rec.requested_by.line_manager_id if rec.requested_by.line_manager_id else None
                if line_manager:
                    message = " for Ugrent and Kindly Approval"
                    self.activity_schedule('master_data.mail_act_master_data_approval', user_id=line_manager.id, note=message)
            else:
                continue





    # manager to line
    def button_to_line_manager(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                rec.write({'approve_by': rec.env.user.id})
                pass

            else:
                rec.write({'approve_by': rec.env.user.id})
                self.ensure_one()
                line_managers = []
                today = fields.Date.today()
                line_manager = False
                try:
                    line_manager = self.requested_by.line_manager_id
                except:
                    line_manager = False
                # comment by ekhlas
                #if not line_manager or not self.user_has_groups('material_request.group_department_manager'):
                #     raise UserError("Sorry. Your are not authorized to approve this document!")
                if not line_manager or line_manager !=rec.env.user :
                    raise UserError("Sorry. Your are not authorized to approve this document!")

                rec.write({'state': 'line_line_approve'})




    # manager to warehouse
    def button_to_warehouse_supervisor(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                rec.write({'approve_by': rec.env.user.id})
                pass

            else:
                rec.write({'approve_by': rec.env.user.id})
                self.ensure_one()
                line_managers = []
                today = fields.Date.today()
                line_manager = False
                line_line_manager = False
                try:
                    line_manager = self.requested_by.line_manager_id
                    line_line_manager = self.requested_by.line_line_manager_id


                    print ("##############",line_line_manager)


                    # to be change if line_line_manager and rec.state=='line_approve':
                    #     # if not line_line_manager or line_line_manager !=rec.env.user :
                    #     #     raise UserError("Sorry. Your are not authorized to approve this document!")

 

                except:
                    line_manager_id = False
                    line_line_manager_id = False
                # comment by ekhlas
                #if not line_manager or not self.user_has_groups('material_request.group_department_manager'):
                #     raise UserError("Sorry. Your are not authorized to approve this document!")



                if line_manager !=rec.env.user and not line_line_manager  :
                    raise UserError("Sorry. Your are not authorized to approve this document!")


                elif line_line_manager:
                    if line_line_manager !=rec.env.user :
                        raise UserError("Sorry..... Your are not authorized to approve this document!")
 

               
            #################################comment by ekhlas################3
            # if rec.emp_type == 'site' and rec.item_type == 'service':
            

            ###############comment by ekhlas code when thiqip became site manager 2023-augest

            if rec.requested_by.user_type == 'site' and rec.item_type == 'service':
                 return rec.write({'state': 'site_approve'})



            #################################add by ekhlas (fleet director )################3
            if rec.requested_by.user_type == 'fleet' and rec.item_type == 'service':
                 return rec.write({'state': 'fleet_director_approve'})

            # if rec.item_type == 'service' and rec.requested_by.user_type=='hq':
            if rec.item_type == 'service':
                 # return rec.write({'state': 'supply_approve'})
                 return rec.write({'state': 'supply_service_approve'})
            #################################comment by ekhlas################3
            # elif rec.emp_type == 'site' and rec.item_type == 'material':

            if rec.requested_by.user_type == 'fleet' and rec.item_type == 'material':
                return rec.write({'state': 'warehouse_sup'})

            #################################add by ekhlas(fleet)################3
            if rec.requested_by.user_type == 'site' and rec.item_type == 'material':
                return rec.write({'state': 'warehouse_sup'})

            else:
                return rec.write({'state': 'supply_approve'})

    # warehouse approve
    def warehouse_supervisor_approve(self):
        for rec in self:
            if rec.requested_by.user_type == 'fleet' and rec.item_type == 'material':
                return rec.write({'state': 'fleet_director_approve'})
            else:
                return rec.write({'state': 'store_approve'})
                # return rec.write({'state': 'site_approve'})


    # def delivered(self):
    #     for rec in self:
    #         rec.issuance_count >0:
    #         issuance_obj=self.env['issuance.request'].search_count([])
    #         return self.write({'state': 'delivered'})


    def activity_update_tehincal_evaluation(self):
        """Send activity to requester, line manager, assigned_to_supply, and additional evaluator"""
        for rec in self:
            if rec.state != 'w_te':
                continue
            # Get the technical evaluation record linked to this MR
            evaluation = self.env['weight.scoring.evaluation'].search([('material_request_id', '=', rec.id)], limit=1)
            if not evaluation:
                continue


            users_to_notify = []

            # Add the requester
            if rec.requested_by:
                users_to_notify.append(rec.requested_by)

            # Add their line manager if defined and different from requester
            if rec.requested_by.line_manager_id:
                users_to_notify.append(rec.requested_by.line_manager_id)

          
            # Include additional evaluator if defined
            if hasattr(rec, 'additional_evaluator') and rec.additional_evaluator and rec.additional_evaluator not in users_to_notify:
                users_to_notify.append(rec.additional_evaluator)

            # Send activity to all target users
            message = "The Technical Evaluation is waiting for your action."
            for user in users_to_notify:
                evaluation.activity_schedule(
                    'material_request.mail_act_material_request_approval',
                    user_id=user.id,
                    note=message
                )

 

    def activity_update(self):
        for rec in self:
            users = []
            # rec.activity_unlink(['hr_salary_advance.mail_act_approval'])
            # if rec.state not in ['draft','reject']:
            #     continue
            message = ""
            if rec.state == 'supply_approve' or rec.state=='supply_service_approve':
                # users = self.env.ref('base_rida.rida_group_master_data_manager').users
                message = "The MR has been Assign To you "
                # for user in users:
                self.activity_schedule('material_request.mail_act_material_request_approval', user_id=rec.assigned_to_supply.id, note=message)
            else:
                continue



    # Warehouse create Issuance
    def make_issuance_request_function(self):
        env = self.env(user=1)
        view_id = self.env.ref('material_request.view_issuance_request_form')
        for order in self:
            if not order.analytic_account_id:
                raise UserError("Please add Analytic account")
            order_line = []
            create_issuance = {
                'title': order.title,
                'state': 'to_inventory',
                'request_id': order.id,
                'origin': order.name,
                #comment by ekhas 'state': order.name,
                'company_id': order.company_id.id,
                'requested_by':order.requested_by.id,
                'analytic_account_id':order.analytic_account_id.id,
                'issuance_type': 'internal_issuance',

            }

            issuance = self.env['issuance.request'].create(create_issuance)

            for line in self.line_ids:
                product = line.product_id
                account_analytic_id = self.analytic_account_id.id if self.analytic_account_id else False
                vals = [(0, 0, {'product_id': line.product_id.id,
                                'product_uom_id': line.product_id.uom_po_id.id,
                                'qty_requested': line.product_qty,
                                'analytic_account_id': line.analytic_account_id.id,
                                'name': line.name,
                                })]
                # create_issuance.append(product_line)
                issuance.update({'line_ids': vals})

    def make_issuance_request(self):
        self.make_issuance_request_function()
        self.button_close()
        return self.action_view_issuance()

    # sit to warehouse approve
    def button_to_warehouse_manager(self):
        for rec in self:
            rec.write({
                'state': 'warehouse_sup',
            })

    # warehouse to supply
    def button_to_supply_approve(self):
        for rec in self:
            ####################comment by ekhlas
            # rec.make_issuance_request_function()
            if rec.item_type=='service' and rec.requested_by.user_type=='hq':
                return rec.write({'state': 'supply_service_approve'})
            else:

                return rec.write({'state': 'supply_approve'})

    # supply to purchase approve
    def button_to_purchase_approve(self):
        for rec in self:
            # rec.make_issuance_request_function()
            ##################### add line by ekhlas ######

            if rec.item_type=='material':
                rec.make_issuance_request_function()

            if not rec.assigned_to_supply:
                raise UserError("Please Assign Purchase User !")

            self.activity_update()

            rec.write({'state': 'done',
                        'assigned_date':datetime.today(),
                        'scm_approved_by':rec.env.user.id
                       })




    # supply to purchase approve (contract only)
    def button_to_purchase_contract_approve(self):
        for rec in self:
            # rec.make_issuance_request_function()
            ##################### add line by ekhlas ######

            if rec.item_type=='material':
                rec.make_issuance_request_function()
            
            if not rec.assigned_to_supply:
                raise UserError("Please Assign Contract  Specialist !")

            self.activity_update()

            rec.write({'state': 'done',
                        'assigned_date':datetime.today(),
                        'scm_approved_by':rec.env.user.id

                       })




    @api.depends('line_ids.unit_price')
    def compute_totals(self):
        for rec in self:
            rec.ensure_one()
            total = subtotal =purchase_total = 0.0
            for line in rec.line_ids:
                line.subtotal = line.unit_price * line.product_qty
                total += line.unit_price * line.product_qty
                purchase_total += line.unit_price * line.qty_purchase
        self.update({
            'amount_total': total,
            'amount_total_purchase': purchase_total
        })

    @api.onchange('categ_id')
    def onchage_categ_id(self):
        if self.categ_id and self.line_ids:
            raise UserError("You cannot change request category after you added "
                            "the request lines. Please remove the lines and try again!")

    @api.onchange('item_type')
    def onchage_type(self):
        self.categ_id = False
    @api.onchange('equipment_id')
    def onchage_equi(self):
        if self.equipment_id.analytic_account_id.id:
           self.analytic_account_id = self.equipment_id.analytic_account_id.id

    @api.model
    def get_default_requested_by(self):
        user = self.env.user.id
        return user

    @api.model
    def _get_default_name(self):
        return self.env['ir.sequence'].next_by_code('material_request.sequence')

    @api.model
    def create(self, vals):
        # seq = self.env['ir.sequence'].next_by_code('material_request.sequence') or "/"
        if vals['item_type'] == 'material':
            ##################add lines by ekhlas ############################
            seq = self.env['ir.sequence'].next_by_code('material_request.sequence')
            vals['name'] = seq
        else:
            s_seq = self.env['ir.sequence'].next_by_code('sr_request.sequence')
            vals['name'] = s_seq
        ##############################if added by ekhlas ###########################


        request = super(MaterialRequest, self).create(vals)
        if vals.get('assigned_to'):
            request.message_subscribe(partner_ids=[request.assigned_to.partner_id.id])

        if request.requested_by.id != self.env.user.id:
            raise UserError("Sorry you cannot create a request with different user.")
        if not request.line_ids:
            raise UserError('Please add MR lines!')
        return request


    def get_name(self):
        for rec in self:
            if rec.item_type == 'material':
                rec.name = 'MR-000' + str(rec.id)
                    # raise UserError(rec.name)
            elif rec.item_type == 'service':
                rec.name = 'SR-000' + str(rec.id)




    @api.model
    def _get_default_picking_type(self):
        return self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            (
                'warehouse_id.company_id', 'in',
                [self.env.context.get('company_id', self.env.user.company_id.id), False])],
            limit=1).id

    def compute_agreement_count(self):
        self.agreement_count = self.env['purchase.requisition'].search_count([('request_ids', 'in', self.ids)])

    def compute_po_count(self):
        self.po_count = self.env['purchase.order'].search_count([('request_ids', 'in', self.ids)])

    def compute_purchase_count(self):
        self.purchase_count = self.env['purchase.order'].search_count([('request_ids', 'in', self.ids)])

    def compute_contract_count(self):
        self.contract_count = self.env['purchase.contract'].search_count([('request_id', '=', self.id)])


    def compute_issuance_count(self):
        self.issuance_count = self.env['issuance.request'].search_count([('request_id', '=', self.id)])

    def compute_picking_count(self):
        # self.picking_count = self.env['stock.picking'].search_count([('request_id', '=', self.id)])
        self.service_count = self.env['service.requisition'].sudo().search_count([('request_id', '=', self.id)])

    @api.depends('state')
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in ('to_approve', 'leader_approved', 'manager_approved', 'reject', 'done'):
                rec.is_editable = False
            else:
                rec.is_editable = True

    def write(self, vals):
        res = super(MaterialRequest, self).write(vals)
        for request in self:
            if vals.get('assigned_to'):
                self.message_subscribe(partner_ids=[request.assigned_to.partner_id.id])
        return res

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Only draft records can be deleted!")

        return super(MaterialRequest, self).unlink()

    def button_draft(self):
        self.mapped('line_ids').do_uncancel()
        return self.write({'state': 'draft'})


    def button_re_sourcing(self):
        return self.write({'state': 'done'})

    def button_site_approve(self):
        for rec in self:
            # comment by ekhlas
            # if rec.emp_type == 'site':

            ###################comment by thaqip comment when  he became site manager##########
            # if rec.requested_by.user_type == 'site':
            #     return rec.write({'state': 'site_approve'})

            ########################add fleet workflow(by ekhlas )##############
            if rec.requested_by.user_type == 'fleet':
                return rec.write({'state': 'fleet_director_approve'})
            # if rec.requested_by.user_type == 'hq':
            #     return rec.write({'state': 'supply_approve'})

            else:
                return rec.write({'state': 'site_approve'})

    def button_rejected(self):
        self.mapped('line_ids').do_cancel()
        return self.write({'state': 'reject'})





    def button_cancel(self):
        for request in self:
            # if  request.scm_approved_by and request.scm_approved_by.id!=request.env.user.id:
            #     if self.env.user.has_group('base.group_system'):
            #         pass
            #     else:
            #         raise UserError(_('Only Purchase Manager has processed  the request can cancel it'))

            orders = self.env['purchase.order'].search([('request_id', '=', request.id)])
            orders.button_cancel()
            pickings = self.env['stock.picking'].search([('request_id', '=', request.id)])
            pickings.action_cancel()
            pickings.unlink()
            request.state = 'cancel'
        # request.mapped('line_ids').do_cancel()

    def button_close(self):
        self.write({'state': 'close'})

    def action_view_purchase_order(self):
        return {
            'name': "RFQ/ Order",
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('request_ids', 'in', self.ids)],
        }

    def action_view_purchase_order_read(self):
        view_id = self.env.ref('material_request.purchase_orde_tree')
        return {
            'name': "RFQ/ Order",
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_id': view_id.id,
            'view_mode': 'tree',
            # 'view_type': 'form',
            'target': 'current',
            'domain': [('request_ids', 'in', self.ids), ('state', '!=', 'draft')],
        }


    def action_view_picking(self):
        return {
            'name': "Material Delivery",
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('request_id', '=', self.id)],
        }

    def action_view_service(self):
        return {
            'name': "Service Delivery",
            'type': 'ir.actions.act_window',
            'res_model': 'service.requisition',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('request_id', '=', self.id)],
        }

    def action_view_purchase_agreement(self):
        return {
            'name': "Purchase Agreement",
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.requisition',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('request_ids', 'in', self.ids)],
        }


    def action_view_contact(self):
        return {
            'name': "Purchase Contract",
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.contract',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('request_id', '=', self.id)],
        }



    def action_view_issuance(self):
        return {
            'name': "Issuance Request",
            'type': 'ir.actions.act_window',
            'res_model': 'issuance.request',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('request_id', '=', self.id)],
        }

    def action_stock_delivery(self):
        for order in self:
            if not order.line_ids:
                raise UserError(_('Please create Material Request lines.'))

            warehouse = self.env['stock.warehouse'].search([], limit=1)
            pickingType = self.env['stock.picking.type'].search(
                [('warehouse_id', '=', warehouse.id), ('code', '=', 'internal')], limit=1)
            location_id = self.env['stock.location'].search([('is_main_store', '=', True)], limit=1)
            location_dest_id = False

            if order.branch_id and order.categ_id.usage == "consumption":
                location_dest_id = order.branch_id.consumption_location_id
            elif order.branch_id and order.categ_id.usage == "sales":
                location_dest_id = order.branch_id.internal_location_id

            elif order.section and order.categ_id.usage == "consumption":
                location_dest_id = order.section.consumption_location_id
            elif order.section and order.section.usage == "sales":
                location_dest_id = order.section.internal_location_id

            elif order.department_id and order.categ_id.usage == "consumption":
                location_dest_id = order.department_id.consumption_location_id
            elif order.department_id and order.categ_id.usage == "sales":
                location_dest_id = order.branch_id.internal_location_id

            if not warehouse or not pickingType or not location_id or not location_dest_id:
                raise UserError("Stock locations are not properly set.")

            deliver_pick = {
                'picking_type_id': pickingType.id,
                'partner_id': False,
                'origin': self.name + '(' + str(self.priority) + ')',
                'request_id': self.id,
                'location_dest_id': location_dest_id.id,
                'location_id': location_id.id,
                'request_id': self.id,
                'analytic_account_id': self.analytic_account_id.id
            }

            purchase_pick = {
                'picking_type_id': pickingType.id,
                'partner_id': False,
                'origin': self.name + '(' + str(self.priority) + ')',
                'request_id': self.id,
                'location_dest_id': location_dest_id.id,
                'location_id': location_id.id,
                'request_id': self.id,
                'analytic_account_id': self.analytic_account_id.id
            }




    def check_auto_reject(self):
        """When all lines are cancelled the purchase request should be
        auto-rejected."""
        for pr in self:
            if not pr.line_ids.filtered(lambda l: l.cancelled is False):
                pr.write({'state': 'reject'})

    def action_open_add_to_rfq_wizard(self):

        wizard = self.env['add.to.rfq.wizard'].create({
            'material_request_id': self.id,
            'product_line_ids': [(0, 0, {
                'product_id': line.product_id.id,  # Ensure correct product.product ID
                'product_qty': line.product_qty,
                'qty_request': line.product_qty,
                'uom_id': line.product_uom_id.id,  # Use UOM from MR line
                'request_line_id': line.id
            }) for line in self.line_ids]
        })
        view_id = self.env.ref(
            'material_request.add_to_rfq_wizard_form').id  # Replace 'material_request' with your module name
        return {
            'name': _('Add to Existing RFQ'),
            'type': 'ir.actions.act_window',
            'res_model': 'add.to.rfq.wizard',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'res_id': wizard.id,  # Open the created wizard record
        }
    def action_open_add_to_tender_wizard(self):

        wizard = self.env['add.to.rfq.wizard'].create({
            'material_request_id': self.id,
            'product_line_ids': [(0, 0, {
                'product_id': line.product_id.id,  # Ensure correct product.product ID
                'product_qty': line.product_qty,
                'qty_request': line.product_qty,
                'uom_id': line.product_uom_id.id,  # Use UOM from MR line
                'request_line_id': line.id
            }) for line in self.line_ids]
        })
        view_id = self.env.ref(
            'material_request.add_to_tender_wizard_form').id  # Replace 'material_request' with your module name
        return {
            'name': _('Add to Existing Tender'),
            'type': 'ir.actions.act_window',
            'res_model': 'add.to.rfq.wizard',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'res_id': wizard.id,  # Open the created wizard record
        }

    def make_purchase_quotation(self):
        if self.env.user.has_group('base.group_system'):
            pass
        else:
            # commend by ekhlas code  if self.assigned_to_supply.id != self.env.user.id or not self.user_has_groups(
            #         'material_request.group_buyers'):
            if self.assigned_to_supply.id != self.env.user.id or not self.user_has_groups(
                    'material_request.group_buyers'):
                raise UserError("Sorry. Only assigned Buyers are authorized to create this document!")
        view_id = self.env.ref('purchase.purchase_order_form')
        order_line1 = []

        for line in self.line_ids:

            fpos = self.env['account.fiscal.position']
            if self.env.uid == SUPERUSER_ID:
                company_id = self.env.user.company_id.id
                taxes_id = fpos.map_tax(
                    line.product_id.supplier_taxes_id.filtered(lambda r: r.company_id.id == company_id))
            else:
                taxes_id = fpos.map_tax(line.product_id.supplier_taxes_id)

            ############################# added by ekhlas ########################3
            name = line.product_id.name

            ###############################add restrict when complete qty on MR######

            # if self.item_type=='service':
            #     print("###########################")
            #     if line.qty_in_po>=line.product_qty:
            #         raise UserError(_("A quote has been created for each quantity in the order"))



            if line.product_id.description_purchase:
                name += '\n' + line.product_id.description_purchase

            if line.product_id.description:
                name += '\n' + line.product_id.description
            ####################################################################

            # Determine analytic_distribution based on item_type
            analytic_distribution = False
            if self.purchase_type != 'overseas' and line.analytic_account_id:
                analytic_distribution = {line.analytic_account_id.id: 100}



            product_line = (0, 0, {'product_id': line.product_id.id,
                                   'state': 'draft',
                                   # 'analytic_distribution': {line.analytic_account_id.id: 100},
                                   # 'equ_id': self.equipment_id.id,
                                   'analytic_distribution': analytic_distribution,
                                   'product_uom': line.product_id.uom_po_id.id,
                                   'price_unit': 0,
                                   'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                   # 'taxes_id': ((6,0,[taxes_id.id])),
                                   'product_qty': line.product_qty,
                                   ########################comment by ekhlas
                                   # 'name': line.product_id.name,

                                   #########################################
                                   ########### add by ekhlas########33
                                   'name': name,
                                   'request_line_id': line.id
                                   })
            order_line1.append(product_line)


        return {
            'name': _('New Quotation'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_line': order_line1,
                'default_request_id': self.id,
                'default_request_ids': [self.id],
                'default_item_type': self.item_type,
                'default_priority1': self.priority,
                'default_eq_fleet': self.eq_fleet.id,
                'default_company_id': self.company_id.id,
                'default_purchase_type':self.purchase_type,

            }
        }



    def make_purchase_requisition(self):
        if self.env.user.has_group('base.group_system'):
            pass
        else:
            if self.assigned_to_supply.id != self.env.user.id or not self.user_has_groups(
                    'material_request.group_buyers'):
                raise UserError("Sorry. Only assigned Buyers are authorized to create this document!")
        view_id = self.env.ref('purchase_requisition.view_purchase_requisition_form')
        order_line = []
        type = self.env['purchase.requisition.type'].search([('exclusive', '=', 'exclusive')], limit=1)
        ######################add line by ekhlas code 
        # account_analytic_id = self.analytic_account_id.id if self.analytic_account_id else False
       
        for line in self.line_ids:
            product = line.product_id
            pick_in= self.env['stock.picking.type'].search(
                [('warehouse_id.company_id', '=', self.company_id.id), ('code', '=', 'incoming')],
                limit=1,)
            if self.env.uid == SUPERUSER_ID:
                company_id = self.env.user.company_id.id
            product_line1 = (0, 0, {'product_id': line.product_id.id,
                                   'product_uom_id': line.product_id.uom_po_id.id,
                                   'schedule_date': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                   'product_qty': line.product_qty,
                                   'qty_ordered': line.product_qty,
                                    'analytic_distribution': {line.analytic_account_id.id: 100}

                                    })
            order_line.append(product_line1)

        return {
            'name': _('New Purchase Agreement'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.requisition',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_line_ids': order_line,
                'default_request_id': self.id,
                'default_request_ids': [self.id],
                'request_id': self.id,
                'default_item_type': self.item_type,
                'default_type_id': type.id if type else False,
                'default_company_id': self.company_id.id,
                'default_picking_type_id': pick_in.id,
                'default_purchase_type':self.purchase_type


            }
        }


    ###################################ekhlas code ########################################
    ##########################add new contract in MR ########################################

    def make_contract_requisition(self):
        if self.env.user.has_group('base.group_system'):
            pass
        else:
            if self.assigned_to_supply.id != self.env.user.id or not self.user_has_groups(
                    'material_request.group_buyers'):
                raise UserError("Sorry. Only assigned Buyers are authorized to create this document!")
        view_id = self.env.ref('material_request.view_purchase_contract_custom_form1')
        order_line = []
        account_analytic_id = self.analytic_account_id.id if self.analytic_account_id else False
        type = self.env['purchase.requisition.type'].search([('exclusive', '=', 'exclusive')], limit=1)
        for line in self.line_ids:
            product = line.product_id
            # if self.env.uid == SUPERUSER_ID:
            #     company_id = self.env.user.company_id.id
            product_line = (0, 0, {'product_id': line.product_id.id,
                                   'product_uom_id': line.product_id.uom_po_id.id,
                                   'product_description_variants': line.description,
                                   'schedule_date': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                   'product_qty': line.product_qty,
                                   'qty_ordered': line.product_qty,
                                   'account_analytic_id':line.analytic_account_id.id,

                                   })
            order_line.append(product_line)

        return {
            'name': _('New Contract '),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.contract',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_line_ids': order_line,
                'default_request_id': self.id,
                'request_id': self.id,
                # 'is_contract':True,
                'default_item_type': self.item_type,
                # 'default_type_id': type.id if type else False,
                'default_company_id': self.company_id.id,
                'default_purchase_type':self.purchase_type

            }
        }


    # def _send_reminder_mail(self, send_single=False):
    #     # if not self.user_has_groups('purchase.group_send_reminder'):
    #     #     return

    #     template = self.env.ref('material_request.email_template_edi_material_request_reminder',
    #                             raise_if_not_found=False)
    #     if template:
    #         orders = self if send_single else self._get_orders_to_remind()
    #         for order in orders:
    #             date = order.date_planned
    #             if date and (send_single or (date - relativedelta(
    #                     days=order.reminder_date_before_receipt)).date() == datetime.today().date()):
    #                 order.with_context(is_reminder=True).message_post_with_template(template.id,
    #                                                                                 email_layout_xmlid="mail.mail_notification_paynow",
    #                                                                                 composition_mode='comment')


class MaterialRequestLine(models.Model):
    _name = "material.request.line"
    _description = "Material Request Line"
    _inherit = ['mail.thread']

    # @api.depends('product_id', 'name', 'product_uom_id', 'product_qty',
    #              'date_required')
    # def _compute_supplier_id(self):
    #     for rec in self:
    #         if rec.product_id:
    #             if rec.product_id.seller_ids:
    #                 rec.supplier_id = rec.product_id.seller_ids[0].name

    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('purchase_ok', '=', True)], required=True,
        track_visibility='onchange')
    name = fields.Char('Description', size=256,
                       track_visibility='onchange')
    product_uomm_category_id = fields.Many2one(related='product_id.uom_id.category_id')

    product_uom_id = fields.Many2one('uom.uom', 'Product Unit of Measure',
                                     track_visibility='onchange',
                                     domain="[('category_id', '=', product_uomm_category_id)]")







    product_qty = fields.Float(string='Quantity', track_visibility='onchange',
                               digits=dp.get_precision('Product Unit of Measure'))
    received_qty = fields.Float(string="Received Qty", compute='_compute_existing_qty_in_rfqs', readonly=True)  # Compute existing qty in RFQs
    request_id = fields.Many2one('material.request',
                                 'Material Request',
                                 ondelete='cascade', readonly=False)
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 store=True, readonly=True)

    requested_by = fields.Many2one('res.users',
                                   related='request_id.requested_by',
                                   string='Requested by',
                                   store=True, readonly=True)

    assigned_to = fields.Many2one('res.users',
                                  related='request_id.assigned_to',
                                  string='Assigned to',
                                  store=True, readonly=True)
    assigned_to_supply = fields.Many2one('res.users',
                                         related='request_id.assigned_to_supply',
                                         string='Assigned to',
                                         store=True, readonly=True)



    ##########################add by ekhlas #######################
    assigned_date=fields.Datetime("Date of assigned",related="request_id.assigned_date",readonly=True)

    date_start = fields.Date(related='request_id.date_start',
                             string='Request Date', readonly=True,
                             store=True)
    end_start = fields.Date(related='request_id.end_start',
                            string='End Date', readonly=True,
                            store=True)
    description = fields.Text(string='Description',store=True
                              )
    date_required = fields.Date(string='Request Date', required=True,
                                track_visibility='onchange',
                                related='request_id.date_start')

    note_vendor = fields.Text(string='Note to vendor')
    part_number = fields.Char('Part Number')
    comment = fields.Text(string='Comment')
    request_state = fields.Selection(string='Request state',
                                     readonly=True,
                                     related='request_id.state',
                                     selection=_STATES,
                                     store=True)
    product_type = fields.Selection(string='PR Product type',
                                    readonly=True,
                                    related='product_id.product_type',
                                    )
    supplier_id = fields.Many2one('res.partner',
                                  string='Preferred supplier')
                                  # compute="_compute_supplier_id")

    categ_id = fields.Many2one('product.category',
                               string="Category")  # , default=lambda self: self.get_default_category())

    cancelled = fields.Boolean(string="Cancelled", readonly=True, default=False, copy=False)
    # qty_available = fields.Float("Available Qty", readonly=True, store=True)
    qty_available = fields.Float("Available Qty", compute='get_qty_available')

    qty_deliver = fields.Float("To Deliver", compute='compute_quantities', store=True)
    qty_purchase = fields.Float("To Purchase", compute='compute_quantities', store=True)
    unit_price = fields.Monetary(string="Estimated Cost")
    currency_id = fields.Many2one('res.currency', related='request_id.currency_id')
    # analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account",
    #                                       related='request_id.analytic_account_id')
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account",inverse='_compute_dummy',
        compute='get_analytic_account_id',readonly=False,store=True)

    # analytic_tag_ids = fields.Many2many(
    #     "account.analytic.tag", string="Analytic Tags", tracking=True,related="request_id.analytic_tag_ids"
    # )

    item_type = fields.Selection(related='request_id.item_type',string='Item Type')


    purchase_delivered = fields.Float()
    remarks = fields.Char()
    total = fields.Monetary(compute="compute_total")
    subtotal = fields.Monetary('SubTotal')



    # pending_qty_to_receive = fields.Float(
    #     compute="_compute_qty_to_buy",
    #     digits="Product Unit of Measure",
    #     copy=False,
    #     string="Pending Qty to Receive",
    #     store=True,
    # )


    qty_in_po = fields.Float(
        string="Qty In PO",
        digits="Product Unit of Measure",
        readonly=True,
        compute="_compute_existing_qty_in_rfqs",
        store=True,
        help="Quantity in Quotation.",
    )
    qty_done = fields.Float(
        string="Qty Received ",
        digits="Product Unit of Measure",
        readonly=True,
        compute="_compute_existing_qty_in_rfqs",
        help="Quantity completed",
        store=True,

    )


  



    @api.depends('product_id','request_id.state')
    def _compute_existing_qty_in_rfqs(self):
        """Compute the existing quantity for the product in all related RFQs (purchase orders)."""
        for record in self:
            if record.product_id and record.request_id.id:
                # Fetch all Purchase Orders related to this material request
                related_po_lines = self.env['purchase.order.line'].search([
                    ('order_id.request_ids', 'in', [record.request_id.id]),
                    ('product_id', '=', record.product_id.id),
                    ('order_id.state', '=','purchase'),
                    # ('company_id', '=',record.company_id.id)
                ])
                # Sum the quantities in all related RFQs
                record.received_qty = sum(related_po_lines.mapped('qty_received'))
                record.qty_in_po = sum(related_po_lines.mapped('product_qty'))
                record.qty_done = sum(related_po_lines.mapped('qty_received'))
            else:
                record.received_qty = 0.0
                record.qty_done = 0.0
                record.qty_in_po = 0.0


    # qty_cancelled = fields.Float(
    #     string="Qty Cancelled",
    #     digits="Product Unit of Measure",
    #     readonly=True,
    #     compute="_compute_qty_cancelled",
    #     store=True,
    #     help="Quantity cancelled",
    # )



    @api.onchange('product_id')
    def get_analytic_account_id(self):
        for rec in self:
            rec.analytic_account_id = rec.request_id.analytic_account_id


    def _compute_dummy(self):
        pass




    @api.depends('product_id','request_id.state')
    def _compute_qty(self):
        for record in self:

            if record.product_id and record.request_id.id:
                # Fetch all Purchase Orders related to this material request
                related_po_lines = self.env['purchase.order.line'].search([
                    ('order_id.request_ids', 'in', [record.request_id.id]),
                    ('product_id', '=', record.product_id.id),
                    ('order_id.state', '=','purchase')
                ])
                # Sum the quantities in all related RFQs
                record.qty_done = sum(related_po_lines.mapped('qty_received'))
                record.qty_in_po = sum(related_po_lines.mapped('product_qty'))
            else:
                record.qty_done = 0.0
                record.qty_in_po = 0.0

            
        

            


    @api.depends('state')          
    def action_recalculate_quantities(self):
        """Recalculate qty_in_po and qty_done for all MR lines."""
        for req in self:
            for line in req.line_ids:   # <-- your one2many to material_request_line
                line._compute_qty()     # call compute
                # Write values to store=True fields
                line.write({
                    'qty_in_po': line.qty_in_po,
                    'qty_done': line.qty_done,
                })


    @api.model
    def create(self, vals):
        product_id = self.env['product.product'].browse(vals.get('product_id'))
        qty = product_id.warehouse_quantity
        vals['qty_available'] = qty
        return super(MaterialRequestLine, self).create(vals)

    @api.constrains('product_qty', 'unit_price')
    def check_non_zero(self):
        if self.product_qty == 0:
            raise UserError("Quantity should be greater than Zero.\n %s" % self.product_id.display_name)
        #
        # if self.unit_price == 0:
        #     raise UserError("Estimated cost should be greater than Zero.\n %s" % self.product_id.display_name)

    # product_id domain

    @api.constrains('product_id', 'request_id')
    def _check_duplicate_product(self):
        """
        Ensure no duplicate product exists in the same material request.
        """
        for line in self:
            duplicate_lines = self.search([
                ('request_id', '=', line.request_id.id),
                ('product_id', '=', line.product_id.id),
                ('id', '!=', line.id)  # Exclude the current line
            ])
            if duplicate_lines:
                raise ValidationError(
                    _("The product '%s' is already added to the material request. Duplicate products are not allowed.")
                    % line.product_id.display_name
                )

    @api.onchange('product_id')
    def onchange_product(self):
        if not self.categ_id:
            raise UserError('Please select a category first!')
        
        #######################COMMENT BY EKHLAS ##########################333
        # if self.product_id:
        if self.request_id.item_type == 'material':
            # raise UserError(self.request_id.categ_id)
            # old code ekhlas ..
            #domain = {
            #     #######################COMMENT BY EKHLAS ##########################333
            #     # 'product_id': [('type', 'in', ['consu', 'product']), ('categ_id', 'child_of', self.request_id.categ_id.id)]}
            #     ##########ADD LINE BY EKHLAS #############
            #     'product_id': ['|',('type', 'in', ['consu', 'product']),('categ_id', '=', self.request_id.categ_id.id),('categ_id', 'child_of', self.request_id.categ_id.id)]}
            

            domain = {'product_id': ['&',('type', 'in', ['consu', 'product']),'|',('categ_id', '=', self.request_id.categ_id.id),('categ_id', 'child_of', self.request_id.categ_id.id)]}



            code=''
            name=''
            if self.product_id.code:
                code = self.product_id.code

            if self.product_id.name:
                name  = '%s [%s]' % (code ,self.product_id.name) + '\n'

            # name = self.product_id.name


            if self.product_id.description_purchase:
                name += '\n' + self.product_id.description_purchase

            elif self.product_id.description:
                name += '\n' + self.product_id.description

            
            self.product_uom_id = self.product_id.uom_id.id
            self.product_qty = 1
            # ###################comment by ekhlas
            self.description = name
            # self.description = self.product_id.name
            self.name = name
            self.qty_available = self.product_id.warehouse_quantity
            self.unit_price = self.product_id.standard_price
            self.unit_price = self.product_id.standard_price
            self.product_type = self.product_id.product_type
            self.part_number = self.product_id.part_number
            # ###################comment by ekhlas
            # self.description = self.product_id.description_purchase
        
        else:
            #######################COMMENT BY EKHLAS ##########################333
            # domain = {'product_id': [('type', '=', 'service'), ('categ_id', 'child_of', self.request_id.categ_id.id)]}
            ##########ADD LINE BY EKHLAS #############
            domain = {'product_id': ['&',('type', '=', 'service'),'|',('categ_id', '=', self.request_id.categ_id.id),('categ_id', 'child_of', self.request_id.categ_id.id)]}

            # comment by ekhlass des = self.product_id.description
            # name  = '%s [%s]' % (self.product_id.name ,des) + '\n'
            # # name = self.product_id.name
            # if self.product_id.code:
            #     name = '[%s] %s' % (name, self.product_id.code) + '\n'
            # if self.product_id.description_purchase:
            #     name += '\n' + self.product_id.description_purchase

            code=''
            name=''
            if self.product_id.code:
                code = self.product_id.code

            if self.product_id.name:
                name  = '%s [%s]' % (code ,self.product_id.name) + '\n'

            # name = self.product_id.name


            if self.product_id.description_purchase:
                name += '\n' + self.product_id.description_purchase

            if self.product_id.description:
                name += '\n' + self.product_id.description

            self.product_uom_id = self.product_id.uom_id.id
            self.product_qty = 1
            self.name = name
            # self.name = self.product_id.name
            self.qty_available = self.product_id.warehouse_quantity
            
            self.unit_price = self.product_id.standard_price
            self.unit_price = self.product_id.standard_price
            self.product_type = self.product_id.product_type
            self.part_number = self.product_id.part_number
            # ###################comment by ekhlas
            # self.description = self.product_id.description_purchase
            # ###################add line by ekhlas
            # self.description = self.product_id.name
            self.description = name

        return {'domain': domain}

    def get_default_category(self):
        # record = self.env['material.request'].browse(self.env.context['active_ids'])
        raise UserError(str(self._context))
        return self.env['material.request']._context.get('categ_id', False)

    @api.depends('product_qty', 'unit_price')
    def compute_total(self):
        self.ensure_one()
        for rec in self:
            rec.total = rec.product_qty * rec.unit_price

    #
    # def compute_purchase_delivered(self):
    #     lines = []
    #     delivered = False
    #
    #     if self.request_id.item_type == 'material':
    #         lines = self.env['stock.move'].search([
    #             ('mr_line_id', '=', self.id),
    #             ('mr_purchase_line', '=', True),
    #             ('state', '=', 'done'),
    #             ('origin_returned_move_id', '=', False),
    #         ])
    #
    #         delivered = sum(line.quantity_done for line in lines)
    #         self.purchase_delivered = delivered
    #
    #     else:
    #         lines = self.env['material.order.line'].search([
    #             ('request_line_id', '=', self.id),
    #         ])
    #
    #         delivered = sum(line.qty_invoiced for line in lines)
    #         self.purchase_delivered = delivered

    @api.depends('qty_available', 'product_qty')
    def compute_quantities(self):
        for line in self:
            if line.qty_available > line.product_qty:
                line.qty_deliver = line.product_qty
            else:
                line.qty_deliver = line.qty_available if line.qty_available > 0 else 0.0

            line.qty_purchase = line.product_qty - line.qty_deliver

    # @api.constrains('product_id', 'request_id')
    # def check_product_category(self):
    #     for line in self:
    #         if not line.product_id.categ_id == line.request_id.categ_id:
    #             raise UserError(
    #                 "All request lines must be under the same category. (%s)" % line.request_id.categ_id.display_name)


    @api.depends('product_id')
    def get_qty_available(self):
        for rec in self:
            rec.qty_available = rec.product_id.qty_available


    # @api.depends('product_id')
    # def get_qty_available(self):
    #     self.qty_available = self.product_id.warehouse_quantity
    #         rec.qty_available = rec.product_id.qty_available

    # @api.onchange('product_id')
    # def onchange_product_id(self):
    #     if not self.categ_id:
    #         raise UserError('Please select a category first!')
    #     if self.product_id:
    #          if self.product_id:

    #             des = self.product_id.description
    #             name  = '%s [%s]' % (self.product_id.name ,des) + '\n'
    #             # name = self.product_id.name
    #             if self.product_id.code:
    #                 name = '[%s] %s' % (name, self.product_id.code) + '\n'
    #             if self.product_id.description_purchase:
    #                 name += '\n' + self.product_id.description_purchase
    #             self.product_uom_id = self.product_id.uom_id.id
    #             self.product_qty = 1
    #             self.name = name
    #             self.qty_available = self.product_id.warehouse_quantity
    #             self.unit_price = self.product_id.standard_price
    #             self.unit_price = self.product_id.standard_price
    #             self.product_type = self.product_id.product_type
    #             self.part_number = self.product_id.part_number
    #             self.description = self.product_id.description_purchase
                
                
    def do_cancel(self):
        """Actions to perform when cancelling a purchase request line."""
        self.write({'cancelled': True})

    def do_uncancel(self):
        """Actions to perform when uncancelling a purchase request line."""
        self.write({'cancelled': False})

    def _compute_is_editable(self):
        for rec in self:
            if rec.request_id.state in ('to_approve', 'leader_approved', 'manager_approved', 'reject',
                                        'done'):
                rec.is_editable = False
            else:
                rec.is_editable = True

    is_editable = fields.Boolean(string='Is editable',
                                 compute="_compute_is_editable",
                                 readonly=True)

    def write(self, vals):
        res = super(MaterialRequestLine, self).write(vals)
        if vals.get('cancelled'):
            requests = self.mapped('request_id')
            requests.check_auto_reject()
        return res

    # add branch id
    # def _create_stock_moves_transfer(self, picking, qty):
    #     moves = self.env['stock.move']
    #     done = self.env['stock.move'].browse()
    #     for line in self:
    #
    #         diff_quantity = 0.0
    #         mr_line = False
    #         if qty == 'deliver':
    #             diff_quantity = line.qty_deliver
    #         elif qty == 'purchase':
    #             diff_quantity = line.qty_purchase
    #             mr_line = True
    #
    #         template = {
    #             'name': line.name or '',
    #             'product_id': line.product_id.id,
    #             'product_uom': line.product_uom_id.id,
    #             'location_id': picking.location_id.id,
    #             'location_dest_id': picking.location_dest_id.id,
    #             'picking_id': picking.id,
    #             'move_dest_id': False,
    #             'state': 'draft',
    #             'company_id': picking.company_id.id,
    #             # 'price_unit': price_unit,
    #             'picking_type_id': picking.picking_type_id.id,
    #             'procurement_id': False,
    #             'route_ids': 1 and [
    #                 (6, 0, [x.id for x in self.env['stock.location.route'].search([('id', 'in', (2, 3))])])] or [],
    #             'warehouse_id': picking.picking_type_id.warehouse_id.id,
    #             'product_uom_qty': diff_quantity,
    #             'mr_purchase_line': mr_line,
    #             'mr_line_id': line.id,
    #         }
    #
    #         done += moves.create(template)
    #     return done



class CodeEquipment(models.Model):
    _name = 'model.equipment'
    _description = 'Equipment'

    name = fields.Char('Equipment')
    code = fields.Char('Code', index=True)
    type = fields.Char('Type')
    brand = fields.Char('Brand')
    model = fields.Char('Model')
    category = fields.Selection(string='Category', selection=[('light', 'Light'), ('vehicles', 'Vehicles'),('heavy_equipment', 'Heavy Equipment'), ('trucks', 'Trucks')])
    categ_id=fields.Many2one("model.equipment.category","Equipment Category")
    year = fields.Integer('Year')
    plate = fields.Char('Plate')
    vin = fields.Char('VIN.#')
    engine = fields.Char('Engine model')
    engine_serial = fields.Char('Engine serial No')
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    c_b_type=fields.Char(string="C.B.Type")
    c_b_rating=fields.Char(string="C.B.Rating")
    rated_power_kva=fields.Char(string="Rated Power KVA")
    voltage_transfer=fields.Char(string="Voltage Transfer")


    B_DIM=fields.Char("B-DIM")
    TYPE=fields.Char("TYPE")
    UNIT_NAME=fields.Char("UNIT NAME")
    U_DIM=fields.Char("U-DIM")
    AC=fields.Char("AC")






class CodeEquipmentCategory(models.Model):
    _name = 'model.equipment.category'
    _description = 'Equipment Category' 
    name = fields.Char('Name')


class EvaluationWizard(models.TransientModel):
    _name = 'evaluation.wizard'
    _description = 'Evaluation Wizard'




    supplier_ids = fields.Many2many('res.partner', string='Suppliers', domain="[('id', 'in', supplier_po_ids)]",required=True)
    material_request_id = fields.Many2one('material.request', string='Material Request', required=True)
    evaluation_type = fields.Selection([
        ('weighted_scoring', 'With Technical Evaluation'),
        ('lowest_price', 'Without Technical Evaluation')
    ], string='Evaluation Type', required=True, default='weighted_scoring')
    supplier_po_ids = fields.Many2many('res.partner', compute="_compute_supplier_po_ids", string="Suppliers in PO")


    @api.depends('material_request_id')
    def _compute_supplier_po_ids(self):
        for wizard in self:
            if wizard.material_request_id:
              

                # Retrieve suppliers from POs related to the material request
                po_suppliers = self.env['purchase.order'].search([
                    ('request_id', '=', wizard.material_request_id.id),
               ('state', '=', 'draft')

                ]).mapped('partner_id')

                # Assign retrieved suppliers to the supplier_po_ids field
                wizard.supplier_po_ids = po_suppliers
            else:
                # If no material request is selected, clear the suppliers
                wizard.supplier_po_ids = [(5, 0, 0)]




    @api.model
    def default_get(self, fields_list):
        res = super(EvaluationWizard, self).default_get(fields_list)

        # Initialize po_suppliers to empty recordset by default
        po_suppliers = self.env['res.partner']

        material_request_id = self._context.get('default_material_request_id')
        if material_request_id:
            # Search suppliers linked to POs of the material request
            po_suppliers = self.env['purchase.order'].search([
                ('request_id', '=', material_request_id),
                ('state', '=', 'draft')
            ]).mapped('partner_id')

        # Assign supplier_ids safely
        res['supplier_ids'] = [(6, 0, po_suppliers.ids)] if po_suppliers else []
        
        return res


    def action_evaluate(self):
        self.ensure_one()
        rec = self  # Current wizard record
        # Ensure that exactly 3 suppliers are selected
        if len(self.supplier_ids) > 3:
            raise UserError("You cann't select Grather Than 3 suppliers.")
        # Dynamically assign suppliers to Class A, B, and C based on selection order
        a_supplier = self.supplier_ids[0]  # First supplier is Class A
        b_supplier = self.supplier_ids[1] if len(self.supplier_ids) > 1 else None  # Second supplier is Class B
        c_supplier = self.supplier_ids[2] if len(self.supplier_ids) > 2 else None  # Third supplier is Class C
        if self.env.context.get('active_id'):
            mr = self.env['material.request'].search([('id', '=', self.env.context.get('active_id'))])
        # Depending on the selected evaluation type, proceed with the evaluation creation
        if self.evaluation_type == 'weighted_scoring':
            env = self.env(user=1)
            res_id = env['weight.scoring.evaluation'].create({
                'req_id': self.env.user.id,
                'material_request_id': self.env.context.get('active_id'),
                'date_request': fields.Datetime.now(),
                'a_supplier_id': a_supplier.id,
                'company_id': self.material_request_id.company_id.id,
                'b_supplier_id': b_supplier.id if b_supplier else False,
                'c_supplier_id': c_supplier.id if c_supplier else False,
            })
            if mr:
                  mr.sudo().write({'state': 'w_te'})
                  mr.sudo().activity_update_tehincal_evaluation()
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'weight.scoring.evaluation',
                'res_id': res_id.id,
                'context': {'form_view_initial_mode': 'edit'},
            }

        elif self.evaluation_type == 'lowest_price':
            env = self.env(user=1)
            res_id = env['lowest.price.evaluation'].create({
                'req_id': self.env.user.id,
                'material_request_id': self.env.context.get('active_id'),
                'a_supplier_id': a_supplier.id,
                'b_supplier_id': b_supplier.id if b_supplier else False,
                'c_supplier_id': c_supplier.id if c_supplier else False,
                'company_id': self.material_request_id.company_id.id,

                # Optionally pass supplier_ids if needed
            })
            if mr:
                  mr.sudo().write({'state': 'w_ce'})
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'lowest.price.evaluation',
                'res_id': res_id.id,
                'context': {'form_view_initial_mode': 'edit'},
            }




    def send_rfqs_email(self):
        """Send all RFQs PDF related to this material request to requester and line manager"""
        self.ensure_one()


        # Fetch all RFQs for this MR
        rfqs = self.env['purchase.order'].search([('request_id', '=', self.material_request_id.id)])
        if not rfqs:
            raise UserError("No RFQs found for this Material Request.")

        # Recipients: MR requester + line manager
        partner_ids = []
        if self.material_request_id.requested_by:
            partner_ids.append(self.material_request_id.requested_by.partner_id.id)
        if getattr(self.material_request_id, 'line_manager_id', False):
            partner_ids.append(self.material_request_id.line_manager_id.partner_id.id)

        if not partner_ids:
            raise UserError("No recipients found for this email.")

        # Prepare attachments: generate PDF for each RFQ
        attachments = []
        report = self.env.ref('purchase.action_report_purchaseorder')  # Standard RFQ/Purchase Order PDF report
        for rfq in rfqs:
            pdf_content, _ = report._render_qweb_pdf([rfq.id])
            attachments.append((f'{rfq.name}.pdf', pdf_content))

        # Send email using a template or direct mail
        mail_values = {
            'subject': f"RFQs for MR {self.material_request_id.name}",
            'body_html': f"<p>Dear User,<br/>Please find attached all RFQs for Material Request {self.material_request_id.name}.</p>",
            'email_to': ','.join([p.email for p in self.env['res.partner'].browse(partner_ids) if p.email]),
            'attachment_ids': [(0, 0, {'name': att[0], 'datas': base64.b64encode(att[1]).decode(), 'mimetype': 'application/pdf'}) for att in attachments],
        }
        self.env['mail.mail'].create(mail_values).send()



class AddToRfqWizard(models.TransientModel):
    _name = 'add.to.rfq.wizard'
    _description = 'Add Products to Existing RFQ'

    purchase_order_id = fields.Many2one('purchase.order', string='RFQ to Add To',
                                        domain="[('state', 'in', ['draft'])]")
    purchase_tender_id = fields.Many2one('purchase.requisition', string='Tender to Add To',
                                        domain="[('state', 'in', ['open','ongoing','in_progress'])]")  # Restrict state
    material_request_id = fields.Many2one('material.request', string='Material Request', required=True,
                                          readonly=True)
    product_line_ids = fields.One2many('add.to.rfq.wizard.line', 'wizard_id', string='Products to Add')

    def action_add_to_rfq(self):
        """
        Adds the selected products to the specified RFQ.  If a product already exists
        on the RFQ, its quantity is increased. The product_qty will not be allowed
        to exceed the qty_available_for_rfq.
        """
        self.ensure_one()
        purchase_order = self.purchase_order_id
        for wizard_line in self.product_line_ids.filtered(
                lambda l: l.add_to_rfq):  # Only process lines that the user wants to add
            existing_po_line = False
            # Check if product_qty exceeds qty_available_for_rfq
            # if wizard_line.product_qty > wizard_line.qty_available_for_rfq:
            #     raise UserError(
            #         _('You cannot add more than the available quantity for product "%s". Available quantity is %s') %
            #         (wizard_line.product_id.name, wizard_line.qty_available_for_rfq))

            # Check if the product already exists in the PO line
            existing_po_line = purchase_order.order_line.filtered(lambda l: l.product_id == wizard_line.product_id)
            if existing_po_line:
                # Product already exists on the RFQ, increase quantity
                existing_po_line.product_qty += wizard_line.product_qty
            else:
                # Product doesn't exist on the RFQ, create a new line
                vals = {
                    'order_id': purchase_order.id,
                    'product_id': wizard_line.product_id.id,
                    'product_qty': wizard_line.product_qty,
                    'product_uom': wizard_line.uom_id.id,
                    'price_unit': 0.0,  # Set a default price
                    'name': wizard_line.product_id.name,  # Or fetch from MR line
                    'date_planned': fields.Date.today(),  # Default date
                }
                existing_po_line = self.env['purchase.order.line'].create(vals)
            print('>>>>>>>>>>>>>>>>>>>>>>>>>.. 1 last', existing_po_line)

            # if existing_po_line:
            #    self.update_mr_qty_details(existing_po_line,self.material_request_id,wizard_line.product_qty)

            # Update the Many2many field in purchase.order with material_request_id
            if self.purchase_order_id and self.material_request_id:
                self.purchase_order_id.write({
                    'request_ids': [(4, self.material_request_id.id)]  # Add the material request
                })

        return {'type': 'ir.actions.act_window_close'}  # Close wizard after operation.
    def action_add_to_tender(self):
        self.ensure_one()
        tender_order = self.purchase_tender_id
        for wizard_line in self.product_line_ids.filtered(
                lambda l: l.add_to_rfq):  # Only process lines that the user wants to add
            existing_po_line = False
            # Check if product_qty exceeds qty_available_for_rfq
            # if wizard_line.product_qty > wizard_line.qty_available_for_rfq:
            #     raise UserError(
            #         _('You cannot add more than the available quantity for product "%s". Available quantity is %s') %
            #         (wizard_line.product_id.name, wizard_line.qty_available_for_rfq))

            # Check if the product already exists in the PO line
            existing_po_line = tender_order.line_ids.filtered(lambda l: l.product_id == wizard_line.product_id)
            if existing_po_line:
                # Product already exists on the RFQ, increase quantity
                existing_po_line.product_qty += wizard_line.product_qty
            else:
                # Product doesn't exist on the RFQ, create a new line
                vals = {
                    'requisition_id': tender_order.id,
                    'product_id': wizard_line.product_id.id,
                    'product_qty': wizard_line.product_qty,
                    'product_uom_id': wizard_line.uom_id.id,
                    'price_unit': 0.0,  # Set a default price
                }
                existing_po_line = self.env['purchase.requisition.line'].create(vals)
            print('>>>>>>>>>>>>>>>>>>>>>>>>>.. 1 last', existing_po_line)

            # if existing_po_line:
            #    self.update_mr_qty_details(existing_po_line,self.material_request_id,wizard_line.product_qty)

            # Update the Many2many field in purchase.order with material_request_id
            if self.purchase_tender_id and self.material_request_id:
                self.purchase_tender_id.write({
                    'request_ids': [(4, self.material_request_id.id)]  # Add the material request
                })

        return {'type': 'ir.actions.act_window_close'}  # Close wizard after operation.

    def update_mr_qty_details(self, po_line, mr_id, product_qty):
        """
        Updates the mr_qty_details field in the purchase order line to show MR-specific quantities.
        This appends the MR and its quantity, or increments the existing quantity if the MR already exists.
        """
        # Get the current details (if any) in the MR qty field
        existing_details = po_line.mr_qty_details or ""

        # Split the existing details into individual lines (each MR's entry)
        existing_lines = existing_details.split("\n") if existing_details else []

        # Check if the MR is already in the details
        mr_found = False
        updated_lines = []

        for line in existing_lines:
            mr_name, qty_str = line.split(": ")
            qty = float(qty_str)

            # If the MR is found, update the quantity
            if mr_name == mr_id.name:
                qty += product_qty
                mr_found = True

            # Append the updated line (or original line if MR not found)
            updated_lines.append(f"{mr_name}: {qty}")

        # If the MR wasn't found, add it as a new entry
        if not mr_found:
            updated_lines.append(f"{mr_id.name}: {product_qty}")

        # Join all lines back together into a single string
        updated_details = "\n".join(updated_lines)



class AddToRfqWizardLine(models.TransientModel):
    _name = 'add.to.rfq.wizard.line'
    _description = 'Product line to add to RFQ'

    wizard_id = fields.Many2one('add.to.rfq.wizard', string='Wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, readonly=True)
    product_qty = fields.Float(string='Quantity', required=True)
    qty_request = fields.Float(string='Quantity')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True, readonly=True)
    add_to_rfq = fields.Boolean(string="Add to RFQ", default=True)  # User can select what to add.
    existing_qty_in_rfqs = fields.Float(string="Received Qty", compute='_compute_existing_qty_in_rfqs', readonly=True)  # Compute existing qty in RFQs
    request_line_id = fields.Many2one('material.request.line', string='Request Line',
                                      readonly=True)  # Link to MR line
    qty_available_for_rfq = fields.Float(string="Available Quantity", compute='_compute_qty_available_for_rfq', readonly=True)


    @api.depends('product_id', 'wizard_id.material_request_id')
    def _compute_existing_qty_in_rfqs(self):
        """Compute the existing quantity for the product in all related RFQs (purchase orders)."""
        for record in self:
            if record.product_id and record.wizard_id.material_request_id:
                # Fetch all Purchase Orders related to this material request
                related_po_lines = self.env['purchase.order.line'].search([
                    ('order_id.request_ids', 'in', [record.wizard_id.material_request_id.id]),
                    ('product_id', '=', record.product_id.id),
                    ('order_id.state', '=','purchase')
                ])
                # Sum the quantities in all related RFQs
                record.existing_qty_in_rfqs = sum(related_po_lines.mapped('qty_received'))
            else:
                record.existing_qty_in_rfqs = 0.0

    @api.depends('qty_request', 'existing_qty_in_rfqs')
    def _compute_qty_available_for_rfq(self):
        """Compute the available quantity that can still be added to RFQs."""
        for record in self:
            record.qty_available_for_rfq = record.qty_request - record.existing_qty_in_rfqs
