# -*- encoding: utf-8 -*-

# the file added by ekhlas code contract new view 
from datetime import datetime, time
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

PURCHASE_REQUISITION_STATES = [
    ('draft', 'Draft'),
    ('contract_specialist', 'Contract Specialist'),
    ('contract_manager', 'Waiting for Contract Manager Approval'),
    ('supply_chain_manager', 'Waiting for SCM Director Approval'),
    ('ccso', 'Waiting for CCSO Approval'),

    ('ongoing', 'Ongoing'),
    ('in_progress', 'Confirmed'),
    ('open', 'Bid Selection'),
    ('done', 'Closed'),
    ('cancel', 'Cancelled'),
    ('reject', 'Reject'),

]


class PurchaseContract(models.Model):
    _name = "purchase.contract"
    _description = "Purchase Contract"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"

    def _get_type_id(self):
        return self.env['purchase.requisition.type'].search([], limit=1)

    name = fields.Char(string='Reference', required=False, copy=False, readonly=False)
    origin = fields.Char(string='Source Document')
    order_count = fields.Integer(compute='_compute_orders_number', string='Number of Orders')
    vendor_id = fields.Many2one('res.partner', string="Vendor",
                                domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    # type_id = fields.Many2one('purchase.requisition.type', string="Agreement Type", required=True, default=_get_type_id)
    type_id = fields.Selection([
        ('blanket_order', 'Blanket Order'), ('purchase_template', 'Purchase Template')],
         string='Agreement Type', required=True, default='blanket_order')
    ordering_date = fields.Date(string="Ordering Date", tracking=True)
    date_end = fields.Datetime(string='Agreement Deadline', tracking=True)
    schedule_date = fields.Date(string='Delivery Date', index=True,
                                help="The expected and scheduled delivery date where all the products are received",
                                tracking=True)
    user_id = fields.Many2one(
        'res.users', string='Purchase Representative',
        default=lambda self: self.env.user, check_company=True)

    contract_reference = fields.Char("Contract Reference")
    related_contract = fields.Many2one("purchase.contract", "Main Contract")
    description = fields.Text()
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    purchase_ids = fields.One2many('purchase.order', 'contract_id', string='Purchase Orders',
                                   states={'done': [('readonly', True)]})
    line_ids = fields.One2many('purchase.contract.line', 'contract_id', string='Products to Purchase',
                               states={'done': [('readonly', True)]}, copy=True)
    product_id = fields.Many2one('product.product', related='line_ids.product_id', string='Product', readonly=False)
    state = fields.Selection(PURCHASE_REQUISITION_STATES,
                             'Status', tracking=True, required=True,
                             copy=False, default='draft')
    state_blanket_order = fields.Selection(PURCHASE_REQUISITION_STATES, compute='_set_state')
    # is_quantity_copy = fields.Selection(related='type_id.quantity_copy', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.company.currency_id.id)

    request_id = fields.Many2one('material.request', 'Material Request',readonly=True)

    issuance_count = fields.Integer(string="Count", compute='compute_issuance_count')

    ###################################################additional field in contract

    requested_by = fields.Many2one('res.users', 'Requested by', track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True, readonly=True)
    date = fields.Date(string='Issue date', default=datetime.today())
    eff_date = fields.Date(string='Effective date', default=datetime.today())
    department_id = fields.Many2one('hr.department', string='Department',
                                    related="request_id.department_id")

    buyer_assigned = fields.Many2one(comodel_name='res.users', string='Buyer Assigned', )
    contract_number = fields.Char(string='Title')
    job_description = fields.Text(string='Job Description')
    duration = fields.Char(string='Contract Duration', compute='compute_contract_duration')
    start_date = fields.Date(string='Signed Date')
    finish_date = fields.Date(string='Expiry date')
    attatchment = fields.Binary(string='Attatchment')

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
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")

    is_fix_price=fields.Boolean("Fix")

    purchase_type = fields.Selection(
        [('local', 'Local Payment'), ('overseas', 'Overseas Payment')],
        string="Purchase Payment",
        default='local'
    )
    
    @api.onchange('related_contract')
    def _onchange_main_contract(self):
        for rec in self:
            if rec.related_contract:
                rec.vendor_id = rec.related_contract.vendor_id.id
                rec.date_end = rec.related_contract.date_end
                rec.type_id = rec.related_contract.type_id.id
                rec.currency_id = rec.related_contract.currency_id.id
                rec.request_id = rec.related_contract.request_id.id
                rec.ordering_date = rec.related_contract.ordering_date
                rec.schedule_date = rec.related_contract.schedule_date
                rec.origin = rec.related_contract.origin
                rec.remarks = rec.related_contract.remarks
                rec.scope_work = rec.related_contract.scope_work
                rec.scope_doc = rec.related_contract.scope_doc
                rec.payment_term_id = rec.related_contract.payment_term_id.id
                rec.t_c = rec.related_contract.t_c
                rec.contract_level = rec.related_contract.contract_level
                rec.department_id = rec.related_contract.department_id.id
                rec.name = rec.related_contract.name + ' :'
                lines = []
                for rec_line in rec.related_contract.line_ids:
                    result = {'product_id': rec_line.product_id, 'product_uom_id': rec_line.product_uom_id,
                              'product_uom_category_id': rec_line.product_uom_category_id,
                              'product_qty': rec_line.product_qty,
                              'product_description_variants': rec_line.product_description_variants,
                              'price_unit': rec_line.price_unit,
                              'qty_ordered': rec_line.qty_ordered, 'supplier_info_ids': rec_line.supplier_info_ids,
                              'account_analytic_id': rec_line.account_analytic_id,
                               'schedule_date': rec_line.schedule_date}
                    lines.append((0, 0, result))
                rec.line_ids = False
                rec.line_ids = lines

    @api.depends('state')
    def _set_state(self):
        for contract in self:
            contract.state_blanket_order = contract.state

    @api.depends('vendor_id')
    def _onchange_vendor(self):
        self = self.with_company(self.company_id)
        if not self.vendor_id:
            self.currency_id = self.env.company.currency_id.id
        else:
            self.currency_id = self.vendor_id.property_purchase_currency_id.id or self.env.company.currency_id.id

        requisitions = self.env['purchase.contract'].search([
            ('vendor_id', '=', self.vendor_id.id),
            ('state', '=', 'ongoing'),
            ('type_id.quantity_copy', '=', 'copy'),
            ('company_id', '=', self.company_id.id),
        ])
        if any(requisitions):
            title = _("Warning for %s", self.vendor_id.name)
            message = _(
                "There is already an open blanket order for this supplier. We suggest you complete this open blanket order, instead of creating a new one.")
            warning = {
                'title': title,
                'message': message
            }
            return {'warning': warning}

    @api.depends('purchase_ids')
    def _compute_orders_number(self):
        for contract in self:
            contract.order_count = len(contract.purchase_ids)

    def action_cancel(self):
        # try to set all associated quotations to cancel state
        for contract in self:
            for contract_line in contract.line_ids:
                contract_line.supplier_info_ids.unlink()
            contract.purchase_ids.button_cancel()
            for po in contract.purchase_ids:
                po.message_post(body=_('Cancelled by the agreement associated to this quotation.'))
        self.write({'state': 'cancel'})

    def action_in_progress(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("You cannot confirm agreement '%s' because there is no product line.", self.name))
        if self.type_id.quantity_copy == 'none' and self.vendor_id:
            for contract_line in self.line_ids:
                if contract_line.price_unit <= 0.0:
                    raise UserError(_('You cannot confirm the blanket order without price.'))
                if contract_line.product_qty <= 0.0:
                    raise UserError(_('You cannot confirm the blanket order without quantity.'))
                contract_line.create_supplier_info()
            self.write({'state': 'ongoing'})
        else:
            self.write({'state': 'in_progress'})
        # Set the sequence number regarding the requisition type
        # if self.name == 'New':
        #     if self.is_quantity_copy != 'copy':
        #         self.name = self.env['ir.sequence'].next_by_code('purchase.contract.blanket.order')
        #     else:
        #         self.name = self.env['ir.sequence'].next_by_code('purchase.contract.blanket.order')

    def action_open(self):
        self.write({'state': 'open'})

    def action_draft(self):
        self.ensure_one()
        # self.name = 'New'
        self.write({'state': 'draft'})

    def action_done(self):
        """
        Generate all purchase order based on selected lines, should only be called on one agreement at a time
        """
        if any(purchase_order.state in ['draft', 'sent', 'to approve'] for purchase_order in
               self.mapped('purchase_ids')):
            raise UserError(_('You have to cancel or validate every RfQ before closing the purchase contract_id.'))
        for requisition in self:
            for requisition_line in requisition.line_ids:
                requisition_line.supplier_info_ids.unlink()
        self.write({'state': 'done'})

    def unlink(self):
        if any(requisition.state not in ('draft', 'cancel') for requisition in self):
            raise UserError(_('You can only delete draft contract_id.'))
        # Draft requisitions could have some requisition lines.
        self.mapped('line_ids').unlink()
        return super(PurchaseContract, self).unlink()

    ###############################################addtionial function
    @api.constrains('start_date', 'finish_date')
    def _check_dates(self):
        for date in self:
            if date.finish_date:
                if date.finish_date < date.start_date:
                    raise ValidationError('The finishing date cannot be earlier than the starting date .')

    def compute_contract_duration(self):
        if self.finish_date:
            self.duration = self.finish_date - self.start_date
        else:
            self.duration = 0.0

    @api.depends('contract_amount')
    def get_contract_level(self):
        self.ensure_one()
        if self.contract_amount < self.company_id.maximum_contract_amount:
            self.contract_level = 'operation'
        else:
            self.contract_level = 'corporate'

    def get_requested_by(self):
        user = self.env.user.id
        return user

    def _get_default_department(self):
        return self.env.user.department_id.id if self.env.user.department_id else False

    def compute_issuance_count(self):
        self.issuance_count = self.env['issuance.request'].search_count([('delivery_address', '=', self.vendor_id.id)])

    def action_view_issuance(self):
        return {
            'name': "Issuance Request",
            'type': 'ir.actions.act_window',
            'res_model': 'issuance.request',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('delivery_address', '=', self.vendor_id.id)],
        }

    def contract_specialist(self):
        for rec in self:
            rec.contract_reference = self.env['ir.sequence'].next_by_code('purchase.contract.blanket.order')
            return rec.write({'state': 'contract_manager'})

    def contract_manager(self):
        for rec in self:
            return rec.write({'state': 'contract_manager'})

    def supply_chain_manager(self):
        for rec in self:
            return rec.write({'state': 'supply_chain_manager'})

    def ccso(self):
        for rec in self:
            return rec.write({'state': 'ccso'})

    def action_view_purchase_order(self):
        return {
            'name': "RFQ/ Order",
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_id': material_request.payment_request_form,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('request_id', '=', self.id)],
        }

    def make_purchase_quotation(self):
        view_id = self.env.ref('material_request.payment_request_form')
        order_line = []

        for line in self.line_ids:
            # Prepare the name field with product descriptions
            name = line.product_id.name
            if line.product_id.description_purchase:
                name += '\n' + line.product_id.description_purchase
            if line.product_id.description:
                name += '\n' + line.product_id.description

            # Construct the order line
            product_line = (0, 0, {
                'product_id': line.product_id.id,
                'state': 'draft',
                'product_uom': line.product_id.uom_po_id.id,
                'price_unit': line.price_unit,
                'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'product_qty': line.product_qty,
                'name': name,
                'account_analytic_id': line.account_analytic_id.id if line.account_analytic_id else False,
            })
            order_line.append(product_line)

        # Create the purchase order (RFQ)
        purchase_order_vals = {
            'partner_id': self.vendor_id.id,  # Supplier
            'date_order': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'order_line': order_line,  # Pass the order_line here
            'contract_purchased': True,
            'contract_id': self.id,
            'company_id':self.company_id.id,
            'request_id':self.request_id.id,
            'currency_id': self.currency_id.id,
            

        }
        purchase_order = self.env['purchase.order'].create(purchase_order_vals)

        # Open the purchase order form view
        return {
            'type': 'ir.actions.act_window',
            'name': 'Request for Quotation',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'res_id': purchase_order.id,
            'view_id': view_id.id if view_id else False,
            'target': 'current',
        }


