from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round
import logging
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang


from odoo.tools import config

_logger = logging.getLogger(__name__)

class x_area(models.Model):
    _name = "x_area"
    _rec_name = "x_name"

    x_name = fields.Char()
    x_active = fields.Boolean()
    x_studio_discount_on_ore_price = fields.Float()
    x_studio_discount_on_transportation = fields.Float()
    x_studio_distance_1 = fields.Integer()
    x_studio_gasoline = fields.Float()
    x_studio_sequence = fields.Integer()
    x_studio_special_discount_1 = fields.Boolean()
    x_studio_state = fields.Many2one('res.country.state')
    x_studio_unit_price = fields.Float()
    x_studio_vendor = fields.Many2one('res.partner')


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    _order = 'create_date desc'

    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('prm', 'Waiting Purchase Manager Approval'),
        ('sum', 'Waiting Procurement Manager Approval'),
        ('sud', 'Waiting Supply Chain Director Approval'),
        ('contract_manager', 'Waiting Contract Manager Approval'),
        ('ccso', 'CCSO Approval'),
        ('fleet_director', 'Fleet Director Approval'),
        ('fm', 'Finance Manager Approval'),
        ('weight', 'Grading and Analysis'),
        ('site', 'Operation Director Approval'),
        ('line_approve', 'Waiting Line Manager Approval'),
        ('service_done', 'Service Completed'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('reject', 'Rejected'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=False, index=True, copy=False, default='draft', track_visibility='onchange')
    user_type_ = fields.Selection(related="create_uid.user_type")

    request_id = fields.Many2one('material.request', 'Material Request')
    request_ids = fields.Many2many(
        'material.request',  # Related model
        'material_request_purchase_order_rel',  # Relation table name
        'po_id',  # Column for this model
        'mr_id',  # Column for related model
        string='Material Requests'
    )
    priority1 = fields.Selection([('normal', 'Normal'), ('urgent', 'Urgent'), ('Critical', 'Critical')],
                                 string='Priority', required=False)

    reason_reject = fields.Text("Rejection Reason", track_visibility="onchange")
    over_budget = fields.Boolean()
    amount_total_default_currency = fields.Monetary(compute='compute_amount_total_company_currency')
    company_currency = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id)
    mr_total = fields.Monetary(related='request_id.amount_total_purchase', string="MR Total")
    has_mr = fields.Boolean(compute='get_has_mr')

    department_id = fields.Many2one(related="request_id.department_id", string="Department")
    average = fields.Float("Average", related='weight_request_id.average')
    weight_request_qty = fields.Float(related="weight_request_id.quantity", string="Quantity")
    assigned_data = fields.Datetime(related='request_id.assigned_date', string='Assigned Date', store=True)
    inspection_id = fields.One2many("material.inspection", "purchase_id", string="Inspection")
    certificate_ids = fields.One2many('completion.certificate', 'purchase_order_id', string="Certificates")
    has_service_lines = fields.Boolean(string="Has Service Lines", compute="_compute_has_service_lines", store=False)

    is_selected = fields.Boolean(string="Selected PO", default=False)
    is_opu_po = fields.Boolean(string='Is MATERIAL MINDS PO', readonly=True)
    lot_id = fields.Many2one(comodel_name="stock.lot", string="Lots Batch")
    x_studio_many2one_field_t3bCi = fields.Many2one("x_area",)
    x_studio_vendor_invoice_no = fields.Char()
    x_studio_delivery_period = fields.Char()
    x_studio_supplier_bank_details_1 = fields.One2many("res.partner.bank", "partner_id", related="partner_id.bank_ids")




    @api.depends('order_line.product_id.type')
    def _compute_has_service_lines(self):
        for order in self:
            order.has_service_lines = any(
                line.product_id and line.product_id.type == 'service' for line in order.order_line)

    def action_open_certificates(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Certificates'),
            'res_model': 'completion.certificate',
            'view_mode': 'list,form',
            'domain': [('purchase_order_id', '=', self.id)],
            'context': {'default_purchase_order_id': self.id},
        }

    def action_mark_service_done(self):
        for order in self:
            if not order.ore_purchased:
                # If the PO has service lines, require at least one approved certificate
                if any(l.product_id.type == 'service' for l in order.order_line):
                    if not any(c.state == 'approved' for c in order.certificate_ids):
                        raise UserError(_("You cannot mark Service Completed without an approved Certificate."))

            order.state = 'service_done'



    purchase_type = fields.Selection(
        [('local', 'Local Payment'), ('overseas', 'Overseas Payment')],
        string="Purchase Payment",
        default='local'
    )

    supply_user_id = fields.Many2one('res.users')
    supply_user = fields.Many2one('res.users', related='request_id.assigned_to_supply')
    ore_purchased = fields.Boolean(default=False, string="IS ORE/ROCK Purchase")

    contract_purchased = fields.Boolean(default=False, string="IS Payment Contract")

    ccso_user_id = fields.Many2one('res.users')
    other_note = fields.Text("Internal Note")
    contract_id = fields.Many2one('purchase.contract', string='Purchase Agreement', copy=False)
    is_fix_price=fields.Boolean(related="contract_id.is_fix_price",string="Fix")

    eq_fleet = fields.Many2one('model.equipment', "Equipment", related="request_id.eq_fleet")
    code = fields.Char(string='Code', related='eq_fleet.code')
    brand = fields.Char('Brand', related='eq_fleet.brand')
    model = fields.Char('Model', related='eq_fleet.model')
    year = fields.Integer('Year', related='eq_fleet.year')
    plate = fields.Char('Plate', related='eq_fleet.plate')
    is_fleet = fields.Boolean('Is Fleet')
    type = fields.Char('Type', related='eq_fleet.type')
    category = fields.Selection(string='Category', related='eq_fleet.category')
    vin = fields.Char('VIN.#', related='eq_fleet.vin')
    engine = fields.Char('Engine model', related='eq_fleet.engine')
    engine_serial = fields.Char('Engine serial No', related='eq_fleet.engine_serial')

    user_type = fields.Selection(related="request_id.user_type", string="Type")

    is_payment_request = fields.Boolean("Payment Request")

    requested_by = fields.Many2one('res.users', 'Requested by', track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True, readonly=True)

    landed_costs_ids = fields.One2many('stock.landed.cost', 'purchase_order_id', string='Landed Costs')
    landed_costs_visible = fields.Boolean(compute='_compute_landed_costs_visible')

    landed_costs_purcahse_ids = fields.One2many('purchase.landed.cost', 'purchase_order_id', string='Landed Costs')

    transporter_id = fields.Many2one("res.partner", "Transporter")

    total_landed_costs = fields.Float("LD COST Total", compute="get_total_cost")

    payment_line = fields.One2many(comodel_name="account.payment", inverse_name="purchase_id")

    weight_request_id = fields.Many2one("weight.request", "Scaling Request")


    analytic_account_id = fields.Many2one("account.analytic.account", "Analytic Account")

    payment_state = fields.Selection([
        ('draft', 'No Bill'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('unpaid', 'Unpaid')
    ], string='Bill Payment Status', compute='_compute_bill_payment_status', store=True, default='draft')

    confirmed = fields.Boolean(string='Is Confirmed', default=False)
    processed_days = fields.Integer(string='MR Processing Time', compute='_compute_days_processing', store=True)
    order_cycle_days = fields.Integer(string='PO Cycle Time', compute='_compute_days_cycle', store=True)
    sale_order_id = fields.Many2one('sale.order', string="Related Sale Order", readonly=True)
    po_overeas_ref=fields.Char("PO overseas NO.")
    supplier_overseas=fields.Many2one("res.partner","overseas Supplier")
    ovearseas_id=fields.Many2one("overseas.payment","Overseas Payment")
    
    company_code=fields.Char("")

    paid_amount = fields.Monetary(string='Paid Amount', compute='_compute_payment_info', store=True)
    amount_due = fields.Monetary(string='Amount Due', compute='_compute_payment_info', store=True)
    material_request_count = fields.Integer(
        string='Material Request Count',
        compute='_compute_material_request_count'
    )
    x_studio_transporter = fields.Many2one('res.partner')


    payment_company_id = fields.Many2one(
        "res.company",
        string="Paying Subsidiary",
    )

    def _compute_material_request_count(self):
        for po in self:
            po.material_request_count = len(po.request_ids)


    def action_view_material_requests(self):
        return {
            'name': "Material Requests",
            'type': 'ir.actions.act_window',
            'res_model': 'material.request',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('id', 'in', self.request_ids.ids)],
        }

    def transfer_request_id_to_requests(self):
        orders = self.env['purchase.order'].search([
            ('request_id', '!=', False)
        ])
        for order in orders:
            if order.request_id and order.request_id not in order.request_ids:
                order.request_ids = [(4, order.request_id.id)]

    @api.depends('invoice_ids.payment_state', 'invoice_ids.amount_residual', 'invoice_ids.amount_total')
    def _compute_payment_info(self):
        for order in self:
            total_paid = 0.0
            total_due = 0.0
            for invoice in order.invoice_ids:
                if invoice.state not in ['cancel']:
                    total_paid += invoice.amount_total - invoice.amount_residual
                    total_due += invoice.amount_residual
            order.paid_amount = total_paid
            order.amount_due = total_due


 





    def action_create_sale_order(self):
        """Create a Sales Order from this Purchase Order."""
        self.ensure_one()

        # Get the appropriate price list

        tax_id=self.env['account.tax'].search([('type_tax_use','=','sale')],limit=1)

        price_list = self.env['product.pricelist'].search([('currency_id', '=', self.currency_id.id)], limit=1)
        if not price_list:
            raise UserError(_("Please create pricelist with same currency of Purchase Order"))
        
        # Create the Sale Order
        sale_order = self.env['sale.order'].create({
            'partner_id': self.dest_address_id.id,
            'origin': self.name,
            'request_id': self.request_id.name,
            'mr_request_id': self.request_id.id,
            'mr_request_ids': self.request_ids,
            'pricelist_id': price_list.id,
            'company_id': self.company_id.id,
        })

        # Create Sale Order lines from the Purchase Order lines
        for line in self.order_line:
            vat_taxes = line.taxes_id.filtered(lambda t: 'vat' in t.name.lower())

            existing_line = sale_order.order_line.filtered(lambda l: l.product_id == line.product_id)
            if  existing_line:
            # # If the product already exists, update the quantity and price (if needed)
                existing_line.write({
                    'product_uom_qty': line.product_qty,  # Add the quantities together
                    'price_unit': line.price_unit  # Update the price if necessary
                })
                line.sale_line_id = existing_line  # Link the sale order line to the purchase order line

            else:
                line_id = self.env['sale.order.line'].create({
                    'order_id': sale_order.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_qty,
                    'price_unit': line.price_unit,
                    'product_uom': line.product_uom.id,
                    'name': line.name,
                    # 'tax_id' : tax_id if vat_taxes else False,

                })
                line.sale_line_id = line_id  # Link the sale order line to the purchase order line

        # Find the specific product (profit item/service)
        profit_product = self.env['product.product'].search([('is_profit_percentage', '=', True)], limit=1)
        if not profit_product:
            raise ValueError("Profit product (service) not found.")


        # Calculate the total amount of the sale order
        total_amount = sum(line.price_subtotal for line in sale_order.order_line)

        if profit_product:
            # Ensure the last line is set to the profit product with quantity 1
            last_line = sale_order.order_line.filtered(lambda l: l.product_id == profit_product)




        if last_line:
            # If the profit product already exists, update its quantity and price
            last_line.write({
                # 'product_uom_qty': 1,  # Set quantity to 1
                'product_uom_qty': line.product_qty,  # Set quantity to 1

                'price_unit': total_amount * 0.10  # Set the price to 10% of the total order amount
            })
        else:
            #If the profit product does not exist in the sale order, create a new line

            self.env['sale.order.line'].create({
                'order_id': sale_order.id,
                'product_id': profit_product.id,
                'name': profit_product.name,
                'product_uom_qty': 1,  # Set quantity to 1
                'product_uom': profit_product.uom_id.id,
                'price_unit': total_amount * 0.10,  # Set the price to 10% of the total order amount
            })

        # Link the sale order to the purchase order (if applicable)
        self.sale_order_id = sale_order.id

        self.sale_order_id.action_confirm()

        dropshipping_record=self.env['stock.picking'].search([("origin","=",self.name)],limit=1)
        dropshipping_record.button_validate()
        
        self.action_create_invoice()  # This returns the invoice(s) created

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
            'target': 'current',
        }

    # processing days
    @api.depends('assigned_data', 'date_approve', 'confirmed')
    def _compute_days_processing(self):
        for order in self:
            if order.confirmed:
                order.processed_days = 0
            elif order.assigned_data:
                if not order.date_approve:
                    # Calculate days since assigned if not approved
                    difference = (datetime.now() - order.assigned_data).days
                    order.processed_days = max(difference, 0)
                else:
                    # Calculate days between assigned and approved dates
                    difference = (order.date_approve - order.assigned_data).days
                    order.processed_days = difference
            else:
                order.processed_days = 0

    def _update_processed_days(self):
        today = fields.Datetime.now()
        records = self.search([('confirmed', '=', False)])  # Only get unconfirmed records

        for record in records:
            if record.assigned_data:
                delta_days = (today - record.assigned_data).days

                # Only update processed_days if the order is not confirmed
                if record.state != 'purchase':  # Adjust 'purchase' to your confirmed state
                    record.processed_days = max(delta_days, 0)  # Update only if it's unconfirmed
                # If the record is confirmed, do not change processed_days
            # No else clause to avoid resetting processed_days for confirmed records

    # Order Cycle days
    @api.depends('assigned_data', 'effective_date')
    def _compute_days_cycle(self):
        for order in self:
            if order.effective_date and order.assigned_data:
                difference = (order.effective_date - order.assigned_data).days
                order.order_cycle_days = difference
            else:
                order.order_cycle_days = 0
                _logger.warning("One of the dates is missing: assigned_data=%s, effective_date=%s", order.assigned_data,
                                order.effective_date)

    # Payment Status
    @api.depends('invoice_ids', 'invoice_ids.payment_state')
    def _compute_bill_payment_status(self):
        for order in self:
            invoices = order.invoice_ids.filtered(lambda inv: inv.is_purchase_document())
            if not invoices:
                order.payment_state = 'draft'
            elif all(inv.payment_state == 'paid' for inv in invoices):
                order.payment_state = 'paid'
            elif any(inv.payment_state == 'partial' for inv in invoices):
                order.payment_state = 'partial'
            else:
                order.payment_state = 'unpaid'

    def _prepare_invoice(self):
        res = super(PurchaseOrder, self)._prepare_invoice()
        res['invoice_date'] = fields.Date.today()
        return res

    def action_advance_payment(self):
        return {
            "name": _("Advance Payment"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "advance.payments.wizard",
            "view_id": self.env.ref("material_request.advance_payments_purchase_wizard_form_view").id,
            "type": "ir.actions.act_window",
            "target": "new"
        }

    @api.depends('landed_costs_purcahse_ids')
    def get_total_cost(self):
        total = 0.0
        for rec in self.landed_costs_purcahse_ids:
            total += rec.subprice_total
        self.total_landed_costs = total

    @api.model
    def action_multiple_confirm(self):
        for order in self:
            if order.state == 'ccso':
                order.button_confirm()
            elif order.state == 'site':
                order.button_confirm()
            else:
                raise UserError(_("Th Po status is not in ccso or Operation Director,cannnot approve"))

    ###################landed cost

    @api.depends('order_line', 'order_line.is_landed_costs_line')
    def _compute_landed_costs_visible(self):
        for purchase_order in self:
            if purchase_order.landed_costs_ids:
                purchase_order.landed_costs_visible = False
            else:
                purchase_order.landed_costs_visible = any(
                    line.is_landed_costs_line for line in purchase_order.order_line)

    #################################landed cost function for scm purchase#########3

    def make_landed_cost_in_po(self):

        view_id = self.env.ref('stock_landed_costs.view_stock_landed_cost_form')

        return {
            'name': _('Landed Cost'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.landed.cost',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_purchase_order_id': self.id,
                'default_picking_ids': self.picking_ids.ids,
                'default_company_id': self.company_id.id,
                'default_analytic_account': self.analytic_account_id.id,
            }
        }


 
    ##################landed cost function for rock purchases################3#######33
    ###############################2023/10/02/###############################
    def button_create_landed_costs(self):
        """Create a `stock.landed.cost` record associated to the account move of `self`, each
        `stock.landed.costs` lines mirroring the current `account.move.line` of self.
        """
        self.ensure_one()
        p_state = False
        analytic = self.env['account.analytic.account'].search(
            [('partner_id', '=', self.partner_id.id)],
            limit=1
        )
        for rec in self.picking_ids:
            if rec.state == 'done':
                p_state = True
        if not p_state:
            # if not self.is_shipped:
            raise UserError(_("Please Validate the receipts"))
        landed_costs_obj = self.env['stock.landed.cost'].search(
            [('purchase_order_id', '=', self.id), ('state', '=', 'done')])
        if landed_costs_obj:
            raise UserError(_("The landed Cost Alrealy createed"))

        landed_costs_lines = self.order_line.filtered(lambda line: line.is_landed_costs_line)

        if not self.x_studio_transporter:
            raise UserError(_("Please write the Transporter"))
        receipts = self.env['stock.picking'].search(
            [('purchase_id', '=', self.id), ('state', 'in', ['assigned', 'done'])])
        lc_journal = self.env['account.journal'].search([('code', '=', 'STJ'), ('company_id', '=', self.company_id.id)],
                                                        limit=1)

        accounts = self.product_id.product_tmpl_id._get_product_accounts()

        landed_costs = self.env['stock.landed.cost'].create({
            'purchase_order_id': self.id,
            'partner_id': self.x_studio_transporter.id,
            'picking_ids': receipts,
            'company_id': self.company_id.id,
            'account_journal_id': lc_journal.id,
            'analytic_account_id': analytic.id if analytic else self.analytic_account_id.id,

            'cost_lines': [(0, 0, {
                'product_id': l.product_id.id,
                'name': l.product_id.name,
                'product_qty': l.product_qty,
                # 'account_id': 3278,
                'price_unit': l.product_qty * abs(
                    l.currency_id._convert(l.price_unit, l.company_currency_id, l.company_id, l.order_id.create_date)),
                'currency_price_unit': l.product_qty * abs(
                    l.currency_id._convert(l.price_unit, l.company_currency_id, l.company_id, l.order_id.create_date)),
                'split_method': l.product_id.split_method_landed_cost or 'equal',
            }) for l in landed_costs_lines],
        })
        action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")

        for rec in landed_costs.picking_ids:
            if rec.state == "done" and landed_costs.state != 'done':
                landed_costs.sudo().button_validate()
                landed_costs.create_transporter_invoices()

        return dict(action, view_mode='form', res_id=landed_costs.id, views=[(False, 'form')])

    def action_view_landed_costs(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")
        domain = [('id', 'in', self.landed_costs_ids.ids)]
        context = dict(self.env.context, default_vendor_bill_id=self.id)
        views = [(self.env.ref('stock_landed_costs.view_stock_landed_cost_tree2').id, 'list'), (False, 'form'),
                 (False, 'kanban')]
        return dict(action, domain=domain, context=context, views=views)

    def action_view_overseas_payment(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("material_request.payment_request_form_approve_action")
        domain = [('purchase_order_id', '=', self.id)]
        context = dict(self.env.context, default_vendor_bill_id=self.id)
        views = [(self.env.ref('material_request.view_ovearseas_payment_tree').id, 'list'), (False, 'form'),
                 (False, 'kanban')]
        return dict(action, domain=domain, context=context, views=views)





    def button_cancel(self):
        super(PurchaseOrder, self).button_cancel()
        for rec in self:
            services = self.env['service.requisition'].search([('purchase_id', '=', rec.id)])
            services.button_cancel()

    def get_requested_by(self):
        user = self.env.user.id
        return user

    def activity_update(self):
        for rec in self:
            message = ""
            if rec.state == 'line_approve':
                # Get the line manager of the current user
                line_manager = rec.user_id.line_manager_id if rec.user_id.line_manager_id else None
                if line_manager:
                    message = " for Ugrent and Kindly Approval"
                    self.activity_schedule('master_data.mail_act_master_data_approval', user_id=line_manager.id, note=message)
            else:
                continue


    def weight(self):
        self.state = 'weight'

    def line_approve(self):
        for rec in self:

            line_manager = False
            line_line_manager = False
            try:
                line_manager = self.requested_by.line_manager_id
            except:
                line_manager = False
            if not line_manager or line_manager != self.env.user:
                raise UserError("Line manger is not set!")

            rec.write({'state': 'contract_manager'})

    # user submit
    def submit(self):
        for rec in self:

            if not self.requested_by.id == self.env.user.id:
                raise UserError('Sorry, Only requester can submit this document!')
            rec.write({'state': 'line_approve'})
            self.activity_update()

    def go_to_prm(self):
        for rec in self:


            for line in rec.order_line:
                if rec.request_id.purchase_type == 'overseas' and line.analytic_distribution:
                    line.analytic_distribution = False
                


            if rec.request_id.item_type == 'service' and rec.request_id.user_type == 'hq':
                rec.state = 'contract_manager'
            else:
                rec.state = 'sum'

    def make_ovearses(self):
        for rec in self:

            if rec.request_id.purchase_type == 'overseas' or rec.purchase_type =='overseas':
                ovearseas_payment = self.env['overseas.payment'].create({
                    'title': self.request_id.title,
                    'request_id': self.request_id.id,
                    'purchase_order_id': self.id,
                    'purchase_order': self.name,
                    'amount_total': self.amount_total,
                    'amount_to_pay': self.amount_total,
                    'currency_id': self.currency_id.id,
                    'company_id': self.company_id.id,
                    'payment_company_id': self.payment_company_id.id ,
                    'contract_id': self.contract_id.id,
                    'is_contract': True,
                    'department_id': self.department_id.id,
                    'material_request_id': self.request_id.id,

                    
                })

                rec.ovearseas_id=ovearseas_payment.id
                rec.ovearseas_id.state='scd'

    def make_ovearses_wizard(self):
        for rec in self:
            default_amount = rec.amount_total if rec.paid_amount == 0 else rec.amount_due

            if rec.request_id.purchase_type != 'overseas' and not rec.contract_purchased:
                raise UserError("This purchase payment in MR is not marked as Overseas.")

            if rec.request_id.purchase_type == 'overseas' or rec.purchase_type =='overseas':
                existing_payment = self.env['overseas.payment'].search(
                    [('purchase_order_id', '=', rec.id)], limit=1)
                if existing_payment and rec.amount_due==0.0:
                    raise UserError("The Overseas Payment is already created.")

                return {
                    'name': 'Enter Amount to Pay',
                    'type': 'ir.actions.act_window',
                    'res_model': 'overseas.payment.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': 
                    {'default_amount_to_pay': default_amount,
                    'default_department_id': self.department_id.id,
                    'default_contract_id': self.contract_id.id,
                    'default_material_request_id': self.request_id.id,
                    'default_company_id': self.company_id.id,
                    'default_currency_id': self.currency_id.id,
                     },
                        }


    def go_to_sum(self):
        for rec in self:

            if rec.request_id:
                if rec.is_payment_request:
                    self.button_confirm()
                else:

                    if rec.supply_user.user_type == 'site':
                        return rec.write({'state': 'sud'})
                    # elif rec.supply_user_type == 'hq':
                    elif rec.supply_user.user_type == 'hq':
                        return rec.write({'state': 'sud'})
                    elif rec.ore_purchased:
                        return rec.write({'state': 'site'})
                    ###############################add new line##########
                    #####################ekhlas code #############
                    elif rec.supply_user.user_type == 'fleet':
                        return rec.write({'state': 'sud'})
                    elif rec.supply_user.user_type == 'rohax':
                        return rec.write({'state': 'sud'})
                    else:
                        raise UserError("Thr Employee Has No Type")
            else:
                return rec.write({'state': 'sud'})

    def go_to_sud(self):
        for rec in self:
            if rec.request_id:
                if rec.supply_user.user_type == 'site':
                    return rec.write({'state': 'ccso'})
                elif rec.supply_user.user_type == 'hq':
                    return rec.write({'state': 'ccso'})
                ###############################add new line##########
                elif rec.supply_user.user_type == 'fleet':
                    return rec.write({'state': 'ccso'})
                elif rec.supply_user.user_type == 'rohax':
                    return rec.write({'state': 'ccso'})
                else:
                    raise UserError("The Employee Has No Type")


            else:
                return rec.write({'state': 'ccso'})


    def go_to_fm(self):
        for rec in self:
            if rec.request_id.purchase_type=='overseas' and rec.ovearseas_id:
                rec.ovearseas_id.state='close'
                rec.ovearseas_id.fm_date=datetime.today()
                rec.ovearseas_id.fm_approved_by=rec.env.user.id


    def go_to_ccso(self):
        for rec in self:
            if rec.supply_user.user_type == 'site' and rec.ore_purchased == False:
                return rec.write({'state': 'ccso'})
            #########################add new line #############
            ######################ekhlas code################3            
            if rec.supply_user.user_type == 'fleet':
                return rec.write({'state': 'ccso'})
            if rec.ore_purchased == True:
                return rec.write({'state': 'site'})

            else:
                return rec.write({'state': 'ccso'})

    def action_reject(self):
        self.state = 'reject'

    @api.depends('request_id')
    def get_has_mr(self):
        self.has_mr = True if self.request_id else False

    def button_confirm(self):
        for order in self:
            # Always call super first (this sets PO state = purchase)
            res = super(PurchaseOrder, self).button_confirm()
            for order in self:
                # ------------------------------
                # 🔷 UPDATE Qty In PO (your requirement)
                # ------------------------------
                for line in order.order_line:
                    for req in order.request_ids:
                        mr_lines = self.env['material.request.line'].search([
                            ('request_id', '=', req.id),
                             ('company_id', '=','record.company_id.id'),
                            ('product_id', '=', line.product_id.id),
                        ])
                        for mr in mr_lines:
                            mr.qty_in_po += line.product_qty


            #     continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.po_double_validation == 'one_step' \
                    or (order.company_id.po_double_validation == 'two_step' \
                        and order.amount_total < self.env.company.currency_id._convert(
                        order.company_id.po_double_validation_amount, order.currency_id, order.company_id,
                        order.date_order or fields.Date.today())) \
                    or order.user_has_groups('purchase.group_purchase_manager'):
                order.button_approve()
                ##############ekhlas code
                order.request_id.state = 'purchased'
            else:
                order.write({'state': 'to approve'})

            #############################################inspection material##########################
            if not (
                    self.company_id.id != self.request_id.company_id.id and self.request_id.purchase_type == 'overseas') and self.requested_by.user_type != 'rohax':
                if not order.ore_purchased and self.picking_type_id.code == 'incoming':
                    env = self.env(user=1)
                    inspection_line_ids = []
                    if self.order_line:
                        for rec in self.order_line:
                            if rec.product_id.type != 'service' and rec.product_id.id:
                                product_uom = rec.product_uom_id  # Current UoM in the order line
                                original_uom = rec.product_id.uom_id  # Product's original UoM

                                # Convert the ordered quantity to the original UoM
                                qty_converted = product_uom._compute_quantity(rec.product_qty, original_uom)

                                inspection_line_ids.append(
                                    (0, 0,
                                     {'product_id': rec.product_id.product_tmpl_id.id,
                                      'product_uom_id': original_uom.id,
                                      'qty_on_bill': qty_converted, 'qty_received': rec.qty_received}))
                        if inspection_line_ids:
                            res = env['material.inspection'].create(
                                {'vendor_id': self.partner_id.id,
                                 'inspection_ids': inspection_line_ids,
                                 'po_number': self.name,
                                 'purchase_id': self.id,
                                 'material_request_id': self.request_id.id,
                                 'material_request_ids': self.request_ids,
                                 })

            if self.request_id.purchase_type=='overseas' and self.dest_address_id:
                self.action_create_sale_order()
            ###############################################################################################
            if order.contract_id :

                if not order.contract_purchased:
                    raise UserError("Please make the 'Is Payment Contract' CHECKED")

                if  self.request_id.purchase_type=='overseas' or self.purchase_type =='overseas':
                    if not self.payment_company_id:
                        raise UserError("Please Enter the Paying Subsidiary")
                order.action_create_invoice()
                order.make_ovearses()


            if order.ore_purchased:
                order.weight_request_id.state = 'done'
                for record in order.order_line:
                    for recordd in order.picking_ids.move_ids:
                        recordd.batch_no = record.batch_No

                if order.weight_request_id:
                    landed_cost = self.env['stock.landed.cost'].search([
                        ('weight_id', '=', order.weight_request_id.id)
                    ], limit=1)
                    if landed_cost:
                          landed_cost.purchase_order_id = order.id
        if self.request_id:
            self.request_id.sudo().write({'state': 'purchased'})

        for order in self:
            if order.request_ids:
                order.request_ids.sudo().write({'state': 'purchased'})

        ###################### Lots And serial with stock picking
        for order in self:
            if order.picking_ids:  # Check if there are related pickings
                for picking in order.picking_ids:  # Iterate over related stock pickings
                    for move in picking.move_ids:  # Iterate over stock moves
                        for line in order.order_line:
                            if line.product_id == move.product_id:
                                move.average = line.average
                                # Propagate lot/batch information
                                for m in move.move_line_ids:
                                    m.lot_id = line.lot_id.id
                                    m.lot_name = line.lot_id.name
        ########################################################s
        return True
        super(PurchaseOrder, self).button_confirm()

    #####################added by ekhlas code ##########################

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        if not self.contract_id:
            return

        self = self.with_company(self.company_id)
        contract = self.contract_id
        if self.partner_id:
            partner = self.partner_id
        else:
            partner = contract.vendor_id
        payment_term = partner.property_supplier_payment_term_id

        FiscalPosition = self.env['account.fiscal.position']
        # fpos = FiscalPosition.with_company(self.company_id).get_fiscal_position(partner.id)

        fpos = FiscalPosition.with_company(self.company_id)._get_fiscal_position(partner)

        # fpos = self.env['account.fiscal.position']._get_fiscal_position(self.partner_id)
        self.partner_id = partner.id
        self.fiscal_position_id = fpos.id
        self.payment_term_id = payment_term.id,
        self.company_id = contract.company_id.id
        self.currency_id = contract.currency_id.id
        if not self.origin or contract.name not in self.origin.split(', '):
            if self.origin:
                if contract.name:
                    self.origin = self.origin + ', ' + contract.name
            else:
                self.origin = contract.name
        self.note = contract.description
        self.date_order = fields.Datetime.now()

        # Create PO lines if necessary
        order_lines = []
        for line in contract.line_ids:
            # Compute name
            product_lang = line.product_id.with_context(
                lang=partner.lang or self.env.user.lang,
                partner_id=partner.id
            )
            name = product_lang.display_name
            if product_lang.description_purchase:
                name += '\n' + product_lang.description_purchase

            # Compute taxes
            taxes_ids = fpos.map_tax(
                line.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == contract.company_id)).ids

            # Compute quantity and price_unit
            if line.product_uom_id != line.product_id.uom_id:
                product_qty = line.product_uom_id._compute_quantity(line.product_qty, line.product_id.uom_id)
                price_unit = line.product_uom_id._compute_price(line.price_unit, line.product_id.uom_id)
            else:
                product_qty = line.product_qty
                price_unit = line.price_unit

            # Create PO line
            order_line_values = line._prepare_purchase_order_line(
                name=name, product_qty=product_qty, price_unit=price_unit,
                taxes_ids=taxes_ids)
            order_lines.append((0, 0, order_line_values))
        self.order_line = order_lines

    @api.model
    def create(self, vals):
        purchase = super(PurchaseOrder, self).create(vals)
        if purchase.contract_id:
            message = f"Linked with contract: {purchase.contract_id.name}"
            subtype_id = self.env.ref('mail.mt_note').id  # Correctly fetch the subtype
            purchase.message_post(body=message, subtype_id=subtype_id)
        return purchase

    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        :return: An action opening the account.payment.register wizard.
        '''
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'purchase.order',
                'active_ids': self.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }


class PurchaseOrderRejectionWizard(models.TransientModel):
    _name = "purchase.order.rejection.wizard"
    reason_reject = fields.Text("Rejection Reason")

    def action_validate(self):
        self.ensure_one()
        context = dict(self._context or {})
        active_model = self.env.context.get('active_model')
        active_id = self.env.context['active_ids']

        order = self.env[active_model].browse(active_id)

        if self.reason_reject:
            order.state = 'reject'
            order.reason_reject = self.reason_reject
            message = """
            This document was rejected by: %s <br/>
            Rejection Reason:%s 
            """ % (self.env.user.name, self.reason_reject)
            order.message_post(body=message)

        return {'type': 'ir.actions.act_window_close'}


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    request_line_id = fields.Many2one('material.request.line', 'requisition', ondelete='set null', index=True,
                                      readonly=True)
    request_id = fields.Many2one('material.request', related='order_id.request_id', string='Requisition Order',
                                 store=False, readonly=True, related_sudo=False, )
    part_number = fields.Char(related="product_id.part_number", string="Part-Nmuber")
    batch_No = fields.Char("Batch Number")
    lot_id = fields.Many2one(comodel_name="stock.lot", string="Lots Batch")
    average = fields.Float("Average")
    is_landed_costs_line = fields.Boolean()
    equ_id = fields.Many2one(comodel_name="maintenance.equipment", string="Equipment", required=False, )

    company_currency_id = fields.Many2one(string='Company Currency', readonly=True,
                                          related='company_id.currency_id')

    account_analytic_id = fields.Many2one("account.analytic.account", string="Cost Center")
    is_fix_price=fields.Boolean(related="order_id.is_fix_price",string="Fix")

    incentive_price = fields.Float("Bonus/Discount")
    percentage = fields.Float(string="Percentage (%)")

    self_deportation = fields.Boolean(
        related='product_id.self_deportation',
        string='Self Deportation',
        store=True,
        readonly=True
    )


    @api.depends('product_qty', 'product_uom_id', 'company_id')
    def _compute_price_unit_and_date_planned_and_name(self):
        for line in self:
            if not line.product_id or line.invoice_lines or not line.company_id:
                continue
            if line.order_id.contract_id:
                continue

            params = line._get_select_sellers_params()
            seller = line.product_id._select_seller(
                partner_id=line.partner_id,
                quantity=line.product_qty,
                date=line.order_id.date_order and line.order_id.date_order.date() or fields.Date.context_today(line),
                uom_id=line.product_uom_id,
                params=params)

            if seller or not line.date_planned:
                line.date_planned = line._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

            # If not seller, use the standard price. It needs a proper currency conversion.
            if not seller:
                line.discount = 0
                unavailable_seller = line.product_id.seller_ids.filtered(
                    lambda s: s.partner_id == line.order_id.partner_id)
                if not unavailable_seller and line.price_unit and line.product_uom_id == line._origin.product_uom_id:
                    # Avoid to modify the price unit if there is no price list for this partner and
                    # the line has already one to avoid to override unit price set manually.
                    continue
                po_line_uom = line.product_uom_id or line.product_id.uom_id
                price_unit = line.env['account.tax']._fix_tax_included_price_company(
                    line.product_id.uom_id._compute_price(line.product_id.standard_price, po_line_uom),
                    line.product_id.supplier_taxes_id,
                    line.tax_ids,
                    line.company_id,
                )
                price_unit = line.product_id.cost_currency_id._convert(
                    price_unit,
                    line.currency_id,
                    line.company_id,
                    line.date_order or fields.Date.context_today(line),
                    False
                )
                line.price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places, self.env['decimal.precision'].precision_get('Product Price')))

            elif seller:
                if line.order_id.contract_id:
                    continue

                    price_unit = line.env['account.tax']._fix_tax_included_price_company(seller.price, line.product_id.supplier_taxes_id, line.taxes_id, line.company_id) if seller else 0.0
                    price_unit = seller.currency_id._convert(price_unit, line.currency_id, line.company_id, line.date_order or fields.Date.context_today(line), False)
                    price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places, self.env['decimal.precision'].precision_get('Product Price')))
                    line.price_unit = seller.product_uom_id._compute_price(price_unit, line.product_uom_id)
                    line.discount = seller.discount or 0.0

            # record product names to avoid resetting custom descriptions
            default_names = []
            vendors = line.product_id._prepare_sellers({})
            product_ctx = {'seller_id': None, 'partner_id': None, 'lang': get_lang(line.env, line.partner_id.lang).code}
            default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
            for vendor in vendors:
                product_ctx = {'seller_id': vendor.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
            if not line.name or line.name in default_names:
                product_ctx = {'seller_id': seller.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                line.name = line._get_product_purchase_description(line.product_id.with_context(product_ctx))

            super(PurchaseOrderLine, self)._compute_price_unit_and_date_planned_and_name()





    def _prepare_account_move_line(self, move=False):
        super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        self.ensure_one()
        aml_currency = move and move.currency_id or self.currency_id
        # Ensure that the analytic ID exists
        analytic_distribution = []
        for rec in self.account_analytic_id:
            if rec:
                analytic_distribution.append((0, 0, {
                    'analytic_account_id': rec.id,
                    'amount': 100.0  # Adjust this as per your logic
                }))
        date = move and move.date or fields.Date.today()
        res = {
            'sequence': self.sequence,
            'name': '%s: %s' % (self.order_id.name, self.name),
            'product_id': self.product_id.id,
            'equipment_id': self.equ_id.id,
            'discount': self.discount,
            'product_uom_id': self.product_uom_id.id,
            'quantity': self.qty_to_invoice,
            'price_unit': self.currency_id._convert(self.price_unit, aml_currency, self.company_id, date, round=False),
            'tax_ids': [(6, 0, self.tax_ids.ids)],
            'analytic_distribution': self.analytic_distribution,
            'purchase_line_id': self.id,
            'is_landed_costs_line': self.is_landed_costs_line,

        }
        account_id = self.product_id.product_tmpl_id.property_account_expense_id
        if account_id and self.product_id.landed_cost_ok==True:
            if self.discount !=0:
                res['account_id'] = account_id.id
        if not move:
            return res

        if self.currency_id == move.company_id.currency_id:
            currency = False
        else:
            currency = move.currency_id

        res.update({
            'move_id': move.id,
            'currency_id': currency and currency.id or False,
            'date_maturity': move.invoice_date_due,
            'partner_id': move.partner_id.id,
        })
        return res

    @api.depends('product_id', 'date_order')
    def _compute_account_analytic_id(self):
        for rec in self:
            if rec.account_analytic_id:
                pass
            else:
                if not rec.display_type:
                    default_analytic_account = rec.env['account.analytic.default'].sudo().account_get(
                        product_id=rec.product_id.id,
                        partner_id=rec.order_id.partner_id.id,
                        user_id=rec.env.uid,
                        date=rec.date_order,
                        company_id=rec.company_id.id,
                    )
                    rec.account_analytic_id = default_analytic_account.analytic_id


    @api.onchange('is_landed_costs_line')
    def _onchange_is_landed_costs_line(self):
        """Mark an invoice line as a landed cost line and adapt `self.account_id`. The default
        value can be set according to `self.product_id.landed_cost_ok`."""
        if self.product_id:
            accounts = self.product_id.product_tmpl_id._get_product_accounts()
            if self.product_type != 'service':
                self.is_landed_costs_line = False

    @api.onchange('product_id')
    def _onchange_is_landed_costs_line_product(self):
        if self.product_id.landed_cost_ok:
            self.is_landed_costs_line = True
        else:
            self.is_landed_costs_line = False

    @api.onchange('order_id.analytic_account_id')
    def get_analytic_account(self):
        for rec in self:
            rec.account_analytic_id = order_id.analytic_account_id


    def _onchange_eval(self, field_name, onchange, result):
        """Remove the trigger for the undesired onchange method with this field.
        We have to act at this place, as `_onchange_methods` is defined as a
        property, and thus it can't be inherited due to the conflict of
        inheritance between Python and Odoo ORM, so we can consider this as a HACK.
        """
        ctx = self.env.context
        if field_name == "product_qty" and (
                not config["test_enable"]
                or (config["test_enable"] and ctx.get("prevent_onchange_quantity", False))
        ):
            cls = type(self)
            for method in self._onchange_methods.get(field_name, ()):
                if method == cls._onchange_quantity:
                    self._onchange_methods[field_name].remove(method)
                    break
        return super()._onchange_eval(field_name, onchange, result)


class PurchaseLandedCOST(models.Model):
    _name = 'purchase.landed.cost'

    name = fields.Char("Name")
    product_id = fields.Many2one("product.product", "Product")
    product_qty = fields.Float("Quantity")
    unit_price = fields.Float("Unit Price")
    subprice_total = fields.Float("Total Price", compute="get_total")
    purchase_order_id = fields.Many2one("purchase.order", "Purchase Order")

    @api.depends('product_qty', 'unit_price')
    def get_total(self):
        for rec in self:
            rec.subprice_total = rec.product_qty * rec.unit_price


class AccountPayment(models.Model):
    _inherit = "account.payment"

    purchase_id = fields.Many2one(comodel_name="purchase.order", string="Purchase Order")
    landed_cost_id = fields.Many2one(comodel_name="stock.landed.cost", string="Landed Costs")

    @api.model_create_multi
    def create(self, vals_list):
        # 1. Create the records first using the standard Odoo logic
        payments = super(AccountPayment, self).create(vals_list)

        # 2. Iterate through the created payments and their corresponding vals
        for pay, vals in zip(payments, vals_list):
            ref = vals.get('ref')
            if ref:
                # Search for matching Purchase Order
                purchase = self.env["purchase.order"].search([("name", "=", ref)], limit=1)
                if purchase:
                    pay.purchase_id = purchase.id

                # Search for matching Landed Cost
                landed = self.env["stock.landed.cost"].search([("name", "=", ref)], limit=1)
                if landed:
                    pay.landed_cost_id = landed.id

        return payments
