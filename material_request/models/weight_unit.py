from odoo import models, fields, api, _
from odoo import models, fields, api, exceptions, _
from odoo.tools import format_datetime
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.exceptions import UserError, ValidationError
import dateutil
from dateutil.relativedelta import relativedelta
# Import statistics Library
import statistics
import re

# import numpy as np

_STATES = [
    ('draft', 'Draft'),
    ('db_geologist', 'Sampling'),
    ('chem_lab', 'Chem-Lab Assaying'),
    ('db_price', 'Waiting Pricing '),
    ('rock_user', 'Waiting Rock Purchaser  '),
    ('done', 'Purchase Order'),
    ('reject', 'Rejected'),
    ('cancel', 'Cancelled'),
    ('waiting_rock', 'Waiting Rock Approve'),
    ('close', 'Closed'),
]

_CSTATES = [
    ('draft', 'Draft'),
    ('generate', 'Generate Samples'),
    ('receive', 'Waiting  Preparation Lab'),
    ('assay', 'Waiting Chem-Lab Assaying'),

    ('close', 'Closed'),
    ('reject', 'Rejected'),

    ('cancel', 'Cancelled'),

]

_PSTATES = [
    ('draft', 'Draft'),
    ('approved', 'Approved'),

]


class WeightRequest(models.Model):
    _name = "weight.request"

    _description = 'Weight Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _rec_name = 'name'
    _order = 'date_request desc'

    def _default_analytic_account_id(self):
        if self.env.user.default_analytic_account_id.id:
            return self.env.user.default_analytic_account_id.id

    name = fields.Char('WR Number', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    car_id = fields.Many2one("transportation.car", "Car No.")
    car_plate = fields.Char(related="car_id.car_plate", string="Plate license No.")
    driver_id = fields.Many2one(related="car_id.driver_id", string="Driver")
    transporter_id = fields.Many2one(related="car_id.transporter_id", string="Transporter" , track_visibility='onchange')
    rock_vendor = fields.Many2one("res.partner", "Rock Vendor" , track_visibility='onchange')
    quantity = fields.Float("Quantity" , track_visibility='onchange')
    area_id = fields.Many2one("x_area", "Area", required=True , track_visibility='onchange')
    state = fields.Selection(selection=_STATES, string='Status', index=True, track_visibility='onchange', readonly=True,
                             required=True, copy=False, default='draft')
    external_visit_state = fields.Selection(related='state')
    date_request = fields.Datetime("Request Date/Time ", default=fields.Datetime.now, required=True)
    requested_by = fields.Many2one('res.users', 'Requested by', track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True, readonly=True)

    request_samples_ids = fields.One2many("weight.samples", "request_id", "Samples for Chemical")

    chemical_samples_ids = fields.One2many("chemical.samples.request", "request_id", "Chemical Request")

    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id)
    chemical_assay_request_count = fields.Integer(string="Count", compute='compute_chemical_assay_count')
    reason_reject = fields.Text("Rejection Reason", track_visibility="onchange")

    batch = fields.Char("Batch")
    store = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="stored after analysis")
    dump = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="dumped after analysis")
    oven = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Oven Option for Samples")
    is_sack = fields.Boolean( string="Is Sack")

    disposal_info = fields.Char(default="STRUCTION FOR DISPOSAL OF SAMPLES AND RECEIPT OF RESULTS", readonly="1")

    store_time = fields.Float("Hours")
    dump_time = fields.Float("Hours")
    oven_time = fields.Float("Hours")

    average = fields.Float("Average Grade")
    # average=fields.Float("Average",compute="get_average")
    qy_average = fields.Float("Qty/Avg", compute="get_total",store=True)
    # product_id=fields.Many2one("product.product",string="Product")
    analytic_account_id = fields.Many2one("account.analytic.account",
                                          string="Analytic Account", )
    # unit_price=fields.Float("Unit Price",compute="get_price")
    line_ids = fields.One2many('weight.request.line', 'weight_id', 'Products to Purchase', readonly=False, copy=True)
    landed_cost_line_ids = fields.One2many('weight.request.landedcost.line', 'weight_id', 'Landed Cost', readonly=False)
    purchase_count = fields.Integer(string="Count", compute='compute_purchase_count')
    sample_no_from = fields.Integer("Sample  From ")
    sample_no_to = fields.Integer("Sample  To ")
    geologist = fields.Many2one('hr.employee', string='Geologist')

    po_request = fields.Date("Po Date/Time ")

    submit_date = fields.Datetime(string='Submit Date')
    ####### External Visti Code #
    rock_note = fields.Html(string="Note")
    form_type = fields.Selection(
        [('scaling_unit', 'Scaling Unit'),
         ('external_sample', 'External Sample'),
         ('external_visit', 'External Visit')],
        string='Request Type', default='scaling_unit'
    )
    geology_sample_ids = fields.One2many(
        'geology.sample',
        'weight_request_id',
        string="Geology Samples"
    )
    partner_id = fields.Many2one("res.partner", string="Vendor")
    select_all_record = fields.Boolean(string="Apply For All Samples")
    type_ore = fields.Selection([
        ('mvol','M,vol'),
         ('qtz', 'Qtz'),
         ('sbr', 'SBR'),
         ('gs', 'GS')],
         string='Ore Type'
    )
    weight_type = fields.Selection([
        ('trucks', 'TRUCKS'),
        ('sacks', 'SACKS'),],
        string='Weight type'
    )

    north = fields.Integer("Northing")
    east = fields.Integer("Easting")
    elevation = fields.Integer("Elevation")
    sample_position = fields.Selection([
        ('hr', 'Host Rock'),
        ('bc', 'Body Contact'),
        ('vein', 'Vein'),
        ('ds', 'Dums'),
    ], string="Sample Position")
    rock_type = fields.Selection([
        ('qtz', 'Quartz (Qtz)'),
        ('m_vol', 'Metavolcanic (M.Vol)'),
        ('chrt' , 'CHRT'),
    ], string="Rock Type")
    dip_strike = fields.Integer(string="DIP/Strike")
    lot_id = fields.Many2one(comodel_name="stock.lot", string="Lots Batch")
    landed_costs_count = fields.Integer(string="Count", compute='compute_landed_costs_count')
    is_opu_po = fields.Boolean(string='Is MATERIAL MINDS PO', compute='_compute_is_opu_po', store=True)
    x_studio_supplier_type = fields.Many2many("res.partner.category",)


    @api.depends('x_studio_supplier_type')
    def _compute_is_opu_po(self):
        for order in self:
            order.is_opu_po = any(
                tag.name == 'MATERIAL MINDS'
                for tag in order.x_studio_supplier_type
            )

    def _update_company_share_line(self):
        for request in self:
            ore_total = 0.0
            company_line = None

            for line in request.line_ids:
                if line.product_id.is_company_percentage:
                    company_line = line
                elif line.product_id.type == 'product':
                    ore_total += line.total

            if company_line:
                company_line.product_qty = 1
                company_line.discount = 0.0
                company_line.unit_price = (
                    (ore_total * company_line.percentage) / 100
                    if company_line.percentage else 0.0
                )



    def _add_company_share_line(self):
        Product = self.env['product.product']

        analytic = self.env['account.analytic.account'].search(
            [('partner_id', '=', self.rock_vendor.id)],
            limit=1
        )
        # self.analytic_account_id = analytic.id if analytic else False

        # Find Company Share product - ensure this exists in your system!
        company_share_product = Product.search([('is_company_percentage', '=',True)], limit=1)
        if not company_share_product:
            raise UserError("Product 'Company Share' not found. Please create it first.")

        # Avoid adding duplicate company share line
        if self.line_ids.filtered(lambda l: l.product_id == company_share_product):
            return

        # Add the line with qty=1 and price_unit=0 (price calculated on line onchange)
        self.line_ids = [(0, 0, {
            'product_id': company_share_product.id,
            'product_qty': 1,
            'unit_price': 0.0,
            'percentage': 70,
            'analytic_account_id':analytic.id if analytic else False
            # 'name': company_share_product.name,
        })]


    def _partner_has_opu_tag(self):
        return any(tag.name == 'MATERIAL MINDS' for tag in self.x_studio_supplier_type)


    @api.onchange('rock_vendor')
    def _onchange_partner_id_add_company_share(self):
        for order in self:
            if not order.rock_vendor:
                continue
            if not order._partner_has_opu_tag():
                continue
            order._add_company_share_line()



    def compute_landed_costs_count(self):
        self.landed_costs_count = self.env['stock.landed.cost'].search_count([('weight_id', '=', self.id)])


    def set_landed_costs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Landed Costs',
            'view_mode': 'list,form',
            'res_model': 'stock.landed.cost',
            'domain': [('weight_id', '=', self.id)],
            'context': "{'create': False}"
        }
    def button_create_landed_costs(self):
        self.ensure_one()

        analytic = self.env['account.analytic.account'].search(
            [('partner_id', '=', self.rock_vendor.id)],
            limit=1
        )

        if not self.landed_cost_line_ids:
            raise UserError("No landed cost lines found. Please add them before proceeding.")

        landed_costs_obj = self.env['stock.landed.cost'].search(
            [('weight_id', '=', self.id), ('state', '=', 'done')])
        if landed_costs_obj:
            raise UserError("The landed Cost Alrealy createed")

        lc_journal = self.env['account.journal'].search([('code', '=', 'STJ'), ('company_id', '=', self.company_id.id)],
                                                        limit=1)
        landed_costs = self.env['stock.landed.cost'].create({
            'partner_id': self.transporter_id.id,
            'company_id': self.company_id.id,
            
            'analytic_account_id': analytic.id if analytic else self.analytic_account_id.id,
            'account_journal_id': lc_journal.id,
            'weight_id': self.id,

            'cost_lines': [(0, 0, {
                'product_id': l.product_id.id,
                'name': l.product_id.name,
                'product_qty': l.product_qty,
                # 'account_id': 3278,
                'price_unit':abs(l.total,),
                'currency_price_unit': abs(l.total,),
                'split_method': l.product_id.split_method_landed_cost or 'equal',
            }) for l in self.landed_cost_line_ids],
        })
        landed_costs.create_transporter_invoices()
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.landed.cost',
            'res_id': landed_costs.id,
            'context': {'form_view_initial_mode': 'edit'},
        }

    def button_rock_close(self):
        for sample in self.request_samples_ids:
            if not sample.partner_id:
                raise ValidationError("Please enter a Vendor for all sample requests before closing.")
            self.write({'state': 'close'})

    @api.onchange('request_samples_ids.au')
    def get_average(self):
        for rec in self:
            if self.request_samples_ids:
                # for line in self.request_samples_ids:
                # if line.sample_type =='rock':
                arr = [rec.au for rec in self.request_samples_ids if rec.sample_type == 'rock']

                #####################old code ###############################
                # arr = [rec.au for rec in self.request_samples_ids]
                std_dev = statistics.stdev(arr)

                avg = sum(arr) / len(arr)
                replace = 0
                if std_dev < 1:
                    self.average = avg
                elif std_dev > 1:
                    low = [r for r in arr if r * 4 < avg]
                    hight = [r for r in arr if r / 4 > avg]
                    if len(low) == 1:
                        arr.remove(low[0])
                    if len(hight) == 1:
                        arr.remove(hight[0])
                        replace = sum(arr) / len(arr) * 4
                        arr.append(replace)
                    self.average = sum(arr) / len(arr)
                else:
                    self.average = avg



    @api.depends('quantity', 'average')
    def get_total(self):
        for rec in self:
            rec.qy_average = rec.quantity * rec.average

    def make_purchase_quotation(self):
        self.ensure_one()
        order_line_ids = []

        self.po_request = datetime.today()

        # Prepare purchase order lines
        for line in self.line_ids:
            unit_price = line.unit_price
            incentive_price = line.incentive_price
            if line.is_landed_costs_line and not line.product_id.product_tmpl_id.self_deportation:
                unit_price = -abs(unit_price)
            if line.product_id.is_company_percentage:
                unit_price = -abs(unit_price)
            else:
                unit_price = unit_price
            analytic_distribution = {line.analytic_account_id.id: 100}

            order_line = {
                'product_id': line.product_id.id,
                'product_uom': line.product_id.uom_id.id,
                'price_unit': unit_price+incentive_price,
                'incentive_price':incentive_price,
                'product_qty': line.product_qty,
                'percentage': line.percentage,
                'discount': line.discount,
                'is_landed_costs_line': line.is_landed_costs_line,
                'self_deportation': line.self_deportation,
                'name': line.product_id.name,
                'date_planned': self.date_request.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'x_studio_batch_no': self.batch,
                'lot_id': self.lot_id.id,
                'average': self.average,
                'analytic_distribution': analytic_distribution,
            }
            order_line_ids.append((0, 0, order_line))


        delivery_obj = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id.code', '=', 'Rock')
        ], limit=1)

        # Create the purchase order
        purchase_order = self.env['purchase.order'].sudo().create({
            'partner_id': self.rock_vendor.id,
            'order_line': order_line_ids,
            'is_opu_po':self.is_opu_po,
            'weight_request_id': self.id,
            'x_studio_transporter': self.car_id.transporter_id.id,
            'analytic_account_id': self.analytic_account_id.id,
            'x_studio_many2one_field_t3bCi': self.area_id.id,
            'company_id': self.company_id.id,
            'lot_id': self.lot_id.id,
            'ore_purchased': True,
            'picking_type_id':delivery_obj.id
        })

        # Change state and return an action to open the created record
        self.state = 'rock_user'

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'res_id': purchase_order.id,
            'view_id': self.env.ref('material_request.purchase_order_form_inherith').id,
            'context': {'form_view_initial_mode': 'edit'},
        }

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('weight_request.sequence') or "/"
            request = super(WeightRequest, self).create(vals)
            product = self.env['product.product'].search([('custom_sequence', '=', 'landed_cost_product')], limit=1)

            if product:
                self.env['weight.request.landedcost.line'].create({
                    'product_id': product.id,
                    'weight_id': request.id,
                })
            if  product.custom_analytic_account_id:
              request.analytic_account_id = product.custom_analytic_account_id
        return request

    def get_requested_by(self):
        user = self.env.user.id
        return user

    def button_submit(self):
        for rec in self:
            if not self.requested_by.id == self.env.user.id:
                raise UserError('Sorry, Only requester can submit this document!')

            if rec.quantity == 0.0 and rec.form_type != 'external_visit':
                raise UserError(_("Please Enter the Quantity"))

            rec.submit_date = fields.Datetime.now()
            return self.write({'state': 'db_geologist'})

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Only draft records can be deleted!")
        return super(WeightRequest, self).unlink()

    def button_draft(self):
        return self.write({'state': 'draft'})

    def button_cancel(self):
        self.write({'state': 'cancel'})

    @api.depends('sample_no_from', 'sample_no_to')
    def button_generate(self):
        if not self.sample_no_from and not self.sample_no_to:
            raise UserError('Please add Samples')

        sample_nums = []
        sample_nums_final = []

        weight_sample_line = []

        start_number = self.sample_no_from
        end_number = self.sample_no_to

        self.write({'request_samples_ids': False})

        for rec in self:

            if rec.sample_no_from and rec.sample_no_to:

                for number in range(start_number, end_number + 1):
                    sample_nums.append(number)

                for line in sample_nums:
                    weight_sample_line = {'name': rec.name,
                                          'sample_no': line,
                                          'quantity': 1,
                                          'batch': rec.batch,
                                          'lot_id': rec.lot_id,
                                          'request_id': rec.id
                                          }
                    sample_nums_final.append(weight_sample_line)

                weight_sample_line_create = self.env['weight.samples'].create(sample_nums_final)

    def button_db_geologist_re_assay(self):
        if not self.request_samples_ids:
            raise UserError('Please Click to generate Samples')
        for rec in self:
            if rec.form_type == 'external_visit':
                for sample in rec.request_samples_ids:
                    if not sample.sample_position or not sample.rock_type:
                        raise UserError(_("Please enter both Sample Position and Rock Type in all sample requests."))

                    if not sample.dip_strike:
                        raise UserError(_("Please enter a value for Dip/Strike in all sample requests."))

                    if sample.north == 0 or sample.east == 0 or sample.elevation == 0:
                        raise UserError(
                            _("North, East, and Elevation must be greater than zero in all sample requests."))

        chemical_samples = []
        sample_line = []
        for rec in self:

            if not rec.store:
                raise UserError(_("Answer The DISPOSAL store Yes/NO "))
            if not rec.dump:
                raise UserError(_("Answer The DISPOSAL dump Yes/NO "))

            for line in rec.request_samples_ids:

                if line.quantity == 0.0:
                    raise UserError(_("Please Enter the Quantity"))

                sample_line = (0, 0, {'name': line.name,
                                      'sample_no1': line.sample_no,
                                      'quantity': line.quantity,
                                      'sample_type': line.sample_type,
                                      'batch': line.batch,
                                      'lot_id': line.lot_id.id,
                                      'weight_request_id': line.id,
                                      })
                chemical_samples.append(sample_line)

            if rec.form_type == 'external_visit':
                create_chemical_sample = {
                    'request_id': rec.id,
                    'company_id': rec.company_id.id,
                    'requested_by': self.env.user.id,
                    'email': rec.requested_by.email,
                    'phone': rec.requested_by.phone,
                    'date': datetime.today(),
                    'request_samples_ids': chemical_samples,
                    'state': 'receive',
                    'sample_type': 'rock_chips',
                    'form_type': 'external_visit',
                    'store': rec.store,
                    'store_time': rec.store_time,
                    'dump': rec.dump,
                    'dump_time': rec.dump_time,
                    'sample_no_from': rec.sample_no_from,
                    'sample_no_to': rec.sample_no_to,
                    'area_id': rec.area_id.display_name,
                    'rock_vendor': rec.rock_vendor.name,
                }
            else:
                create_chemical_sample = {
                    'request_id': rec.id,
                    'company_id': rec.company_id.id,
                    'requested_by': self.env.user.id,
                    'email': rec.requested_by.email,
                    'phone': rec.requested_by.phone,
                    'date': datetime.today(),
                    'request_samples_ids': chemical_samples,
                    'state': 'receive',
                    'sample_type': 'rock_chips',
                    'form_type': 'scaling_unit',
                    'store': rec.store,
                    'store_time': rec.store_time,
                    'dump': rec.dump,
                    'dump_time': rec.dump_time,
                    'sample_no_from': rec.sample_no_from,
                    'sample_no_to': rec.sample_no_to,

                }

            chemical = self.env['chemical.samples.request'].create(create_chemical_sample)
        return self.write({'state': 'chem_lab'})

    def button_db_geologist(self):
        if not self.request_samples_ids:
            raise UserError('Please Click to generate Samples')
        for rec in self:
            if rec.form_type == 'external_visit':
                for sample in rec.request_samples_ids:
                    if not sample.sample_position or not sample.rock_type:
                        raise UserError(_("Please enter both Sample Position and Rock Type in all sample requests."))

                    if not sample.dip_strike:
                        raise UserError(_("Please enter a value for Dip/Strike in all sample requests."))

                    if sample.north == 0 or sample.east == 0 or sample.elevation == 0:
                        raise UserError(
                            _("North, East, and Elevation must be greater than zero in all sample requests."))
        chemical_samples = []
        sample_line = []
        for rec in self:

            if not rec.store:
                raise UserError(_("Answer The DISPOSAL store Yes/NO "))
            if not rec.dump:
                raise UserError(_("Answer The DISPOSAL dump Yes/NO "))

            if not rec.oven:
                raise UserError(_("Answer The Oven Option Yes/NO "))

            for line in rec.request_samples_ids:

                if line.quantity == 0.0:
                    raise UserError(_("Please Enter the Quantity"))

                sample_line = (0, 0, {'name': line.name,
                                      'sample_no1': line.sample_no,
                                      'quantity': line.quantity,
                                      'batch': line.batch,
                                      'lot_id': line.lot_id.id,
                                      'sample_type': line.sample_type,
                                      'weight_request_id': line.id,
                                      'analysis_required': 'au'
                                      })
                chemical_samples.append(sample_line)
            if rec.form_type == 'external_visit':
                create_chemical_sample = {
                    'request_id': rec.id,
                    'company_id': rec.company_id.id,
                    'requested_by': self.env.user.id,
                    'email': rec.requested_by.email,
                    'phone': rec.requested_by.phone,
                    'date': datetime.today(),
                    'request_samples_ids': chemical_samples,
                    'state': 'receive',
                    'sample_type': 'rock_chips',
                    'form_type': 'external_visit',
                    'store': rec.store,
                    'store_time': rec.store_time,
                    'dump': rec.dump,
                    'dump_time': rec.dump_time,
                    'sample_no_from': rec.sample_no_from,
                    'sample_no_to': rec.sample_no_to,
                    'area_id': rec.area_id.display_name,
                    'rock_vendor': rec.rock_vendor.name,
                }
            else:
                create_chemical_sample = {
                    'request_id': rec.id,
                    'company_id': rec.company_id.id,
                    'requested_by': self.env.user.id,
                    'email': rec.requested_by.email,
                    'phone': rec.requested_by.phone,
                    'date': datetime.today(),
                    'request_samples_ids': chemical_samples,
                    'state': 'receive',
                    'sample_type': 'rock_chips',
                    'form_type': 'scaling_unit',
                    'store': rec.store,
                    'store_time': rec.store_time,
                    'dump': rec.dump,
                    'dump_time': rec.dump_time,
                    'sample_no_from': rec.sample_no_from,
                    'sample_no_to': rec.sample_no_to,

                }

            chemical = self.env['chemical.samples.request'].create(create_chemical_sample)
        if self.form_type != 'external_visit' and not self.car_id.x_studio_no_landed_cost:
            self.button_create_landed_costs()
        else:
            pass

        return self.write({'state': 'chem_lab'})

    def action_view_chemical_assay(self):
        return {
            'name': "Samples Assay Request",
            'type': 'ir.actions.act_window',
            'res_model': 'chemical.samples.request',
            'view_id': False,
            'view_mode': 'list,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('request_id', '=', self.id)],
        }

    def compute_chemical_assay_count(self):
        self.chemical_assay_request_count = self.env['chemical.samples.request'].search_count(
            [('request_id', '=', self.id)])

    def action_view_purchases_order(self):
        view_id = self.env.ref('material_request.purchase_orde_tree')
        return {
            'name': "RFQ/ Order",
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_id': view_id.id,
            'view_mode': 'list',
            'target': 'current',
            'domain': [('weight_request_id', '=', self.id)],
        }

    def compute_purchase_count(self):
        self.purchase_count = self.env['purchase.order'].search_count([('weight_request_id', '=', self.id)])

    def apply_values_to_checked_lines(self):
        """Apply partner, north, east, elevation, sample_position, and dip_strike to checked lines"""
        if self.form_type != 'external_visit':
            return  # Don't apply changes if not 'external_visit'

        for line in self.request_samples_ids:
            if self.select_all_record:
                line.partner_id = self.partner_id
                line.north = self.north
                line.east = self.east
                line.elevation = self.elevation
                line.sample_position = self.sample_position
                line.dip_strike = self.dip_strike
                line.rock_type = self.rock_type
                line.apply_partner = False
            elif line.apply_partner:
                line.partner_id = self.partner_id
                line.north = self.north
                line.east = self.east
                line.elevation = self.elevation
                line.sample_position = self.sample_position
                line.dip_strike = self.dip_strike
                line.rock_type = self.rock_type
                line.apply_partner = False


