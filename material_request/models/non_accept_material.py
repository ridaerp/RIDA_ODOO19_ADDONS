# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import float_compare


class NonAcceptMaterial(models.Model):
    _name = 'nonaccept.material'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_default_name(self):
        return self.env['ir.sequence'].next_by_code('nonaccept.material')

    @api.model
    def create(self, vals):

        seq = self.env['ir.sequence'].next_by_code('non_accept_material.sequence') or "/"
        vals['name'] = seq

        request = super(NonAcceptMaterial, self).create(vals)
        return request

    name = fields.Char('Reference', default=lambda self: _('New'), copy=False, readonly=True, required=True)
    state = fields.Selection(string='Status', default='draft', selection=[('draft', 'Draft'), (
        'wharehouse_manager_approval', 'Warehouse Manager Approval'), ('user_department_manager_approval',
                                                                       'User Department Manager Approval'), (
                                                                              'supply_chain_manager_approval',
                                                                              'Supply Chain Manager Approval')])
    operation_type = fields.Selection(string='Operation Type',
                                      selection=[('scrap', 'Scrap'), ('return', 'Return'), ('repair', 'Repair')])
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    origin = fields.Char(string='Source Document')
    purchase_id = fields.Many2one('purchase.order', related='picking_id.purchase_id', string='Purchase Order',
                                  # domain="[ ('state', '=','purchase'),('company_id', '=','company_id')]"
                                  )
    product_id = fields.Many2one(
        'product.product', 'Product',
        # domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        domain=lambda self: [('product_id', 'in', self.env.ref('stock.group_stock_user').id)], check_company=True)

    vendor_id = fields.Many2one('res.partner', 'Vendor', check_company=True)
    picking_id = fields.Many2one('stock.picking', 'Picking', states={'done': [('readonly', True)]}, check_company=True,
                                 required=True)
    location_id = fields.Many2one(
        'stock.location', 'Stock Location', domain="[ ('company_id', 'in', [company_id, False])]", required=True,
        check_company=True)
    nonaccept_qty = fields.Float('Quantity', default=1.0, required=True)
    # order_line = fields.Many2many(related='purchase_id.picking_ids', string='Order Lines',
    #                              #states={'cancel': [('readonly', True)]},attrs={'readonly': [('state', '!=', ['draft', 'running'])]}, copy=True, auto_join=True
    #                              )
    order_line = fields.One2many(related='purchase_id.order_line', string='Order Lines', readonly=False)
                                 # states={'cancel': [('readonly', True)]},attrs={'readonly': [('state', '!=', ['draft', 'running'])]}, copy=True, auto_join=True


    department_id = fields.Many2one('hr.department', string='Department',
                                    # default=lambda self: self._get_default_department()
                                    )
    inspect_date = fields.Date('Date Of Inspection', track_visibility='onchange')
    click = fields.Boolean(string='Check', default=False)
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", )
    order_line_ids = []

    @api.onchange('purchase_id')
    def onchange_purchase_id(self):
        # record = self.env[active_model].browse(active_id)
        # raise UserError(str(self._context))
        if self.purchase_id:
            self.vendor_id = self.purchase_id.partner_id
        products = self.env['purchase.order'].search([('id', '=', self.purchase_id.id)]).order_line
        product = []
        for p in products:
            if p.qty_received > 0:
                product.append(p.product_id.id)
                self.order_line_ids.append(p)
        # return {'domain':{'product_id':[('id', 'in', product)]}}  
        return {'domain': {'product_id': [('id', 'in', product)], 'order_line': [('id', 'in', self.order_line_ids)]}}

        # @api.onchange('product_id')

    # def onchange_product_id(self):
    #     print("ttttttttttttttttttttt",self.order_line_ids)
    #     if self.product_id:
    #         location=self.env['purchase.order.line'].search([('id','=',self.order_line_ids[0].id),('product_id','=',self.product_id.id)])

    #         self.location_id=location.location_dest_id

    def wharehouse_manager_approval(self):
        self.write({'state': 'wharehouse_manager_approval'})

    def user_department_manager_approval(self):
        self.write({'state': 'user_department_manager_approval'})

    def supply_chain_manager_approval(self):
        for rec in self:
            if rec.operation_type == 'scrap':

                rec.button_scrap()

            elif rec.operation_type == 'repair':
                rec.button_repair()
            elif rec.operation_type == 'return':
                rec.button_return_to_supplier()

        self.write({'state': 'supply_chain_manager_approval'})

    '''def do_scrap(self):
        # self._check_company()
        for scrap in self:
            scrap.name = self.env['ir.sequence'].next_by_code('stock.scrap') or _('New')
            move = self.env['stock.move'].create(scrap._prepare_move_values())
            # master: replace context by cancel_backorder
            move.with_context(is_scrap=True)._action_done()
            scrap.write({'move_id': move.id, 'state': 'done'})
            scrap.date_done = fields.Datetime.now()
        return True
        '''

    def button_scrap(self):
        self.ensure_one()
        # self.do_scrap()
        self.click = True
        view = self.env.ref('stock.stock_scrap_form_view')
        for line in self.order_line:
            scrap_id = self.env['stock.scrap'].create(
                {'product_id': line.product_id.id,
                 'origin': self.purchase_id.name,
                 'product_uom_id': '1',
                 'company_id': self.company_id.id
                 })
            # products = self.env['product.product']
            # for move in self.purchase_id.order_line:
            #     if move.state not in ('draft', 'cancel') and move.product_id.type in ('product', 'consu'):
            #         products |= move.product_id
            return {
                'name': _('Scrap'),
                'view_mode': 'form',
                'res_model': 'stock.scrap',
                'view_id': view.id,
                # 'views': [(view.id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': scrap_id.id,
                'product_id': line.product_id,
            }

    def action_see_move_scrap(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_stock_scrap")
        # scrap = self.env['stock.scrap'].search([('origin', '=', self.purchase_id.name)])
        # scrap = self.env['stock.scrap'].search([('picking_id', '=', self.id)])
        action['domain'] = [('origin', '=', self.purchase_id.name)]
        action['context'] = dict(self._context, create=False)
        return action

    def button_repair(self):
        return

    def button_return_to_supplier(self):
        return


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    nonaccept_qty = fields.Float('Non Accepting Quantity', default=1.0, required=True)
