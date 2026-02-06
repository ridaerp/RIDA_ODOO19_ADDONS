from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
from datetime import datetime


class MaterialInspection(models.Model):
    _name = 'material.inspection'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    date = fields.Date(default=fields.Date.today())
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    state = fields.Selection(
        [('draft', 'Draft'),
         ('waiting_qhse_inspection', 'Waiting QHSE Inspection'),
         ('inspection', 'Waiting User Inspection'),
         ('closed', 'Closed'),
         ('reject', 'reject'), ]
        , string='Status', default='draft', track_visibility='onchange')
    state_qhse = fields.Selection(related='state')
    employee_id = fields.Many2one("hr.employee", string="Name")
    vendor_id = fields.Many2one('res.partner',
                                string='Supplier Name')
    address = fields.Char(string="Address")
    po_number = fields.Char(string="No. of delivery permission / bill")
    inspection_ids = fields.One2many(comodel_name="material.inspection.line", inverse_name="request_id",
                                     string="Inspection Line", copy=1)
    purchase_id = fields.Many2one('purchase.order', string="Purchase")
    material_request_id = fields.Many2one('material.request', 'Main Material Request')
    material_request_ids = fields.Many2many(
        'material.request',
        'material_inspection_material_request_rel',
        string='Other Material Requests'
    )
    requested_by = fields.Many2one('res.users', related='material_request_id.requested_by', string='Requested by',
                                   track_visibility='onchange', readonly=True)
    inspector = fields.Many2one("res.users", "Inspector")
    qhse_inspector = fields.Many2one("res.users", "QHSE Inspector")
    department_id = fields.Many2one('hr.department', related='material_request_id.department_id',
                                    string="Requested Department")
    backorder_picking_id = fields.Many2one('stock.picking', 'Back Order of')
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")

    is_catering = fields.Boolean(
        string="Is Catering Product",
        compute='_compute_is_catering',
    )

    @api.depends('inspection_ids.product_id')
    def _compute_is_catering(self):
        for inspection in self:
            inspection.is_catering = False  # Default to False

            for line in inspection.inspection_ids:
                if line.product_id and line.product_id.categ_id:  # Check if product and category exist
                    # Check if the product category name contains 'food'
                    if 'food' in line.product_id.categ_id.name.lower():
                        inspection.is_catering = True
                        break  # Exit line loop - catering found
    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('material.inspection') or ' '

        return super(MaterialInspection, self).create(vals)

    def action_draft(self):
        for rec in self:
            for line in rec.inspection_ids:
                line.qty_accepted = 0
                line.qty_received = 0
                line.qty_rejected = 0
                line.note = False
        return self.write({'state': 'draft'})

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(MaterialInspection, self).unlink()

    def action_submit(self):
        if not self.is_catering:
            return self.write({'state': 'inspection', 'inspector': self.requested_by})
        else:
            return self.write({'state': 'waiting_qhse_inspection'})

    def action_qhse_validate(self):
        for rec in self.inspection_ids:
            total = rec.qty_accepted + rec.qty_rejected
            if float(format(total, ".2f")) != float(format(rec.qty_received, ".2f")):
                raise UserError("The Total of ( Qty Accepted and Qty Rejected ) Must Equal Received")
        for rec in self.inspection_ids:
            rec.qhse_qty_accepted = rec.qty_accepted
            rec.qhse_qty_rejected = rec.qty_rejected
        return self.write({'state': 'inspection', 'inspector': self.qhse_inspector})


    def action_validate(self):
        # 1. Validation Logic
        for rec in self.inspection_ids:
            # QHSE Check for catering
            if self.is_catering and rec.qty_accepted > rec.qhse_qty_accepted:
                raise UserError("Qty Accepted cannot be greater than QHSE Qty Accepted.")
            
            # Precision-safe equality check (Fixes the 64.63 error)
            total = rec.qty_accepted + rec.qty_rejected
            if float_compare(total, rec.qty_received, precision_digits=2) != 0:
                raise UserError(
                    f"Validation Error for {rec.product_id.name}:\n"
                    f"The Total of Qty Accepted ({rec.qty_accepted}) and "
                    f"Qty Rejected ({rec.qty_rejected}) Must Equal Received ({rec.qty_received})."
                )

        # 2. Update Transfer Quantities (Picking)
        if self.purchase_id.picking_ids and not self.purchase_id.ore_purchased:
            # Target the first picking record
            target_picking = self.purchase_id.picking_ids[0]
            for insp_line in self.inspection_ids:
                for move_line in target_picking.move_ids_without_package:
                    # Compare Product ID to Product ID (more reliable than Template ID)
                    if insp_line.product_id.id == move_line.product_id.id:
                        move_line.quantity = insp_line.qty_accepted

        # 3. Authorization Logic
        for rec in self:
            # Bypass for requester, assigned inspector, or Administrator
            if rec.env.user == rec.requested_by or rec.env.user == rec.inspector:
                continue
            if self.env.user.has_group('base.group_system'):
                continue
                
            # Line Manager Validation
            try:
                line_manager = rec.requested_by.line_manager_id
            except:
                line_manager = False

            if not line_manager or line_manager != rec.env.user:
                raise UserError("Sorry, you are not authorized to approve this document! Please assign the correct inspector or manager.")

        # 4. Finalize State
        return self.write({'state': 'closed'})

    
    # def action_validate(self):
    #     for rec in self.inspection_ids:
    #         if self.is_catering:
    #             if rec.qty_accepted > rec.qhse_qty_accepted:
    #                 raise UserError("Qty Accepted cannot be greater than QHSE Qty Accepted.")
    #     for rec in self.inspection_ids:
    #         total = rec.qty_accepted + rec.qty_rejected
    #         if float(format(total, ".2f")) != float(format(rec.qty_received, ".2f")):
    #             raise UserError("The Total of ( Qty Accepted and Qty Rejected ) Must Equal Received")
    #     x = self.purchase_id.picking_ids.ids
    #     for rec in self.purchase_id.picking_ids:
    #         if rec.id == x[0]:
    #             if not self.purchase_id.ore_purchased:
    #                 for rec1 in self.inspection_ids:
    #                     for line in rec.move_ids_without_package:
    #                         if rec1.product_id.id == line.product_id.product_tmpl_id.id:
    #                             line.quantity = rec1.qty_accepted
    #     for rec in self:
    #         if rec.env.user == rec.requested_by or rec.env.user == rec.inspector:
    #             pass
    #         elif self.env.user.has_group('base.group_system'):
    #             pass
    #         else:
    #             self.ensure_one()
    #             try:
    #                 line_manager = self.requested_by.line_manager_id
    #             except:
    #                 line_manager = False
    #             # comment by ekhlas
    #             # if not line_manager or not self.user_has_groups('material_request.group_department_manager'):
    #             #     raise UserError("Sorry. Your are not authorized to approve this document!")
    #             if not line_manager or line_manager != rec.env.user:
    #                 raise UserError(
    #                     "Sorry. Your are not authorized to approve this document!,please assgin the inspector")
    #     return self.write({'state': 'closed'})