class WeightSamples(models.Model):
    _name = "weight.samples"

    name = fields.Char("Batch")
    sample_no = fields.Integer("Sample No.")
    request_id = fields.Many2one("weight.request", "Weight Request")
    quantity = fields.Float("Quantity", default=1.0)
    au = fields.Float("Au")
    company_id = fields.Many2one(related="request_id.company_id")
    batch = fields.Char("Batch", related="request_id.batch")
    lot_id = fields.Many2one(comodel_name="stock.lot", string="Lots Batch", related="request_id.lot_id")
    sample_type = fields.Selection([('rock', 'Rock'), ('blank', 'Blank'), ('double', 'Double'), ('std', 'STD')],
                                   default="rock")

    #### external visit #################################
    form_type = fields.Selection(
        [('scaling_unit', 'Scaling Unit'),
         ('external_sample', 'External Sample'),
         ('external_visit', 'External Visit')],
        string='Request Type', related='request_id.form_type'
    )
    date_request = fields.Datetime("Request Date/Time ", related='request_id.date_request')
    area_id = fields.Many2one("x_area", related='request_id.area_id')
    east = fields.Integer("Easting")
    north = fields.Integer("Northing")
    elevation = fields.Integer("Elevation")
    partner_id = fields.Many2one("res.partner", string="Partner")
    apply_partner = fields.Boolean(string="Apply Partner")
    rock_type = fields.Selection([
        ('qtz', 'Quartz (Qtz)'),
        ('m_vol', 'Metavolcanic (M.Vol)'),
    ], string="Rock Type")
    sample_position = fields.Selection([
        ('hr', 'Host Rock'),
        ('bc', 'Body Contact'),
        ('vein', 'Vein'),
        ('ds', 'Dums'),
    ], string="Sample Position")
    dip_strike = fields.Integer(string="DIP/Strike")
    average_au = fields.Float(
        "Average AU",
        compute='_compute_average_au'
    )
    unit_price = fields.Float(string="Unit Price", compute='_compute_unit_price')
    oxidation = fields.Selection(
        [('vox', 'VOX'),
         ('mox', 'MOX'),
         ('wox', 'WOX')],
        string='Oxidation'
    )

    alteration = fields.Selection(
        [('lem', 'LEM'),
         ('hem', 'HEM'),
         ('mag', 'MAG')],
        string='Alteration'
    )

    location = fields.Text(string='Location')
    notes = fields.Text(string='Notes')
    

    def _compute_average_au(self):
        for record in self:
            count = 0
            # Only calculate average AU if 'is_external_visit' is True in the context
            # if self.env.context.get('is_external_visit', False):
            # Group by chemical_request_id and partner_id for external visit samples
            lines = self.env['weight.samples'].search([
                ('request_id', '=', record.request_id.id),
                ('partner_id', '=', record.partner_id.id)
            ])

            # Calculate the average of AU
            if lines:
                total_au = sum(line.au for line in lines)
                record.average_au = total_au / len(lines)
                record.average_au = record.average_au / len(lines)
            else:
                record.average_au = 0

    def _compute_unit_price(self):
        for record in self:
            average_au = 0
            lines = self.env['weight.samples'].search([
                ('request_id', '=', record.request_id.id),
                ('partner_id', '=', record.partner_id.id)
            ])
            if lines:
                total_au = sum(line.au for line in lines)
                average_au = total_au / len(lines)
            else:
                average_au = 0

            price_list = self.env['purchase.price.list'].search([
                ('qty_min', '<=', average_au),
                ('qty_max', '>=', average_au)
            ], limit=1)

            record.unit_price = price_list.unit_price / len(lines) if price_list else 0.0  # Default to 0 if no match


