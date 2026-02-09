# -*- coding: utf-8 -*-
# Copyright 2016 Eficent Business and IT Consulting Services S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl-3.0).
from docutils.nodes import field
from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
import random


class IssuanceRequest(models.Model):
    _name = 'issuance.request'
    _description = 'Issuance Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _rec_name = 'name'
    _order = 'name desc'

    def _default_analytic_account_id(self):
        if self.env.user.default_analytic_account_id.id:
            return self.env.user.default_analytic_account_id.id

    name = fields.Char('IS Number', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    equipment_id = fields.Many2one(comodel_name="maintenance.equipment", string="Equipment", required=False, )
    request_date = fields.Date('Request Date', help="Date when the user initiated the request.",
                               default=fields.Date.context_today, track_visibility='onchange')
    requested_by = fields.Many2one('res.users', 'Receiver', track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True, readonly=True)
    store_keeper = fields.Many2one('res.users', 'Store Keeper', track_visibility='onchange')
    warehouse_id = fields.Many2one('stock.warehouse', "Warehouse")
    dest_location = fields.Many2one('stock.location', 'Source Location', track_visibility='onchange')
    description = fields.Html('Description')
    title = fields.Char()
    origin = fields.Char("Source Document")
    line_ids = fields.One2many('issuance.request.line', 'request_id', 'Products to Purchase', readonly=False, copy=True,
                               track_visibility='onchange')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('line_approve', 'Waiting for Line Manager'),
        ('to_inventory', 'Waiting for inventory Approve'),
        ('done', 'Approved'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')

    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', domain=[('code', '=', 'internal')])
    picking_count = fields.Integer(string="Count", compute='compute_picking_count')

    department_id = fields.Many2one('hr.department', string='Department',
                                    default=lambda self: self._get_default_department())

    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account",
                                          default=_default_analytic_account_id)
    company_id = fields.Many2one('res.company')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id)
    amount_total = fields.Monetary('Total', compute='compute_totals', store=False)
    # Special Dates
    inventory_check_date = fields.Date()
    lm_approval_date = fields.Date("LM Approval Date")
    stock_user_id = fields.Many2one('res.users', "Stock Manager", copy=False)
    request_id = fields.Many2one('material.request', "Material Request", copy=False)
    mr_type = fields.Selection(related="request_id.item_type", string="MR Type")

    delivery_address = fields.Many2one("res.partner", "Vendor")
    issuance_type = fields.Selection(
        [('internal_issuance', 'Internal Issuance'), ('external_issuance', 'External Issuance')], "Issuance Type",
        default="internal_issuance")

    status = fields.Char('Inventory Status')

    issuance_location_id = fields.Many2one("issuance.location", string="Location")
    product_id = fields.Many2one('product.product', related='line_ids.product_id', string='Product', readonly=False)
    security_number = fields.Integer(string='Security Number', copy=False)
    show_button = fields.Boolean(compute='_compute_show_button', string='Show Button', copy=False)
    user_ids = fields.Many2many(comodel_name="res.users", string="Who Will see Receipt Confirmation Number", copy=False)
    
    warehouse_location = fields.Many2one(
        related='warehouse_id.issuance_location', 
        string='Location',
        readonly=False, 
    )

    issuance_new_location = fields.Many2one("stock.location", string="Location")
    m_request_id = fields.Many2one('maintenance.request', "Maintenance Request", copy=False)

    @api.depends('user_ids', 'product_id')
    def _compute_show_button(self):
        for record in self:
            if self.product_id:
                if self.product_id.categ_id and not 'Gasoline'.lower() in self.product_id.categ_id.name.lower():
                    if self.env.user.id in self.user_ids.ids or self.requested_by.id == self.env.user.id or self.requested_by.line_manager_id.id == self.env.user.id:
                        record.show_button = True
                    else:
                        if self.env.user.has_group('base.group_system'):
                            record.show_button = True
                        else:
                            record.show_button = False
                else:
                    record.show_button = False
            else:
                record.show_button = False

    def _generate_security_number(self):
        return random.randint(100000, 999999)

    @api.onchange('equipment_id')
    def onchage_equi(self):
        if self.equipment_id.analytic_account_id.id:
            self.analytic_account_id = self.equipment_id.analytic_account_id.id

    # lm manager buttons
    def action_approve_sheets(self):

        self.ensure_one()
        line_managers = []
        today = fields.Date.today()
        line_manager = False
        try:
            line_manager = self.requested_by.line_manager_id or self.employee_id.parent_id.user_id
        except:
            line_manager = False

        if not line_manager or line_manager != self.env.user:
            raise UserError("Sorry. Your are not authorized to approve this document!")
        self.write({'state': 'to_inventory'})

    def get_requested_by(self):
        user = self.env.user.id
        return user

    @api.depends('requested_by')
    def compute_edit_cost_center(self):
        self.edit_analytic_account = self.env.user.has_group('base_op.group_edit_cost_center')

    def check_product(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Please add Issuance lines!")

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('issuance_request.sequence') or "/"

        return super(IssuanceRequest, self).create(vals)

    @api.model
    def _get_default_picking_type(self):
        return self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            (
                'warehouse_id.company_id', 'in',
                [self.env.context.get('company_id', self.env.user.company_id.id), False])],
            limit=1).id

    def compute_picking_count(self):
        self.picking_count = self.env['stock.picking'].search_count([('issuance_request_id', '=', self.id)])
        self.status = self.env['stock.picking'].search([('issuance_request_id', '=', self.id)], limit=1).state

    def _get_default_department(self):
        return self.env.user.department_id.id if self.env.user.department_id else False

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Only draft records can be deleted!")

        return super(IssuanceRequest, self).unlink()

    ## Submit to Inventory

    def button_to_lm(self):
        for rec in self:

            if self.analytic_account_id.company_id and self.analytic_account_id.company_id != self.company_id:
                raise UserError('the Cost Center Incompatible for the Company')

            if not self.requested_by.id == self.env.user.id:
                raise UserError('Sorry, Only requester can submit this document!')
            if self.product_id.categ_id.name:
                if not 'Gasoline'.lower() in self.product_id.categ_id.name.lower():
                    self.security_number = self._generate_security_number()
            for line in rec.line_ids:
                if not line.qty_requested:
                    raise UserError(_("%sPlease Specify Requested QTY to proceed") % line.product_id.name)

                if line.qty_requested> line.qty_available:
                    raise UserError("The Requested Quantity > Available")

            if rec.issuance_type == 'internal_issuance':
                rec.write({'state': 'to_inventory'})
            else:
                if not rec.delivery_address:
                    raise UserError('Please Enter The Vendor')
                rec.write({'state': 'line_approve'
                           })

            # rec.write({'state': 'line_approve',
            #            })
            rec.check_product()

    def button_to_inventory(self):
        for rec in self:
            if not self.requested_by.id == self.env.user.id:
                raise UserError('Sorry, Only requester can submit this document!')
            for line in rec.line_ids:
                if not line.qty_requested:
                    raise UserError(" Please Specify Requested QTY to proceed")

            rec.write({'state': 'to_inventory',
                       })
            rec.check_product()

    # Set draft
    def button_draft(self):
        # self.mapped('line_ids').do_uncancel()
        return self.write({'state': 'draft'})

    # Stock check issued qty and create dlivery

    def action_stock_delivery(self):
        for order in self:
            if not order.line_ids:
                raise UserError(_('Please create Issuance Request lines.'))
            if not order.issuance_type:
                raise UserError(_('Please write the type of Issuance'))

            # old code if not self.dest_location:
            ############## modified by ekhlas
            if not self.warehouse_id:
                raise UserError('Please Add Warehouse !')
            for line in order.line_ids:
                if not line.qty_issued:
                    raise UserError(" Please Specify Issued QTY to proceed")
                if line.qty_issued > line.qty_requested:
                    raise UserError("The Issued Quantity must be equal or lessthan Requested QTY")

            # Default Location and Picking Type
            # old code ##########################
            # warehouse = self.env['stock.warehouse'].search([])
            ################add line below by ekhlas code############
            warehouse = self.env['stock.warehouse'].search([('id', '=', order.warehouse_id.id)])

            # old code ##########################
            # pickingType = self.env['stock.picking.type'].sudo().search(
            #     [('code', '=', 'outgoing'),('issued','=',True),('company_id','=',order.company_id.id)])

            ##################add line by ekhlas code 
            pickingType = self.env['stock.picking.type'].sudo().search(
                [('code', '=', 'outgoing'), ('issued', '=', True), ('warehouse_id', '=', order.warehouse_id.id)])

            location_dest_id = warehouse.issuance_location
            if self.issuance_new_location:
                location_dest_id=self.issuance_new_location
            # old code######################3
            # location_id = self.dest_location
            # ekhlas code ######################3
            location_id = warehouse.lot_stock_id

            if not warehouse or not pickingType:
                raise UserError("Stock locations are not properly set.warehouse,pickingType")
            elif not location_id or not location_dest_id:
                raise UserError("Stock locations are not properly set.location_id,location_dest_id")
            print('>>>>>>>>>>>>>>>>>>>>. location_dest_id',location_dest_id)
            # pass
            deliver_pick = {
                'picking_type_id': pickingType.id,
                'origin': self.name,
                'partner_id': self.delivery_address.id,
                'issuance_request_id': self.id,
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id,
                'analytic_account_id': line.analytic_account_id.id
            }
            deliver_picking = self.env['stock.picking'].sudo().create(deliver_pick)
            moves = order.line_ids.filtered(lambda r: r.qty_issued)._create_stock_moves_transfer(deliver_picking,
                                                                                                 'deliver')
            # move_ids = moves._action_confirm()
            # move_ids._action_assign()

            picking = self.env['stock.picking'].sudo().search([('origin', '=', self.name)], limit=1)
            # picking.sudo().action_assign()
            # deliver_picking=self.env['stock.immediate.transfer'].sudo()
            # deliver_picking.sudo().process()

            # deliver_picking_id.button_validate()                                                                              'deliver')

            order.write({
                'state': 'done',
                'store_keeper': self.env.user.id,
            })

            #############ekhlas code ########################
            # for move in picking.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
            #     for move_line in move.move_line_ids:
            #         move_line.qty_done = move_line.product_uom_qty

            # pickings_to_validate = self.env.context.get('button_validate_picking_ids')
            # if pickings_to_validate:
            #     pickings_to_validate = self.env['stock.picking'].browse(pickings_to_validate)
            #     pickings_to_validate = pickings_to_validate - pickings_not_to_do
            # return picking.button_validate()

    def button_rejected(self):
        self.mapped('line_ids').do_cancel()
        return self.write({'state': 'reject'})

    def button_cancel(self):
        for request in self:
            pickings = self.env['stock.picking'].search([('issuance_request_id', '=', request.id)])
            pickings.action_cancel()
            pickings.unlink()
            request.state = 'cancel'

    def action_view_picking(self):
        return {
            'name': "Issuance Delivery",
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('issuance_request_id', '=', self.id)],
        }