class MaterialInspectionLine(models.Model):
    _name = 'material.inspection.line'

    request_id = fields.Many2one("material.inspection", string="Inspection")
    product_id = fields.Many2one(
        'product.template', 'Product',
        required=True,
        track_visibility='onchange')
    product_uom_id = fields.Many2one('uom.uom', 'Product Unit of Measure',
                                     track_visibility='onchange')
    product_qty = fields.Float(string='Quantity', track_visibility='onchange', )
    part_number = fields.Char('Part Number')
    qty_on_bill = fields.Float(string='Qty. on bill', track_visibility='onchange', )
    qty_received = fields.Float(string='Qty Received', track_visibility='onchange', )
    qty_accepted = fields.Float(string='Qty Accepted', track_visibility='onchange', )
    qty_rejected = fields.Float(string='Qty Rejected', track_visibility='onchange', )
    qhse_qty_accepted = fields.Float(string='QHSE Qty Accepted', track_visibility='onchange', )
    qhse_qty_rejected = fields.Float(string='QHSE Qty Rejected', track_visibility='onchange', )
    expire_date = fields.Date(string="Expire Date", track_visibility='onchange',)
    note = fields.Text(string='Comments –if any-')
    sequence = fields.Integer(string="NO", compute='_compute_step_number')

    @api.constrains('qty_received', 'qty_accepted', 'qty_rejected')
    def constraint_field_qty(self):
        for rec in self:
            if float(format(rec.qty_received, ".2f")) > float(format(rec.qty_on_bill, ".2f")) or float(
                    format(rec.qty_accepted,
                           ".2f")) > float(format(
                rec.qty_on_bill, ".2f")) or float(format(rec.qty_rejected, ".2f")) > float(
                format(rec.qty_on_bill, ".2f")):
                raise UserError('The Quantity Must be less or Equal Qty. on bill')

    @api.depends('request_id.inspection_ids')
    def _compute_step_number(self):
        for index, record in enumerate(self, start=1):
            record.sequence = str(index)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    inspection_count = fields.Integer(string="Count", compute='compute_inspection_count')

    def compute_inspection_count(self):
        if self.picking_type_id.code == 'incoming' and self.purchase_id:
            self.inspection_count = self.env['material.inspection'].search_count(
                [('purchase_id', '=', self.purchase_id.id)])
        else:
            self.inspection_count = 0

    def material_inspection(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Material Inspection',
            'view_mode': 'tree,form',
            'res_model': 'material.inspection',
            'domain': [('purchase_id', '=', self.purchase_id.id)],
            'context': "{'create': False}"
        }