class TransportationCar(models.Model):
    _name = "transportation.car"
    name = fields.Char("Car No.")
    car_plate = fields.Char("Plate license No.")
    driver_id = fields.Many2one("transportation.car.driver", "Driver")
    transporter_id = fields.Many2one("res.partner", "Transporter")
    active = fields.Boolean(default=True)


class TransportationCarDriver(models.Model):
    _name = "transportation.car.driver"

    name = fields.Char("driver Name")


class ChemicalSamples(models.Model):
    _name = "chemical.samples.request"

    _description = 'Chemical Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _rec_name = 'name'
    _order = 'sample_no_from desc'

    def _get_default_department(self):
        return self.env.user.department_id.id if self.env.user.department_id else False

    name = fields.Char('Sample Submission No.', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))

    request_id = fields.Many2one("weight.request", "Scaling Request")
    work_order_id = fields.Many2one("mrp.production", "Mo Reference")
    production_id = fields.Many2one('mrp.production', string="Production Order")
    workorder_id = fields.Many2one('mrp.workorder', string="Work Order")

    requested_by = fields.Many2one('res.users', 'Sender Name', track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True, readonly=True)

    department_id = fields.Many2one('hr.department', string='Department',
                                    default=lambda self: self._get_default_department())
    project = fields.Many2one("project.project", "Project")
    email = fields.Char("Email")
    phone = fields.Char("Phone")
    date = fields.Datetime("Date", default=fields.Datetime.now, )

    receive_date = fields.Datetime("Receive Date")

    receive_name = fields.Many2one('res.users', 'Receive Name', track_visibility='onchange',
                                   store=True, readonly=True)

    # sample_type = fields.Selection([('grade_control','Grade Control'),('rc', 'RC'), ('rock_chips', 'Rock Chips'),
    #                                 ('trench', 'Trench'), ('tailing', 'Tailing'), ('crusher', 'Crusher'),
    #                                 ('cic', 'CIC'),('cil', 'CIL'), ('meta', 'Metallurgical Lab'), ('other', 'Other')],
    #                                required=True)
    sample_type = fields.Selection([
        ('grade_control', 'Grade Control'),
        ('rc', 'RC'),
        ('rock_chips', 'Rock Chips'),
        ('trench', 'Trench'),
        ('tailing', 'Tailing'),
        ('crusher', 'Crusher'),
        ('cic', 'CIC'),
        ('cic_carbon', 'CIC-Carbon'),
        ('cil', 'CIL'),
        ('solution', 'CIL-Solution'),
        ('solid', 'CIL-Solid'),
        ('stripping', 'CIL-Stripping'),
        ('carbon', 'CIL-Carbon'),
        ('meta', 'Met-Solution'),
        ('meta_solid', 'Met-Solid'),
        ('main', 'Main'),
        ('other', 'Other')
    ], required=True)

    other = fields.Char("Other")

    request_samples_ids = fields.One2many("chemical.samples.line", "chemical_request_id", "Samples")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id)

    state = fields.Selection(selection=_CSTATES, string='Status', index=True, track_visibility='onchange',
                             readonly=True,
                             required=True, copy=False, default='draft')

    reason_reject = fields.Text("Rejection Reason", track_visibility="onchange")

    no_of_samples = fields.Float("No. of Samples")
    methods = fields.Selection(
        [('aqua', 'Aqua Regia Digest With Solvent Extraction and AAS Finish,ppm'), ('other', 'Other')], default="aqua",
        string="Methods Of Analysis")

    date_analysis = fields.Datetime("Date of Analysis")
    analysis_required = fields.Selection([('au', 'Au'), ('other', 'Other')], default="au", srting="Analysis Required")

    lab_reference_no = fields.Char('Lab. Reference No.', required=True, copy=False, readonly=True, index=True,
                                   default=lambda self: _('New'))

    disposal_info = fields.Char(default="STRUCTION FOR DISPOSAL OF SAMPLES AND RECEIPT OF RESULTS", readonly="1")
    store = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="stored after analysis")
    dump = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="dumped after analysis")

    oven = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Oven Option for Samples")

    oven_time = fields.Float("Hours")

    store_time = fields.Float("Hours")
    dump_time = fields.Float("Hours")

    sample_no_from = fields.Integer("Sample  From ")
    sample_no_to = fields.Integer("Sample  To ")
    daily_night = fields.Selection([('crd', 'CR-D'), ('hd', 'HD'), ('crn', 'CR-N',), ('hn', "HN"),('hp','HP')],
                                   string="Sample Sequence")
    cic_samples = fields.Selection(
        [('factory', 'Factory samples'), ('stripping', 'Stripping samples'), ('carbon', 'Carbon')],
        string="Sample Sequence")

    cic_sub_samples = fields.Selection(
        [('unit_one_old', 'Unit One '), ('unit_two_old', 'Unit Two '), ('unit_three_old', 'Unit Three'),
         ('unit_four_old', 'Unit Four'), ('unit_five_old', 'Unit Five'),
         ('bs_6', 'BS6'), ('pregnant_sample', 'Pregnant Sample'), ('manhole', 'Manhole Sample'), ],
        string="Sub Sample")


    ############# External Visit & External Sample #############

    rock_vendor = fields.Char("Rock Vendor")
    area_id = fields.Char("Area")
    east = fields.Integer("Easting")
    north = fields.Integer("Northing")
    elevation = fields.Integer("Elevation")

    form_type = fields.Selection(
        [('scaling_unit', 'Scaling Unit'),
         ('external_sample', 'External Sample'),
         ('external_visit', 'External Visit')],
        string='Request Type',

    )

    rock_type = fields.Selection(
        [('qtz', 'QTZ'),
         ('m_vol', 'M.VOL'),
         ('chert', 'CHERT')],
        string='Rock Type'
    )

    sample_position = fields.Selection(
        [('m_v', 'M.V'),
         ('h_r', 'H.R'),
         ('b_c', 'B.C'),
         ('o_c', 'O.C'),
         ('ds', 'DS')],
        string='Sample Position'
    )
    notes = fields.Text(string='Notes')
    average = fields.Float("Average Grade", compute="get_average", store=True)




    total_sample_quantity = fields.Float(
        string="Total Samples Quantity",
        compute="_compute_total_sample_quantity",
        store=True,
        readonly=True
    )

    
    hcl = fields.Float(string="HCL")
    hno3 = fields.Float(string="HNO3")
    dibk = fields.Float(string="DIBK")
    aliquate = fields.Float(string="Aliquate")

    hcl_total = fields.Float(string="QTY/HCL",compute="_compute_hcl_total",store=True)
    hno3_total = fields.Float(string="QTY/HNO3",compute="_compute_hno3_total",store=True)
    dibk_total = fields.Float(string="QTY/DIBK",compute="_compute_dibk_total",store=True)
    aliquate_total = fields.Float(string="QTY/Aliquate",compute="_compute_aliquate_total",store=True)

    @api.onchange('sample_type')
    def _onchange_sample_type_values(self):
        """تحديث قيم المواد الكيميائية بناءً على نوع العينة"""
        if self.sample_type:
            # قاموس يحتوي على القيم لكل نوع (حسب ملف الإكسل)
            values_map = {
                'rc': {'hcl': 30.0, 'hno3': 10.0, 'dibk': 5.0, 'aliquate': 0.1},
                'grade_control': {'hcl': 21.0, 'hno3': 7.0, 'dibk': 5.0, 'aliquate': 0.1},
                'rock_chips': {'hcl': 21.0, 'hno3': 7.0, 'dibk': 5.0, 'aliquate': 0.1},
                'trench': {'hcl': 21.0, 'hno3': 7.0, 'dibk': 5.0, 'aliquate': 0.1},
                'tailing': {'hcl': 21.0, 'hno3': 7.0, 'dibk': 5.0, 'aliquate': 0.1},
                'crusher': {'hcl': 21.0, 'hno3': 7.0, 'dibk': 5.0, 'aliquate': 0.1},
                'main': {'hcl': 21.0, 'hno3': 7.0, 'dibk': 5.0, 'aliquate': 0.1},
                'meta': {'hcl': 1.0, 'hno3': 0.0, 'dibk': 5.0, 'aliquate': 0.1},
                'meta_solid': {'hcl': 21.0, 'hno3': 7.0, 'dibk': 5.0, 'aliquate': 0.1},
                'cic': {'hcl': 1.0, 'hno3': 0.0, 'dibk': 5.0, 'aliquate': 0.1},
                'cic_carbon': {'hcl': 30.0, 'hno3': 10.0, 'dibk': 5.0, 'aliquate': 0.1},
                'solution': {'hcl': 1.0, 'hno3': 0.0, 'dibk': 5.0, 'aliquate': 0.1},
                'solid': {'hcl': 21.0, 'hno3': 7.0, 'dibk': 5.0, 'aliquate': 0.1},
                'stripping': {'hcl': 1.0, 'hno3': 0.0, 'dibk': 5.0, 'aliquate': 0.1},
                'carbon': {'hcl': 30.0, 'hno3': 10.0, 'dibk': 10.0, 'aliquate': 0.2},

            }

            vals = values_map.get(self.sample_type)
            if vals:
                self.hcl = vals.get('hcl', 0.0)
                self.hno3 = vals.get('hno3', 0.0)
                self.dibk = vals.get('dibk', 0.0)
                self.aliquate = vals.get('aliquate', 0.0)
            else:
                # تصفير القيم إذا كان النوع 'Other' أو غير معرف
                self.hcl = self.hno3 = self.dibk = self.aliquate = 0.0

    @api.depends('request_samples_ids.quantity')
    def _compute_total_sample_quantity(self):
        for rec in self:
            rec.total_sample_quantity = sum(line.quantity for line in rec.request_samples_ids)



    @api.depends('total_sample_quantity', 'hcl')
    def _compute_hcl_total(self):
        for rec in self:
            rec.hcl_total = rec.total_sample_quantity * rec.hcl


    @api.depends('total_sample_quantity', 'hno3')
    def _compute_hno3_total(self):
        for rec in self:
            rec.hno3_total = rec.total_sample_quantity * rec.hno3



    @api.depends('total_sample_quantity', 'dibk')
    def _compute_dibk_total(self):
        for rec in self:
            rec.dibk_total = rec.total_sample_quantity * rec.dibk



    @api.depends('total_sample_quantity', 'aliquate')
    def _compute_aliquate_total(self):
        for rec in self:
            rec.aliquate_total = rec.total_sample_quantity * rec.aliquate





    @api.depends('request_samples_ids.au','workorder_id')
    def get_average(self):
        for rec in self:
            if rec.request_samples_ids:
                arr = [line.au for line in rec.request_samples_ids if line.au is not None]

                if not arr:
                    rec.average = 0.0
                    continue

                try:
                    std_dev = statistics.stdev(arr) if len(arr) > 1 else 0
                except statistics.StatisticsError:
                    std_dev = 0

                avg = sum(arr) / len(arr)
                replace = 0

                if std_dev < 1:
                    rec.average = avg
                elif std_dev > 1:
                    low = [r for r in arr if r * 4 < avg]
                    high = [r for r in arr if r / 4 > avg]
                    if len(low) == 1:
                        arr.remove(low[0])
                    if len(high) == 1:
                        arr.remove(high[0])
                        replace = (sum(arr) / len(arr)) * 4
                        arr.append(replace)
                    rec.average = sum(arr) / len(arr)
                else:
                    rec.average = avg
            else:
                rec.average = 0.0


            # Sync to related Work Order
            if rec.workorder_id and rec.workorder_id.workcenter_id:
                code = rec.workorder_id.workcenter_id.code
                if code in ["WC-CIC-CRSH", "WC-CIC-STKR"]:
                    rec.workorder_id.grade_control = rec.average
                elif code in ["WC-CIC-ADRO", "WC-CIC-ADRN"]:
                    rec.workorder_id.unit_Outlet = rec.average

                # Sync to related pregnant Sample result
            if rec.pregnant_result:
                if rec.pregnant_result.type == 'ps':
                    rec.pregnant_result.pregnant_sample = rec.average

                elif rec.pregnant_result.type == 'bs':
                    rec.pregnant_result.barren_sex = rec.average

            rec.pregnant_result.write({'state': 'done'})

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('cheimcal_request.sequence') or "/"

        return super(ChemicalSamples, self).create(vals)


    def button_to_db_reject(self):
        self.write({'state': 'reject'})


    def button_reject(self):
        self.write({'state': 'reject'})
        if self.request_id:
            self.request_id.state = 'db_price'
            

    def button_draft(self):
        return self.write({'state': 'draft'})

    @api.depends('sample_no_from', 'sample_no_to')
    def button_generate(self):
        self.write({'request_samples_ids': False})
        for rec in self:
            if rec.sample_type == 'crusher':

                if not self.daily_night:
                    raise UserError('Please Select Daily/Night')

                if rec.daily_night == 'crd':
                    samples_sequence = self.env['chemical.samples.sequences'].search(
                        [('category', '=', 'crusher'), ('daily_night', '=', 'crd')])
                    chemical_samples = []
                    sample_line = []
                    for line in samples_sequence:
                        chemical_samples = {'name': rec.name,
                                            'sample_no1': line.name,
                                            'quantity': 1,
                                            'chemical_request_id': rec.id
                                            }
                        sample_line.append(chemical_samples)

                    chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)


                elif rec.daily_night == 'crn':
                    samples_sequence = self.env['chemical.samples.sequences'].search(
                        [('category', '=', 'crusher'), ('daily_night', '=', 'crn')])
                    chemical_samples = []
                    sample_line = []
                    for line in samples_sequence:
                        chemical_samples = {'name': rec.name,
                                            'sample_no1': line.name,
                                            'quantity': 1,
                                            'chemical_request_id': rec.id
                                            }
                        sample_line.append(chemical_samples)

                    chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)



                elif rec.daily_night == 'hd':
                    samples_sequence = self.env['chemical.samples.sequences'].search(
                        [('category', '=', 'crusher'), ('daily_night', '=', 'hd')])
                    chemical_samples = []
                    sample_line = []
                    for line in samples_sequence:
                        chemical_samples = {'name': rec.name,
                                            'sample_no1': line.name,
                                            'quantity': 1,
                                            'chemical_request_id': rec.id
                                            }
                        sample_line.append(chemical_samples)

                    chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)



                elif rec.daily_night == 'hn':
                    samples_sequence = self.env['chemical.samples.sequences'].search(
                        [('category', '=', 'crusher'), ('daily_night', '=', 'hn')])
                    chemical_samples = []
                    sample_line = []
                    for line in samples_sequence:
                        chemical_samples = {'name': rec.name,
                                            'sample_no1': line.name,
                                            'quantity': 1,
                                            'chemical_request_id': rec.id
                                            }
                        sample_line.append(chemical_samples)

                    chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)




                elif rec.daily_night == 'hp':
                    samples_sequence = self.env['chemical.samples.sequences'].search(
                        [('category', '=', 'crusher'), ('daily_night', '=', 'hp')])
                    chemical_samples = []
                    sample_line = []
                    for line in samples_sequence:
                        chemical_samples = {'name': rec.name,
                                            'sample_no1': line.name,
                                            'quantity': 1,
                                            'chemical_request_id': rec.id
                                            }
                        sample_line.append(chemical_samples)

                    chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)



                else:

                    samples_sequence = self.env['chemical.samples.sequences'].search([('category', '=', 'crusher')])
                    chemical_samples = []
                    sample_line = []
                    for line in samples_sequence:
                        chemical_samples = {'name': rec.name,
                                            'sample_no1': line.name,
                                            'quantity': 1,
                                            'chemical_request_id': rec.id
                                            }
                        sample_line.append(chemical_samples)

                    chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)


            # elif rec.sample_type == 'cic':
            #
            #     if rec.cic_samples == 'factory':
            #
            #         samples_sequence = self.env['chemical.samples.sequences'].search(
            #             [('category', '=', 'cic'), ('cic_samples', '=', 'factory')])
            #
            #         chemical_samples = []
            #         sample_line = []
            #         for line in samples_sequence:
            #             chemical_samples = {'name': rec.name,
            #                                 'sample_no1': line.name,
            #                                 'sample_no': line.id,
            #                                 'quantity': 1,
            #                                 'chemical_request_id': rec.id
            #                                 }
            #             sample_line.append(chemical_samples)
            #
            #         chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)

            elif rec.sample_type in ['cic', 'cic_carbon']:

                if rec.cic_samples == 'factory':

                    if rec.cic_sub_samples == 'unit_one_old':

                        samples_sequence = self.env['chemical.samples.sequences'].search(
                            [('category', '=', 'cic'), ('cic_samples', '=', 'factory') , ('cic_sub_samples', '=', 'unit_one_old')])

                        chemical_samples = []
                        sample_line = []
                        for line in samples_sequence:
                            chemical_samples = {'name': rec.name,
                                                'sample_no1': line.name,
                                                'sample_no': line.id,
                                                'quantity': 1,
                                                'chemical_request_id': rec.id
                                                }
                            sample_line.append(chemical_samples)

                        chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)

                    elif rec.cic_sub_samples == 'unit_two_old':

                        samples_sequence = self.env['chemical.samples.sequences'].search(
                            [('category', '=', 'cic'), ('cic_samples', '=', 'factory') , ('cic_sub_samples', '=', 'unit_two_old')])

                        chemical_samples = []
                        sample_line = []
                        for line in samples_sequence:
                            chemical_samples = {'name': rec.name,
                                                'sample_no1': line.name,
                                                'sample_no': line.id,
                                                'quantity': 1,
                                                'chemical_request_id': rec.id
                                                }
                            sample_line.append(chemical_samples)

                        chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)

                    elif rec.cic_sub_samples == 'unit_three_old':

                        samples_sequence = self.env['chemical.samples.sequences'].search(
                            [('category', '=', 'cic'), ('cic_samples', '=', 'factory') , ('cic_sub_samples', '=', 'unit_three_old')])

                        chemical_samples = []
                        sample_line = []
                        for line in samples_sequence:
                            chemical_samples = {'name': rec.name,
                                                'sample_no1': line.name,
                                                'sample_no': line.id,
                                                'quantity': 1,
                                                'chemical_request_id': rec.id
                                                }
                            sample_line.append(chemical_samples)

                        chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)

                    elif rec.cic_sub_samples == 'unit_four_old':

                        samples_sequence = self.env['chemical.samples.sequences'].search(
                            [('category', '=', 'cic'), ('cic_samples', '=', 'factory') , ('cic_sub_samples', '=', 'unit_four_old')])

                        chemical_samples = []
                        sample_line = []
                        for line in samples_sequence:
                            chemical_samples = {'name': rec.name,
                                                'sample_no1': line.name,
                                                'sample_no': line.id,
                                                'quantity': 1,
                                                'chemical_request_id': rec.id
                                                }
                            sample_line.append(chemical_samples)

                        chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)

                    elif rec.cic_sub_samples == 'unit_five_old':

                        samples_sequence = self.env['chemical.samples.sequences'].search(
                            [('category', '=', 'cic'), ('cic_samples', '=', 'factory') , ('cic_sub_samples', '=', 'unit_five_old')])

                        chemical_samples = []
                        sample_line = []
                        for line in samples_sequence:
                            chemical_samples = {'name': rec.name,
                                                'sample_no1': line.name,
                                                'sample_no': line.id,
                                                'quantity': 1,
                                                'chemical_request_id': rec.id
                                                }
                            sample_line.append(chemical_samples)

                        chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)

                    elif rec.cic_sub_samples == 'bs_6':

                        samples_sequence = self.env['chemical.samples.sequences'].search(
                            [('category', '=', 'cic'), ('cic_samples', '=', 'factory'),
                             ('cic_sub_samples', '=', 'bs_6')])

                        chemical_samples = []
                        sample_line = []
                        for line in samples_sequence:
                            chemical_samples = {'name': rec.name,
                                                'sample_no1': line.name,
                                                'sample_no': line.id,
                                                'quantity': 1,
                                                'chemical_request_id': rec.id
                                                }
                            sample_line.append(chemical_samples)

                        chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)

                    elif rec.cic_sub_samples == 'pregnant_sample':

                        samples_sequence = self.env['chemical.samples.sequences'].search(
                            [('category', '=', 'cic'), ('cic_samples', '=', 'factory'),
                             ('cic_sub_samples', '=', 'pregnant_sample')])

                        chemical_samples = []
                        sample_line = []
                        for line in samples_sequence:
                            chemical_samples = {'name': rec.name,
                                                'sample_no1': line.name,
                                                'sample_no': line.id,
                                                'quantity': 1,
                                                'chemical_request_id': rec.id
                                                }
                            sample_line.append(chemical_samples)

                        chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)

                    elif rec.cic_sub_samples == 'manhole':

                        samples_sequence = self.env['chemical.samples.sequences'].search(
                            [('category', '=', 'cic'), ('cic_samples', '=', 'factory'),
                             ('cic_sub_samples', '=', 'manhole')])

                        chemical_samples = []
                        sample_line = []
                        for line in samples_sequence:
                            chemical_samples = {'name': rec.name,
                                                'sample_no1': line.name,
                                                'sample_no': line.id,
                                                'quantity': 1,
                                                'chemical_request_id': rec.id
                                                }
                            sample_line.append(chemical_samples)

                        chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)











                elif rec.cic_samples == 'stripping':

                    if rec.sample_no_from <= 0 or rec.sample_no_to <= 0:
                        raise UserError(_('Please enter valid Sample From and Sample To values.'))

                    samples_sequence = self.env['chemical.samples.sequences'].search([

                        ('category', '=', 'cic'),
                        ('cic_samples', '=', 'stripping'),
                        ('sample_no', '>=', rec.sample_no_from),
                        ('sample_no', '<=', rec.sample_no_to),
                    ], order='sample_no asc')

                    if not samples_sequence:
                        raise UserError(_('No samples found in the given range (%s to %s).') % (rec.sample_no_from,
                                                                                                rec.sample_no_to))

                    sample_line = []

                    for line in samples_sequence:
                        vals = {
                            'sample_seq_no':line.sample_no,
                            'name': rec.name,
                            'sample_no1': line.name,
                            'sample_no': line.sample_no,
                            'quantity': 1,
                            'chemical_request_id': rec.id,
                        }

                        sample_line.append(vals)

                    self.env['chemical.samples.line'].create(sample_line)



                elif rec.cic_samples == 'carbon':

                    samples_sequence = self.env['chemical.samples.sequences'].search(
                        [('category', '=', 'cic'), ('cic_samples', '=', 'carbon')])

                    chemical_samples = []
                    sample_line = []
                    for line in samples_sequence:
                        chemical_samples = {'name': rec.name,
                                            'sample_no1': line.name,
                                            'sample_no': line.id,
                                            'quantity': 1,
                                            'chemical_request_id': rec.id
                                            }
                        sample_line.append(chemical_samples)

                    chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)


                else:

                    samples_sequence = self.env['chemical.samples.sequences'].search([('category', '=', 'cic_cil')])

                    chemical_samples = []
                    sample_line = []
                    for line in samples_sequence:
                        chemical_samples = {'name': rec.name,
                                            'sample_no1': line.name,
                                            'sample_no': line.id,
                                            'quantity': 1,
                                            'chemical_request_id': rec.id
                                            }
                        sample_line.append(chemical_samples)

                    chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)






            elif rec.sample_type in ['cil', 'solution', 'solid', 'stripping', 'carbon']:
                samples_sequence = self.env['chemical.samples.sequences'].search([('category', '=', 'cil')])

                chemical_samples = []
                sample_line = []
                for line in samples_sequence:
                    chemical_samples = {'name': rec.name,
                                        'sample_no1': line.name,
                                        'sample_no': line.id,
                                        'quantity': 1,
                                        'chemical_request_id': rec.id
                                        }
                    sample_line.append(chemical_samples)

                chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)



            elif rec.sample_type == 'heap':
                samples_sequence = self.env['chemical.samples.sequences'].search(
                    [('category', '=', 'crusher'), ('daily_night', '=', 'hp')])
                chemical_samples = []
                sample_line = []
                for line in samples_sequence:
                    chemical_samples = {'name': rec.name,
                                        'sample_no1': line.name,
                                        'quantity': 1,
                                        'chemical_request_id': rec.id
                                        }
                    sample_line.append(chemical_samples)

                chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)




            else:

                if not self.sample_no_from and not self.sample_no_to:
                    raise UserError('Please add Samples')

                sample_nums = []

                start_number = self.sample_no_from
                end_number = self.sample_no_to

                sample_line = []

                chemical_samples = []

                if rec.sample_no_from and rec.sample_no_to:

                    for number in range(start_number, end_number + 1):
                        sample_nums.append(number)

                    for line in sample_nums:
                        chemical_samples = {'name': rec.name,
                                            'sample_no1': line,
                                            'quantity': 1,
                                            'chemical_request_id': rec.id
                                            }
                        sample_line.append(chemical_samples)

                    chemical_sample_line_create = self.env['chemical.samples.line'].create(sample_line)


        # finally, return the view to keep Shopfloor open
        if not self.requested_by.id == self.env.user.id:
            raise UserError('Sorry, Only requester can submit this document!')

        if not rec.store:
            raise UserError(_("Answer The DISPOSAL store Yes/NO "))
        if not rec.dump:
            raise UserError(_("Answer The DISPOSAL dump Yes/NO "))

        if not rec.request_samples_ids:
            raise UserError(_("Please Enter the Samples"))

        # if self.sample_type!='heap':
            # self.button_submit()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'chemical.samples.request',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def button_submit(self):
        for rec in self:
            if not self.requested_by.id == self.env.user.id:
                raise UserError('Sorry, Only requester can submit this document!')

            if not rec.store:
                raise UserError(_("Answer The DISPOSAL store Yes/NO "))
            if not rec.dump:
                raise UserError(_("Answer The DISPOSAL dump Yes/NO "))

            if not rec.request_samples_ids:
                raise UserError(_("Please Enter the Samples"))

        # for line in rec.request_samples_ids:
        # 	if not line.quantity:
        # 		raise UserError('Please Enter Assay')

        self.write({'state': 'receive'})

        # # To show success notification:
        # return {
        #     'effect': {
        #         'fadeout': 'slow',
        #         'message': 'Request submitted successfully.',
        #         'type': 'rainbow_man',  # or 'success', 'warning'
        #     }
        # }

    def button_receive(self):
        for rec in self:
            rec.receive_name = rec.env.user.id
            rec.receive_date = datetime.today()
            dep = str(rec.department_id.name)[:2]
            if rec.department_id:
                rec.lab_reference_no = self.name + '-' + dep + '-' + self.env['ir.sequence'].next_by_code(
                    'lab_reference.sequence') or "/"
            else:
                rec.lab_reference_no = self.name + '-' + self.env['ir.sequence'].next_by_code(
                    'lab_reference.sequence') or "/"

        return self.write({'state': 'assay'})

    def button_assay(self):
        for rec in self:
            

            if not (rec.hcl or rec.hno3 or rec.dibk or rec.aliquate):
                raise UserError(_("Please enter the Report Elements (HCL, HNO3, DIBK, or Aliquate)."))


            for r in rec.request_samples_ids:
                if r.au == 0:
                    raise UserError(_("The AU Must be not Equal Zero (0)"))
            request_samples_ids = self.env['weight.samples'].search([('request_id', '=', rec.request_id.id)])

            for line in rec.request_samples_ids:
                # if not line.au:
                # 	raise UserError(_("Please Enter Assay Result"))

                if rec.request_id:
                    if rec.request_id.form_type == 'external_visit':
                        rec.request_id.state = 'waiting_rock'
                    else:
                        rec.request_id.state = 'db_price'

                    for s_line in request_samples_ids:
                        if s_line.id == line.weight_request_id.id:
                            s_line.au = line.au

            rec.request_id.get_average()
            rec.date_analysis = datetime.today()
            rec.state = 'close'

            if rec.stripping_id:
                stripping_sheet = self.env['stripping.log.sheet'].search([('id', '=', rec.stripping_id.id)], limit=1)
                print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>.>>>>>>>>>>>>>>>>.")
                if stripping_sheet:
                    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>.>>>>>>>>>>>>>>>>.", '2')
                    for line in stripping_sheet.stripping_line_ids:
                        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>.>>>>>>>>>>>>>>>>." , '3')
                        for sample in rec.request_samples_ids:
                            if line.sample_number == sample.sample_seq_no:
                                if sample.sample_no1 and sample.sample_no1.startswith('IN'):
                                    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>.>>>>>>>>>>>>>>>>.", '4')
                                    line.assay_pregnant = sample.au
                                elif sample.sample_no1 and sample.sample_no1.startswith('OUT'):
                                    line.assay_barren = sample.au





            # rec.request_id.get_average()
            # rec.date_analysis = datetime.today()
            # rec.write({'state': 'close'})
            #
            # rec._update_related_stripping()
            # self.get_average()

            ############### old code its so slow ###############
            # for rec in self:
            #     all_assays = self.env['chemical.samples.request'].search([
            #         ('request_id', '=', rec.request_id.id),
            #         ('state', '=', 'close')
            #     ])

            #     max_avg = 0
            #     for assay in all_assays:
            #         assay.get_average()
            #         max_avg = max(max_avg, assay.average)


            #     rec.request_id.average = max_avg


            # After updating all records, compute max average per request_id
            request_ids = self.mapped('request_id')
            for request in request_ids:
                all_assays = self.search([
                    ('request_id', '=', request.id),
                    ('state', '=', 'close')
                ])

                max_avg = 0
                for assay in all_assays:
                    assay.get_average()
                    max_avg = max(max_avg, assay.average)

                request.average = max_avg





    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Only draft records can be deleted!")
        return super(ChemicalSamples, self).unlink()

    def get_requested_by(self):
        user = self.env.user.id
        self.email = self.env.user.email
        return user