class IssuanceRequestLine(models.Model):
    _name = "issuance.request.line"
    _description = "Issuance Request Line"
    _inherit = ['mail.thread']

    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('purchase_ok', '=', True)], required=True,
        track_visibility='onchange')
    name = fields.Char('Description', size=256,
                       track_visibility='onchange')
    product_uom_id = fields.Many2one('uom.uom', 'Product Unit of Measure',
                                     track_visibility='onchange')
    qty_requested = fields.Float(string='Requested Quantity', track_visibility='onchange', digits=(16, 2))

    qty_issued = fields.Float(string='Issued Quantity', track_visibility='onchange', digits=(16, 2))
    lot_ids = fields.Many2many(comodel_name="stock.lot")
    request_id = fields.Many2one('issuance.request',
                                 'Issuance No.',
                                 ondelete='cascade', readonly=True)
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 store=True, readonly=True)

    qty_available = fields.Float("Available Qty", compute='get_qty_available')
    # qty_available = fields.Float("Available Qty")

    currency_id = fields.Many2one('res.currency', related='request_id.currency_id')
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account",
                                          inverse='_compute_dummy',
                                          compute='get_analytic_account_id', readonly=False, store=True)
    equipment_id = fields.Many2one(comodel_name="maintenance.equipment", string="Equipment", required=False, )
    title = fields.Char(related="request_id.title", string="Issuance Name")

    issuance_type = fields.Selection(related="request_id.issuance_type", string='Issuance Type')

    remarks = fields.Char()
    total = fields.Monetary(compute="compute_total")

    @api.onchange('product_id')
    def get_analytic_account_id(self):
        for rec in self:
            rec.analytic_account_id = rec.request_id.analytic_account_id
            rec.equipment_id = rec.request_id.equipment_id

    def _compute_dummy(self):
        pass

    @api.model
    def create(self, vals):
        for val in vals:
            product_id = self.env['product.product'].browse(val.get('product_id'))
            qty = product_id.warehouse_quantity
            val['qty_available'] = qty
        return super(IssuanceRequestLine, self).create(vals)

    @api.depends('product_id')
    def get_qty_available(self):
        for rec in self:
            rec.qty_available = rec.product_id.qty_available

    @api.onchange('product_id')
    def onchange_product_id(self):

        if self.product_id:
            name = self.product_id.name
            if self.product_id.code:
                name = '[%s] %s' % (name, self.product_id.code)
            if self.product_id.description_purchase:
                name += '\n' + self.product_id.description_purchase
            self.product_uom_id = self.product_id.uom_id.id
            self.name = name
            self.qty_available = self.product_id.qty_available
            # self.product_type = self.product_id.product_type

    def do_cancel(self):
        """Actions to perform when cancelling a purchase request line."""
        self.write({'cancelled': True})

    def do_uncancel(self):
        """Actions to perform when uncancelling a purchase request line."""
        self.write({'cancelled': False})

    def _create_stock_moves_transfer(self, picking, qty):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self.filtered(lambda l: l.product_id):

            diff_quantity = 0.0
            mr_line = False
            if qty == 'deliver':
                diff_quantity = line.qty_issued

            template = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                # old code 'equipment_id': line.request_id.equipment_id.id,
                'equipment_id': line.equipment_id.id,
                'product_uom': line.product_id.uom_id.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'picking_id': picking.id,
                'state': 'confirmed',
                'company_id': picking.company_id.id,
                # 'price_unit': price_unit,
                'picking_type_id': picking.picking_type_id.id,
                # 'route_ids': 1 and [
                #     (6, 0, [x.id for x in self.env['stock.location.route'].search([('id', 'in', (2, 3))])])] or [],
                'warehouse_id': picking.picking_type_id.warehouse_id.id,
                'product_uom_qty': diff_quantity,
                'issuance_line_id': line.id,
                #####################add line by ekhlas code
                'analytic_distribution': {line.analytic_account_id.id:100},
                'lot_ids': [(6, 0, line.lot_ids.ids)],
            }
            new_move = moves.create(template)
            done += new_move

            # Add `analytic_account_id` after creation using `write`
            if self.analytic_account_id:
                for analytic_account in self.analytic_account_id:
                    new_move.write({
                        'analytic_account_id': analytic_account.id,
                    })

        return done


class IssuanceLocation(models.Model):
    _name = 'issuance.location'
    _description = 'Issuance Location'

    name = fields.Char('Location')