class MaterialRequest(models.Model):
    _inherit = "material.request"

    inspection_count = fields.Integer(string="Count", compute='compute_inspection_count')

    def compute_inspection_count(self):
        self.inspection_count = self.env['material.inspection'].search_count(
            [('material_request_id', '=', self.id), ('state', 'in', ['inspection', 'closed', 'reject'])])

    def material_inspection(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Material Inspection',
            'view_mode': 'tree,form',
            'res_model': 'material.inspection',
            'domain': [('material_request_id', '=', self.id), ('state', 'in', ['inspection', 'closed', 'reject'])],
            'context': "{'create': False}"
        }


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    inspection_count = fields.Integer(string="Count", compute='compute_inspection_count')

    def compute_inspection_count(self):
        self.inspection_count = self.env['material.inspection'].search_count(
            [('purchase_id', '=', self.id)])

    def material_inspection(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Material Inspection',
            'view_mode': 'tree,form',
            'res_model': 'material.inspection',
            'domain': [('purchase_id', '=', self.id)],
            'context': "{'create': False,'edit':False}"
        }


class StockBackorderConfirmation(models.TransientModel):
    _inherit = "stock.backorder.confirmation"

    def process_cancel_backorder(self):
        res = super(StockBackorderConfirmation, self).process_cancel_backorder()
        pickings_to_do = self.env['stock.picking']
        for line in self.backorder_confirmation_line_ids:
            if line.to_backorder is True:
                pickings_to_do |= line.picking_id
        if pickings_to_do.purchase_id.request_id:
            pickings_to_do.purchase_id.request_id.sudo().write({'state': 'delivered'})
        return res

    def process(self):
        pickings_to_do = self.env['stock.picking']
        pickings_not_to_do = self.env['stock.picking']
        inspection_line_ids = []
        for line in self.backorder_confirmation_line_ids:
            if line.to_backorder is True:
                pickings_to_do |= line.picking_id
            else:
                pickings_not_to_do |= line.picking_id
        for pick_id in pickings_not_to_do:
            moves_to_log = {}
            for move in pick_id.move_lines:
                if float_compare(move.product_uom_qty,
                                 move.quantity,
                                 precision_rounding=move.product_uom.rounding) > 0:
                    moves_to_log[move] = (move.quantity, move.product_uom_qty)
            pick_id._log_less_quantities_than_expected(moves_to_log)
        pickings_to_validate = self.env.context.get('button_validate_picking_ids')
        if pickings_to_validate:
            pickings_to_validate = self.env['stock.picking'].browse(pickings_to_validate).with_context(
                skip_backorder=True)
            if pickings_not_to_do:
                pickings_to_validate = pickings_to_validate.with_context(
                    picking_ids_not_to_backorder=pickings_not_to_do.ids)
            if pickings_to_do:
                for rec in pickings_to_do.move_ids_without_package:
                    if rec.quantity < rec.product_uom_qty:
                        if rec.product_tmpl_id.type != 'service' and rec.product_id.product_tmpl_id.id:
                            inspection_line_ids.append(
                                (0, 0,
                                 {'product_id': rec.product_id.product_tmpl_id.id,
                                  'product_uom_id': rec.product_uom.id,
                                  'qty_on_bill': rec.product_uom_qty - rec.quantity}))
            temp = pickings_to_validate.button_validate()

            #########################inspection materail code####################################################
            if pickings_to_do.purchase_id and not (
                    pickings_to_do.purchase_id.company_id.id != pickings_to_do.purchase_id.request_id.company_id.id and pickings_to_do.purchase_id.request_id.purchase_type == 'overseas'):
                env = self.env(user=1)
                if pickings_to_do and (
                        not pickings_to_do.purchase_id.ore_purchased) and pickings_to_do.picking_type_id.code == 'incoming':
                    if inspection_line_ids:
                        res = env['material.inspection'].create(
                            {'vendor_id': pickings_to_do.partner_id.id,
                             'inspection_ids': inspection_line_ids,
                             'backorder_picking_id': pickings_to_do.id,
                             'po_number': pickings_to_do.purchase_id.name,
                             'purchase_id': pickings_to_do.purchase_id.id,
                             'material_request_id': pickings_to_do.purchase_id.request_id.id,
                             })
            ##########################################################################################################
            return temp
        return True