class ChemicalSamplesLine(models.Model):
    _name = "chemical.samples.line"

    name = fields.Char("Name")
    batch = fields.Char("Batch")
    lot_id = fields.Many2one(comodel_name="stock.lot", string="Lots Batch")
    sample_seq_no = fields.Integer("Sample No")
    sample_no = fields.Integer("Sample ID")
    sample_no1 = fields.Char("Sample ID")
    quantity = fields.Float("Quantity", default=1)
    chemical_request_id = fields.Many2one("chemical.samples.request", "Request")
    weight_request_id = fields.Many2one("weight.samples", "Request")
    analysis_required = fields.Selection([('au', 'Au'), ('auo', 'AU/CU/AG')], default="au", string="Analysis Required")
    methods = fields.Char("Methods", default="AAS")
    comments = fields.Char("Comments")
    # weight_request_id=fields.Char("Request")
    sample_type = fields.Selection([('rock', 'Rock'), ('blank', 'Blank'), ('double', 'Double'), ('std', 'STD') , ('cic', 'CIC'),],
                                   default="rock")

    company_id = fields.Many2one(related="chemical_request_id.company_id")

    au = fields.Float("Au")
    try1 = fields.Float("1")
    try2 = fields.Float("2")
    ag = fields.Float("Ag")
    cu = fields.Float("Cu")
    fe = fields.Float("Fe")
    
    parent_state = fields.Selection(
        related="chemical_request_id.state",
        string="Parent State",
        store=True,
    )







    ### new Feilds

    east = fields.Integer("Easting")
    north = fields.Integer("Northing")
    elevation = fields.Integer("Elevation")
    rock_type = fields.Selection(
        [('qtz', 'QTZ'),
         ('m_vol', 'M.VOL'),
         ('chert', 'CHERT')],
        string='Rock Type'
    )
    sample_position = fields.Selection(
        [('m_v', 'M.V'),
         ('h_r', 'H.R'),
         ('b_c', 'B.C'),
         ('o_c', 'O.C'),
         ('ds', 'DS')],
        string='Sample Position'
    )
    oxidation = fields.Selection(
        [('vox', 'VOX'),
         ('mox', 'MOX'),
         ('wox', 'WOX')],
        string='Oxidation'
    )

    alteration = fields.Selection(
        [('lem', 'LEM'),
         ('hem', 'HEM'),
         ('mag', 'MAG')],
        string='Alteration'
    )
    notes = fields.Text(string='Notes')



    def unlink(self):
        if not self.chemical_request_id.state == 'draft':
            raise UserError("Only draft records can be deleted!")

        return super(ChemicalSamplesLine, self).unlink()

    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('chemical_request_id'):
                request = self.env['chemical.samples.request'].browse(val['chemical_request_id'])
        return super().create(vals)


