# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, time
from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
import time


class ServiceRequisition(models.Model):
    _name = 'service.requisition'
    _inherit = ['mail.thread']

    @api.model
    def _get_default_name(self):
        return self.env['ir.sequence'].next_by_code('service.requisition') or '/'

    # @api.model
    # def create(self, vals):
    #     service = super(ServiceRequisition, self).create(vals)
    #     if 'name' not in vals or vals['name'] == _('New'):
    #         vals['name'] = self.env['ir.sequence'].next_by_code('service.requisition') or _('New')
    #     return service

    name = fields.Char('Name', default=_get_default_name,
                       copy=False, readonly=True, required=True,
                       states={'done': [('readonly', True)]})
    state = fields.Selection([('draft', 'Draft'), ('cancel', 'Cancelled'), ('done', 'Done')], 'State', default='draft')
    request_id = fields.Many2one('material.request', 'Material Request')
    purchase_id = fields.Many2one('purchase.order', 'Purchase Order')
    ##############################comment by ekhlas #############################
    # sale_id = fields.Many2one('sale.order', 'Sales Order')
    user_id = fields.Many2one('res.users', 'Requested By')
    schedule_date = fields.Date('Scheduled Date')
    description = fields.Char('Description')
    line_ids = fields.One2many('service.requisition.line', 'service_id')
    company_id = fields.Many2one('res.company', 'Company')
    backorder_id = fields.Many2one('service.requisition', 'Backorder of')
    job_completion = fields.Binary('Job Completion')


    def unlink(self):
        for rec in self:
            if True:
                raise UserError("Sorry. cannot delete service entries!")

        return super(ServiceRequisition, self).unlink()

    def button_confirm(self):
        if all(line.service_qty_done == 0 for line in self.line_ids):
            raise UserError("Please add some quantity before validating!")
        if self.purchase_id:
            self.purchase_id.is_service_receipt = True
            for line in self.line_ids:
                for po_line in self.purchase_id.order_line:
                    if line.service_qty_done > line.product_qty:
                        raise UserError('You cannot receive service amount more than requested!!')
                    if line.line_id.id == po_line.id:
                        # po_line.service_qty_done = line.service_qty_done
                        po_line.qty_received = po_line.qty_received + line.service_qty_done


        ##########################comment by ekhlas ###################################
        # if self.sale_id:
        #     for line in self.line_ids:
        #         if line.service_qty_done > line.product_qty:
        #             raise UserError('You cannot receive service amount more than requested!!')
        #         line.sale_line_id.qty_delivered += line.service_qty_done

        if self._check_backorder():
            return self.action_generate_backorder_wizard()
        return self.write({'state': 'done'})


    def button_cancel(self):
        for rec in self:
            rec.state = 'cancel'
            for line in rec.line_ids:
                line.line_id.qty_received -= line.service_qty_done


    def _create_service_backorder(self, pick_id):
        for pick in pick_id:
            if pick.request_id:
                requested_by = pick.request_id.requested_by
            service = {
                'purchase_id': pick.purchase_id.id or False,
                'request_id': pick.request_id.id or False,
                'user_id': pick.user_id.id or False,
                'schedule_date': pick.schedule_date,
                'company_id': pick.company_id.id,
                'backorder_id': pick.id,  # check if requested by or created by
            }
            service_picking = pick.create(service)
            service_orderline = pick.line_ids.filtered(
                lambda r: r.product_qty > r.service_qty_done).create_service_backorder_lines(service_picking)

    def action_generate_backorder_wizard(self):
        view = self.env.ref('procurement.view_backorder_confirmation')
        wiz = self.env['service.backorder.confirmation'].create({'pick_ids': [(4, p.id) for p in self]})
        return {
            'name': _('Create Backorder?'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'service.backorder.confirmation',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': wiz.id,
            'context': self.env.context,
        }

    def _check_backorder(self):
        quantity_todo = {}
        quantity_done = {}
        for move in self.mapped('line_ids'):
            quantity_todo.setdefault(move.product_id.id, 0)
            quantity_done.setdefault(move.product_id.id, 0)
            quantity_todo[move.product_id.id] += move.product_qty
            quantity_done[move.product_id.id] += move.service_qty_done
        return any(quantity_done[x] < quantity_todo.get(x, 0) for x in quantity_done)

    def button_reset(self):
        if not self.purchase_id.state == 'purchase':
            raise UserError(_("Related purchase order should be confirmed to set this record to draft."))
        self.purchase_id.is_service_receipt = False
        return self.write({'state': 'draft'})

    # @api.model
    # def create(self, vals):
    #     service = super(ServiceRequisition, self).create(vals)
    #     if vals.get('name', 'New') == 'New':
    #         vals['name'] = self.env['ir.sequence'].next_by_code('service.requisition') or '/'
    #     return service


class ServiceRequisition(models.Model):
    _name = "service.requisition.line"

    service_id = fields.Many2one('service.requisition')
    product_id = fields.Many2one('product.product', 'Proudct')
    name = fields.Char('Description')
    product_uom_id = fields.Many2one('uom.uom', 'Uom')
    product_qty = fields.Float('Ordered Qty', digits=(16, 4))
    service_qty_done = fields.Float('Done', digits=(16, 4))
    company_id = fields.Many2one('res.company', 'Company')
    line_id = fields.Many2one('purchase.order.line')
    sale_line_id = fields.Many2one('sale.order.line')

    def create_service_backorder_lines(self, service):
        moves = self
        done = self.browse()
        for line in self:
            if line.product_uom_id:
                uom = line.product_uom_id
            qty = line.product_qty - line.service_qty_done
            template = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_qty': qty,
                'product_uom_id': uom.id or False,
                'service_id': service.id,
                'company_id': service.company_id.id,
                'line_id': line.line_id.id,
            }
            done += moves.create(template)
        return done


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    service_delivery = fields.Boolean('Service Delivered')
    item_type = fields.Selection([('material', 'Material'), ('service', 'Service')], 'Item Type', readonly=False)
    service_count = fields.Integer(compute="compute_service_count")
    is_service_receipt = fields.Boolean('Done')


    def compute_service_count(self):
        self.service_count = self.env['service.requisition'].search_count([('purchase_id', '=', self.id)])

 