class PurchaseContractLine(models.Model):
    _name = "purchase.contract.line"
    _description = "Purchase Contract Line"
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)],
                                 required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Product Unit of Measure',)
     # domain="[('category_id', '=', product_uom_category_id)]"
    product_uom_category_id = fields.Many2one(related='product_id.uom_id')
    product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure')
    product_description_variants = fields.Char('Custom Description')
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    qty_ordered = fields.Float(compute='_compute_ordered_qty', string='Ordered Quantities')
    contract_id = fields.Many2one('purchase.contract', required=True, string='Purchase Agreement', ondelete='cascade')
    company_id = fields.Many2one('res.company', related='contract_id.company_id', string='Company', store=True,
                                 readonly=True, default=lambda self: self.env.company)
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    # analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    schedule_date = fields.Date(string='Scheduled Date')
    supplier_info_ids = fields.One2many('product.supplierinfo', 'purchase_contract_line_id')






    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line, vals in zip(lines, vals_list):
            if line.contract_id.state not in ['draft', 'cancel', 'done']:
                supplier_infos = self.env['product.supplierinfo'].search([
                    ('product_id', '=', vals.get('product_id')),
                    ('partner_id', '=', line.contract_id.vendor_id.id),
                ])
                if not any(s.contract_id for s in supplier_infos):
                    line.create_supplier_info()
                # if vals['price_unit'] <= 0.0  :
                #     raise UserError(_('You cannot confirm the blanket order without price.'))
        return lines




    # @api.model
    # def create(self, vals):
    #     res = super(PurchaseContractLine, self).create(vals)
    #     # if res.contract_id.state not in ['draft', 'cancel', 'done'] and res.contract_id.is_quantity_copy == 'none': odoo 14
    #     if res.contract_id.state not in ['draft', 'cancel', 'done'] :
    #         supplier_infos = self.env['product.supplierinfo'].search([
    #         ('product_id', '=', vals.get('product_id')),
    #         ('name', '=', res.contract_id.vendor_id.id),
    #     ])
    #     if not any(s.contract_id for s in supplier_infos):
    #         res.create_supplier_info()
    #     if vals['price_unit'] <= 0.0:
    #         raise UserError(_('You cannot confirm the blanket order without price.'))
    #     return res

    def write(self, vals):
        res = super(PurchaseContractLine, self).write(vals)
        if 'price_unit' in vals:
            # if vals['price_unit'] <= 0.0 and any(
            #         requisition.state not in ['draft', 'cancel', 'done'] for requisition in self.mapped('contract_id')):
            #     raise UserError(_('You cannot confirm the blanket order without price.'))
            # If the price is updated, we have to update the related SupplierInfo
            self.supplier_info_ids.write({'price': vals['price_unit']})
        return res

    def unlink(self):
        to_unlink = self.filtered(lambda r: r.contract_id.state not in ['draft', 'cancel', 'done'])
        to_unlink.mapped('supplier_info_ids').unlink()
        return super(PurchaseContractLine, self).unlink()

    def create_supplier_info(self):
        purchase_contract = self.contract_id
        if purchase_contract.type_id.quantity_copy == 'copy' and purchase_contract.vendor_id:
            # create a supplier_info only in case of blanket order
            self.env['product.supplierinfo'].create({
                'partner_id': purchase_contract.vendor_id.id,
                'product_id': self.product_id.id,
                'product_tmpl_id': self.product_id.product_tmpl_id.id,
                'price': self.price_unit,
                'currency_id': self.contract_id.currency_id.id,
                'purchase_contract_line_id': self.id,
            })

    @api.depends('contract_id.purchase_ids.state')
    def _compute_ordered_qty(self):
        line_found = set()
        for line in self:
            total = 0.0
            for po in line.contract_id.purchase_ids.filtered(
                    lambda purchase_order: purchase_order.state in ['purchase', 'done']):
                for po_line in po.order_line.filtered(lambda order_line: order_line.product_id == line.product_id):
                    if po_line.product_uom != line.product_uom_id:
                        total += po_line.product_uom._compute_quantity(po_line.product_qty, line.product_uom_id)
                    else:
                        total += po_line.product_qty
            if line.product_id not in line_found:
                line.qty_ordered = total
                line_found.add(line.product_id)
            else:
                line.qty_ordered = 0

    @api.depends('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_po_id
            self.product_qty = 1.0
        if not self.schedule_date:
            self.schedule_date = self.contract_id.schedule_date

    def _prepare_purchase_order_line(self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False):
        self.ensure_one()
        requisition = self.contract_id
        if self.product_description_variants:
            name += '\n' + self.product_description_variants
        if requisition.schedule_date:
            date_planned = datetime.combine(requisition.schedule_date, time.min)
        else:
            date_planned = datetime.now()
        return {
            'name': name,
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_po_id.id,
            'product_qty': product_qty,
            'price_unit': price_unit,
            'taxes_id': [(6, 0, taxes_ids)],
            'date_planned': date_planned,
            'account_analytic_id': self.account_analytic_id.id,
            # 'analytic_tag_ids': self.analytic_tag_ids.ids,
        }