class WeightLandedCostLine(models.Model):
    _name = "weight.request.landedcost.line"

    name = fields.Char("Name")
    product_id = fields.Many2one("product.product", "Product")
    product_qty = fields.Float("Quantity")
    unit_price = fields.Float("Unit Price", compute="get_unit_price")
    total = fields.Float("Total", compute="_compute_total", store=True)
    discount = fields.Float("Discount ", compute="get_unit_price")
    weight_id = fields.Many2one("weight.request", "Request")

    is_landed_costs_line = fields.Boolean()

    @api.depends('product_qty', 'unit_price')
    def _compute_total(self):
        for record in self:
            record.total = record.product_qty * record.unit_price

    @api.onchange('is_landed_costs_line')
    def _onchange_is_landed_costs_line(self):
        if self.product_id:
            accounts = self.product_id.product_tmpl_id._get_product_accounts()
            if self.product_type != 'service':
                self.is_landed_costs_line = False

    # @api.onchange('product_id')
    # def _onchange_is_landed_costs_line_product(self):
    # 	if self.product_id.landed_cost_ok:
    # 		self.is_landed_costs_line = True
    # 	else:
    # 		self.is_landed_costs_line = False

    @api.depends('product_id', 'product_qty', 'weight_id.quantity')
    def get_unit_price(self):

        for rec in self:

            # if not rec.weight_id.average:
            # 	raise UserError(_("Please Enter the average"))

            produt_qty = rec.weight_id.quantity
            average_qty = rec.weight_id.average
            if rec.product_id.landed_cost_ok:
                rec.is_landed_costs_line = True
            else:
                rec.is_landed_costs_line = False

            rec.product_qty = produt_qty

            # print ("@@@@@@@@@@@@@",rec.product_qty)

            # if rec.product_id.type=='product':
            discount = 0.0
            rec.discount = 0.0
            rec.unit_price = 0.0

            price_list = self.env['purchase.price.list'].search([])
            for line in price_list:
                price = 0.0
                # qty=rec.product_qty
                # print ("@@@@@@@@@@@@@",qty)

                price_max = line.qty_max
                price_min = line.qty_min

                # area_list=self.env['x_area'].search([('id','=',rec.weight_id.area_id.id),('x_studio_vendor','=',rec.weight_id.transporter_id.id)],limit=1)
                area_list = self.env['x_area'].search([('id', '=', rec.weight_id.area_id.id)], limit=1)
                #####################discount for vendoer

                if rec.weight_id.partner_id == rec.weight_id.transporter_id:
                    discount = 100
                else:
                    # If not, continue with the regular discount logic
                    discount = line.discount

                if rec.weight_id.rock_vendor.max_grade:
                    grade = rec.weight_id.rock_vendor.max_grade
                    ###############################high grade################################
                    if average_qty >= grade:
                        if rec.product_id.type == 'product':
                            if average_qty >= price_min and average_qty <= price_max:
                                rec.unit_price = price
                                rec.discount = 0.0
                                price = line.unit_price
                                rec.unit_price = price
                                rec.discount = 0.0

                        else:
                            # if average_qty >=price_min and average_qty<=price_max:
                            rec.unit_price = area_list.x_studio_unit_price

                            rec.discount = 100
                    #########################################################################

                    else:
                        ############################discount on area#########################
                        if area_list.x_studio_discount_on_ore_price:

                            if average_qty < area_list.x_studio_discount_on_ore_price:
                                if rec.product_id.type == 'product':
                                    price = 0.0
                                    rec.unit_price = price
                                    rec.discount = 0.0
                                else:
                                    rec.unit_price = area_list.x_studio_unit_price
                                    # if average_qty >=price_min and average_qty<=price_max:
                                    # rec.unit_price=price
                                    rec.discount = 100

                            ###################new code ##########################################
                            elif average_qty >= 1.50 and average_qty <= 1.99 and area_list.x_studio_special_discount_1 == True:
                                if rec.product_id.type == 'product':
                                    if average_qty >= price_min and average_qty <= price_max:
                                        price = line.unit_price
                                        rec.unit_price = price
                                        rec.discount = 0.0
                                else:
                                    rec.unit_price = area_list.x_studio_unit_price
                                    # if average_qty >=price_min and average_qty<=price_max:
                                    # rec.unit_price=price
                                    rec.discount = 75

                            ###############################################################

                            else:
                                if rec.product_id.type == 'product':
                                    if average_qty >= price_min and average_qty <= price_max:
                                        price = line.unit_price
                                        rec.unit_price = price
                                        rec.discount = 0.0

                                else:
                                    rec.unit_price = area_list.x_studio_unit_price
                                    if average_qty >= price_min and average_qty <= price_max:
                                        # discount = line.discount
                                        rec.discount = discount

                        ############################discount on area#########################
                        if area_list.x_studio_discount_on_transportation:

                            if average_qty < area_list.x_studio_discount_on_transportation:
                                if rec.product_id.type == 'product':
                                    if average_qty >= price_min and average_qty <= price_max:
                                        price = line.unit_price
                                        rec.discount = 0.0
                                else:
                                    rec.unit_price = area_list.x_studio_unit_price
                                    # if average_qty >=price_min and average_qty<=price_max:
                                    # rec.unit_price=price
                                    rec.discount = 100


                            else:
                                if rec.product_id.type == 'product':
                                    if average_qty >= price_min and average_qty <= price_max:
                                        price = line.unit_price
                                        rec.unit_price = price
                                        rec.discount = 0.0

                                else:
                                    rec.unit_price = area_list.x_studio_unit_price
                                    if average_qty >= price_min and average_qty <= price_max:
                                        # discount = line.discount
                                        rec.discount = discount




                        ############################discount on area#########################

                        else:
                            if rec.product_id.type == 'product':
                                if average_qty >= price_min and average_qty <= price_max:
                                    rec.unit_price = price
                                    rec.discount = 0.0
                                    price = line.unit_price
                                    rec.unit_price = price
                                    rec.discount = 0.0

                            else:
                                rec.unit_price = area_list.x_studio_unit_price
                                if average_qty >= price_min and average_qty <= price_max:
                                    # discount = line.discount
                                    rec.discount = discount


                else:
                    ##########################discount for specific area with
                    if area_list.x_studio_discount_on_ore_price:
                        if average_qty < area_list.x_studio_discount_on_ore_price:
                            if rec.product_id.type == 'product':
                                price = 0.0
                                rec.unit_price = price
                                rec.discount = 0.0
                            else:
                                rec.unit_price = area_list.x_studio_unit_price
                                # if average_qty >=price_min and average_qty<=price_max:
                                # rec.unit_price=price
                                rec.discount = 100



                        #############################new code #######################
                        elif average_qty >= 1.50 and average_qty <= 1.99 and area_list.x_studio_special_discount_1 == True:
                            if rec.product_id.type == 'product':
                                if average_qty >= price_min and average_qty <= price_max:
                                    price = line.unit_price
                                    rec.unit_price = price
                                    rec.discount = 0.0
                            else:
                                rec.unit_price = area_list.x_studio_unit_price
                                # if average_qty >=price_min and average_qty<=price_max:
                                # rec.unit_price=price
                                rec.discount = 75
                        #######################################################################

                        else:
                            if rec.product_id.type == 'product':
                                if average_qty >= price_min and average_qty <= price_max:
                                    rec.unit_price = price
                                    rec.discount = 0.0

                                    price = line.unit_price
                                    rec.unit_price = price
                                    # discount=line.discount
                                    rec.discount = 0.0

                            else:
                                rec.unit_price = area_list.x_studio_unit_price
                                if average_qty >= price_min and average_qty <= price_max:
                                    # discount = line.discount
                                    rec.discount = discount
                                else:
                                    pass

                        ############################discount on area#########################
                        if area_list.x_studio_discount_on_transportation:

                            if average_qty < area_list.x_studio_discount_on_transportation:
                                if rec.product_id.type == 'product':
                                    if average_qty >= price_min and average_qty <= price_max:
                                        price = line.unit_price
                                        rec.discount = 0.0
                                else:
                                    rec.unit_price = area_list.x_studio_unit_price
                                    # if average_qty >=price_min and average_qty<=price_max:
                                    # rec.unit_price=price
                                    rec.discount = 100


                            else:
                                if rec.product_id.type == 'product':
                                    if average_qty >= price_min and average_qty <= price_max:
                                        price = line.unit_price
                                        rec.unit_price = price
                                        rec.discount = 0.0

                                else:
                                    rec.unit_price = area_list.x_studio_unit_price
                                    if average_qty >= price_min and average_qty <= price_max:
                                        # discount = line.discount
                                        rec.discount = discount





                    else:
                        if rec.product_id.type == 'product':
                            if average_qty >= price_min and average_qty <= price_max:
                                rec.unit_price = price
                                rec.discount = 0.0

                                price = line.unit_price
                                rec.unit_price = price
                                # discount=line.discount
                                rec.discount = 0.0

                        else:
                            rec.unit_price = area_list.x_studio_unit_price
                            if average_qty >= price_min and average_qty <= price_max:
                                rec.discount = discount
                            else:
                                pass



class WeightOrderLine(models.Model):
    _name = "weight.request.line"

    name = fields.Char("Name")
    product_id = fields.Many2one("product.product", "Product")
    product_qty = fields.Float("Quantity")
    incentive_price = fields.Float("Bonus/Discount")
    unit_price = fields.Float("Unit Price", compute="get_unit_price")
    discount = fields.Float("Discount ", compute="get_unit_price")
    weight_id = fields.Many2one("weight.request", "Request")

    is_landed_costs_line = fields.Boolean()
    self_deportation = fields.Boolean()

    # total = fields.Float("Total",store=True)
    total = fields.Float("Total",compute="_compute_total",store=True)

    percentage = fields.Float(string="Percentage (%)")

    # analytic_account_id = fields.Many2one("account.analytic.account",
    #                                       string="Analytic Account", )


    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account",
                                          inverse='_compute_dummy',
                                          compute='get_analytic_account_id', readonly=False, store=True)





    # @api.onchange('incentive_price')
    # def get_analytic_account_id(self):
    #     for rec in self:
    #         analytic = self.env['account.analytic.account'].search(
    #             [('partner_id', '=', rec.weight_id.rock_vendor.id)],
    #             limit=1
    #         )
    #         if rec.weight_id.x_studio_supplier_type=='OPU':
    #             rec.analytic_account_id = analytic



    # @api.onchange('product_id', 'incentive_price')
    # def get_analytic_account_id(self):
    #     for rec in self:
    #         supplier_type = rec.weight_id.x_studio_supplier_type
    #         if rec.incentive_price == 100 and supplier_type and 'MATERIAL MINDS' in supplier_type.mapped('name'):     
    #             analytic = self.env['account.analytic.account'].search(
    #                 [('partner_id', '=', rec.weight_id.rock_vendor.id)],
    #                 limit=1)
    #             rec.analytic_account_id = analytic if analytic else False
    #         else:
    #             rec.analytic_account_id = rec.weight_id.analytic_account_id if rec.weight_id.analytic_account_id else False

   

    @api.onchange('product_id', 'incentive_price')
    def get_analytic_account_id(self):
        for rec in self:
            supplier_type = rec.weight_id.x_studio_supplier_type
            rock_vendor = rec.weight_id.rock_vendor

            # Default analytic from the parent (if any)
            analytic_account = rec.weight_id.analytic_account_id

            # Condition: 100 incentive and MATERIAL MINDS supplier type
            if (
                rec.incentive_price == 100
                and supplier_type
                and any('MATERIAL MINDS' in name for name in supplier_type.mapped('name'))
                and rock_vendor
            ):
                # Search for analytic account linked to that vendor
                analytic = self.env['account.analytic.account'].search(
                    [('partner_id', '=', rock_vendor.id)],
                    limit=1
                )
                analytic_account = analytic or analytic_account

            # Apply the result
            rec.analytic_account_id = analytic_account
            


    def _compute_dummy(self):
        pass



    # is_opu_user = fields.Boolean(compute='_compute_is_opu_user', store=False)

    # @api.depends()
    # def _compute_is_opu_user(self):
    #     for rec in self:
    #         rec.is_opu_user = self.env.user.has_group('material_request.group_opu_user')



    @api.depends('product_qty', 'unit_price', 'incentive_price')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.product_qty * (rec.unit_price + rec.incentive_price)



    @api.depends('product_id', 'product_qty','percentage', 'weight_id.quantity')
    def get_unit_price(self):

        for rec in self:
            rec.unit_price = 0.0
            rec.discount = 0.0

            # 🚫 Skip calculation for company share line
            if rec.product_id.is_company_percentage:
                continue

            produt_qty = rec.weight_id.quantity
            average_qty = rec.weight_id.average
            if rec.product_id.landed_cost_ok:
                rec.is_landed_costs_line = True
            else:
                rec.is_landed_costs_line = False

            rec.product_qty = produt_qty

            # print ("@@@@@@@@@@@@@",rec.product_qty)

            # if rec.product_id.type=='product':
            discount = 0.0
            rec.discount = 0.0
            rec.unit_price = 0.0

            price_list = self.env['purchase.price.list'].search([])
            for line in price_list:
                price = 0.0
                # qty=rec.product_qty
                # print ("@@@@@@@@@@@@@",qty)

                price_max = line.qty_max
                price_min = line.qty_min

                # area_list=self.env['x_area'].search([('id','=',rec.weight_id.area_id.id),('x_studio_vendor','=',rec.weight_id.transporter_id.id)],limit=1)
                area_list = self.env['x_area'].search([('id', '=', rec.weight_id.area_id.id)], limit=1)
                #####################discount for vendoer

                if rec.weight_id.partner_id == rec.weight_id.transporter_id:
                    discount = 100

                # elif getattr(line, 'incentive_price', 0) > 0:
                #     rec.discount = line.incentive_price
                #     print ("########################################3",rec.discount)

                else:
                    # If not, continue with the regular discount logic
                    discount = line.discount

                if rec.weight_id.rock_vendor.max_grade:
                    grade = rec.weight_id.rock_vendor.max_grade
                    ###############################high grade################################
                    if average_qty >= grade:
                        if rec.product_id.type == 'product':
                            if average_qty >= price_min and average_qty <= price_max:
                                rec.unit_price = price
                                rec.discount = 0.0
                                price = line.unit_price
                                rec.unit_price = price
                                rec.discount = 0.0

                        else:
                            # if average_qty >=price_min and average_qty<=price_max:
                            rec.unit_price = area_list.x_studio_unit_price
                            if rec.product_id.product_tmpl_id.self_deportation:
                                rec.discount = 0.0
                            else:
                                rec.discount = 100
                    #########################################################################

                    else:
                        ############################discount on area#########################
                        if area_list.x_studio_discount_on_ore_price:

                            if average_qty < area_list.x_studio_discount_on_ore_price:
                                if rec.product_id.type == 'product':
                                    price = 0.0
                                    rec.unit_price = price
                                    rec.discount = 0.0
                                else:
                                    rec.unit_price = area_list.x_studio_unit_price
                                    # if average_qty >=price_min and average_qty<=price_max:
                                    # rec.unit_price=price

                                    if rec.product_id.product_tmpl_id.self_deportation:
                                        rec.discount = 0.0
                                    else:
                                        rec.discount = 100

                            ###################new code ##########################################
                            elif average_qty >= 1.50 and average_qty <= 1.99 and area_list.x_studio_special_discount_1 == True:
                                if rec.product_id.type == 'product':
                                    if average_qty >= price_min and average_qty <= price_max:
                                        price = line.unit_price
                                        rec.unit_price = price
                                        rec.discount = 0.0
                                else:
                                    rec.unit_price = area_list.x_studio_unit_price
                                    # if average_qty >=price_min and average_qty<=price_max:
                                    # rec.unit_price=price
                                    if rec.product_id.product_tmpl_id.self_deportation:
                                        rec.discount = 0.0
                                    else:
                                       rec.discount = 75

                            ###############################################################

                            else:
                                if rec.product_id.type == 'product':
                                    if average_qty >= price_min and average_qty <= price_max:
                                        price = line.unit_price
                                        rec.unit_price = price
                                        rec.discount = 0.0

                                else:
                                    rec.unit_price = area_list.x_studio_unit_price
                                    if average_qty >= price_min and average_qty <= price_max:
                                        # discount = line.discount
                                        if rec.product_id.product_tmpl_id.self_deportation:
                                            rec.discount = 0.0
                                        else:

                                            rec.discount = discount

                        ############################discount on area#########################
                        if area_list.x_studio_discount_on_transportation:

                            if average_qty < area_list.x_studio_discount_on_transportation:
                                if rec.product_id.type == 'product':
                                    if average_qty >= price_min and average_qty <= price_max:
                                        price = line.unit_price
                                        rec.discount = 0.0
                                else:
                                    rec.unit_price = area_list.x_studio_unit_price
                                    # if average_qty >=price_min and average_qty<=price_max:
                                    # rec.unit_price=price
                                    if rec.product_id.product_tmpl_id.self_deportation:
                                        rec.discount = 0.0
                                    else:
                                        rec.discount = 100



                            else:
                                if rec.product_id.type == 'product':
                                    if average_qty >= price_min and average_qty <= price_max:
                                        price = line.unit_price
                                        rec.unit_price = price
                                        rec.discount = 0.0

                                else:
                                    rec.unit_price = area_list.x_studio_unit_price
                                    if average_qty >= price_min and average_qty <= price_max:
                                        # discount = line.discount
                                        if rec.product_id.product_tmpl_id.self_deportation:
                                            rec.discount = 0.0
                                        else:

                                            rec.discount = discount




                        ############################discount on area#########################

                        else:
                            if rec.product_id.type == 'product':
                                if average_qty >= price_min and average_qty <= price_max:
                                    rec.unit_price = price
                                    rec.discount = 0.0
                                    price = line.unit_price
                                    rec.unit_price = price
                                    rec.discount = 0.0

                            else:
                                rec.unit_price = area_list.x_studio_unit_price
                                if average_qty >= price_min and average_qty <= price_max:
                                    # discount = line.discount
                                    if rec.product_id.product_tmpl_id.self_deportation:
                                        rec.discount = 0.0
                                    else:

                                        rec.discount = discount


                else:
                    ##########################discount for specific area with
                    if area_list.x_studio_discount_on_ore_price:
                        if average_qty < area_list.x_studio_discount_on_ore_price:
                            if rec.product_id.type == 'product':
                                price = 0.0
                                rec.unit_price = price
                                rec.discount = 0.0
                            else:
                                rec.unit_price = area_list.x_studio_unit_price
                                # if average_qty >=price_min and average_qty<=price_max:
                                # rec.unit_price=price
                                if rec.product_id.product_tmpl_id.self_deportation:
                                    rec.discount = 0.0
                                else:
                                    rec.discount = 100




                        #############################new code #######################
                        elif average_qty >= 1.50 and average_qty <= 1.99 and area_list.x_studio_special_discount_1 == True:
                            if rec.product_id.type == 'product':
                                if average_qty >= price_min and average_qty <= price_max:
                                    price = line.unit_price
                                    rec.unit_price = price
                                    rec.discount = 0.0
                            else:
                                rec.unit_price = area_list.x_studio_unit_price
                                # if average_qty >=price_min and average_qty<=price_max:
                                # rec.unit_price=price
                                if rec.product_id.product_tmpl_id.self_deportation:
                                    rec.discount = 0.0
                                else:
                                    rec.discount = 75

                        #######################################################################

                        else:
                            if rec.product_id.type == 'product':
                                if average_qty >= price_min and average_qty <= price_max:
                                    rec.unit_price = price
                                    rec.discount = 0.0

                                    price = line.unit_price
                                    rec.unit_price = price
                                    # discount=line.discount
                                    rec.discount = 0.0

                            else:
                                rec.unit_price = area_list.x_studio_unit_price
                                if average_qty >= price_min and average_qty <= price_max:
                                    # discount = line.discount
                                    if rec.product_id.product_tmpl_id.self_deportation:
                                        rec.discount = 0.0
                                    else:

                                        rec.discount = discount
                                else:
                                    pass

                        ############################discount on area#########################
                        if area_list.x_studio_discount_on_transportation:

                            if average_qty < area_list.x_studio_discount_on_transportation:
                                if rec.product_id.type == 'product':
                                    if average_qty >= price_min and average_qty <= price_max:
                                        price = line.unit_price
                                        rec.discount = 0.0
                                else:
                                    rec.unit_price = area_list.x_studio_unit_price
                                    # if average_qty >=price_min and average_qty<=price_max:
                                    # rec.unit_price=price
                                    if rec.product_id.product_tmpl_id.self_deportation:
                                        rec.discount = 0.0
                                    else:
                                        rec.discount = 100



                            else:
                                if rec.product_id.type == 'product':
                                    if average_qty >= price_min and average_qty <= price_max:
                                        price = line.unit_price
                                        rec.unit_price = price
                                        rec.discount = 0.0

                                else:
                                    rec.unit_price = area_list.x_studio_unit_price
                                    if average_qty >= price_min and average_qty <= price_max:
                                        # discount = line.discount
                                        if rec.product_id.product_tmpl_id.self_deportation:
                                            rec.discount = 0.0
                                        else:

                                            rec.discount = discount





                    else:
                        if rec.product_id.type == 'product':
                            if average_qty >= price_min and average_qty <= price_max:
                                rec.unit_price = price
                                rec.discount = 0.0

                                price = line.unit_price
                                rec.unit_price = price
                                # discount=line.discount
                                rec.discount = 0.0

                        else:
                            rec.unit_price = area_list.x_studio_unit_price
                            if average_qty >= price_min and average_qty <= price_max:

                                if rec.product_id.product_tmpl_id.self_deportation:
                                    rec.discount = 0.0
                                else:

                                    rec.discount = discount
                            else:
                                pass


            # ✅ Final override: apply incentive if present
            if rec.incentive_price:
                if rec.product_id.type=='service':
                    incentive_price=rec.incentive_price
                    rec.discount = incentive_price


            # ✅ Call update after all price logic is finished
            if rec.product_id.type == 'product' and rec.weight_id:
                rec.weight_id._update_company_share_line()


    # @api.constrains('percentage')
    # def _constrain_update_company_share(self):
    #     for line in self:
    #         if line.product_id.is_company_percentage and line.weight_id:
    #             line.weight_id._update_company_share_line()

    @api.onchange('percentage')
    def _onchange_percentage(self):
        if self.product_id.is_company_percentage and self.weight_id:
            self.weight_id._update_company_share_line()



    @api.onchange('is_landed_costs_line')
    def _onchange_is_landed_costs_line(self):
        if self.product_id:
            accounts = self.product_id.product_tmpl_id._get_product_accounts()
            if self.product_type != 'service':
                self.is_landed_costs_line = False




class PurchasePriceList(models.Model):
    _name = "purchase.price.list"

    name = fields.Char("Name")
    qty_min = fields.Float("Min")
    qty_max = fields.Float("Max")
    unit_price = fields.Float("Unit Price")
    discount = fields.Float("Discount")


class ChemicalSamplesSequnces(models.Model):
    _name = "chemical.samples.sequences"
    name = fields.Char("")
    category = fields.Selection([('crusher', 'Crusher'), ('cic', 'CIC'), ('cil', 'CIL')])
    daily_night = fields.Selection([('crd', 'CR-D'), ('hd', 'HD'), ('crn', 'CR-N',), ('hn', "HN"), ('hp', 'HP')],
                                   string="CRUSHER/Sample Sequence")
    cic_samples = fields.Selection(
        [('factory', 'Factory samples'), ('stripping', 'Stripping samples'), ('carbon', 'Carbon')],
        string="CIC/Sample Sequence")
    cic_sub_samples = fields.Selection(
        [('unit_one_old', 'Unit One '), ('unit_two_old', 'Unit Two '), ('unit_three_old', 'Unit Three'),
         ('unit_four_old', 'Unit Four'), ('unit_five_old', 'Unit Five') ,
         ('bs_6', 'BS6') , ('pregnant_sample', 'Pregnant Sample'),('manhole', 'Manhole Sample'),],
        string="Sub Sample")
    sample_no = fields.Integer(string='Sample No', required=True)


class Incentivecategory(models.Model):
    _name = 'incentive.category'

    name = fields.Char("Name")
    max_grade = fields.Float("Max Grade", default="")
    min_grade = fields.Float("Min Grade")


class IncentiveClasses(models.Model):
    _name = 'incentive.classes'

    name = fields.Char("Name")
    max_ton = fields.Float("Max Ton", default="")
    min_ton = fields.Float("Min Ton")
    incentive_category_id = fields.Many2one("incentive.category", "Incentive Category")
    support = fields.Float("Support%")


class StockLot(models.AbstractModel):
    _inherit = 'stock.lot'

    ore_ph = fields.Float("PH")
    weight_request_ids = fields.One2many('weight.request','lot_id',string='Weight Requests')
    display_name_qty = fields.Char(string="Batch Info",store=True)
    ore_types = fields.Char(string='All Ore Types', compute='_compute_ore_types')

    state = fields.Selection(string="", selection=[
        ('un_received', 'Un Received'),
        ('received', 'Received'),
        ('water', 'Water'),
        ('tchoin', 'Tchoin'),
        ('plan', 'Planning to Produce'),
        ('produced', ' Produced'),

    ], default='un_received')
    ore_workflow = fields.Boolean(string="Ore Workflow" , default=False)

    stock_move_line_ids = fields.One2many(
        'stock.move.line', 'lot_id', string="Stock Move Lines"
    )
    total_average = fields.Float(string="Total Average",compute="_compute_average")

    @api.depends('weight_request_ids.type_ore')
    def _compute_ore_types(self):
        for lot in self:
            types = lot.weight_request_ids.mapped('type_ore')
            lot.ore_types = ', '.join(filter(None, types))

    @api.depends('name','product_qty')
    def _compute_display_name(self):
        for lot in self:
            lot.display_name = f"{lot.name} / {lot.product_qty}"




    def _compute_average(self):
        for lot in self:
            # Filter moves where lot.id exists in move's lot_ids
            moves = self.env['stock.move'].search([
                ('lot_ids', 'in', lot.id),  # Ensure this move is linked to the lot
                ('state', '=', 'done'),  # Consider only completed stock moves
                ('average', '>', 0)  # Ignore zero or negative averages
            ])

            # Ensure we only calculate the average for this specific lot, not all moves' lot_ids
            valid_moves = moves.filtered(lambda move: lot.id in move.lot_ids.ids)

            print(f">>>>>>> Lot {lot.id} >>>>> Valid Moves: {valid_moves.mapped('id')}")

            # Compute total average
            lot.total_average = sum(valid_moves.mapped('average')) / len(valid_moves) if valid_moves else 0.0

    @api.model
    def set_state(self, new_state):
        """Set the state to the given value."""
        self.ensure_one()
        self.state = new_state

    def action_Received(self):
        self.set_state('received')

    def action_water(self):
        self.set_state('water')

    def action_tchoin(self):
        self.set_state('tchoin')

    def action_plan(self):
        self.set_state('plan')

    def action_done(self):
        self.set_state('produced')

    @api.model
    def create(self, vals):
        for val in vals:
            if 'name' in val and val['name']:
                if re.search(r'[a-z]', val['name']):  # Check for lowercase letters
                    raise ValidationError(_("Lot/Serial Number must be in UPPERCASE letters only."))
                val['name'] = val['name'].upper()  # Ensure it's stored in uppercase

        return super(StockLot, self).create(vals)


class GeologySample(models.Model):
    _name = "geology.sample"
    _description = "Geology Sample"

    weight_request_id = fields.Many2one('weight.request', string="Weight Request")

    ox = fields.Selection([
        ('vox', 'Very Oxide'),
        ('mox', 'Medium Oxide'),
        ('won', 'Weak Oxide'),
    ], string="Oxidation")

    altr = fields.Selection([
        ('lem', 'Limonite'),
        ('hem', 'Hematite'),
        ('mag', 'Magnetite'),
    ], string="Alteration.")

    note = fields.Text(string="Note")

class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    weight_id = fields.Many2one("weight.request", "Request")
    analytic_account_id = fields.Many2one("account.analytic.account", string="Analytic Account", )
