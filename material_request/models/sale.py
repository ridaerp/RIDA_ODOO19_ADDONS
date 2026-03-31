from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round
import logging



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    date_planned = fields.Datetime('Planned Date')
    request_line_id = fields.Many2one('material.request.line', 'requisition', ondelete='set null', index=True,
                                      readonly=True)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    request_id = fields.Char(string="Material Request")
    mr_request_id = fields.Many2one("material.request",string="Material Request")
    
    mr_request_ids = fields.Many2many(
        'material.request',  # Related model
        'material_request_sale_order_rel',  # Relation table name
        'so_id',  # Column for this model
        'mr_id',  # Column for related model
        string='Material Requests'
    )

    def _prepare_purchase_order_data(self, company, company_partner):
        res = super(SaleOrder, self)._prepare_purchase_order_data(company, company_partner)

        """ Generate purchase order values, from the SO (self)
            :param company_partner : the partner representing the company of the SO
            :rtype company_partner : res.partner record
            :param company : the company in which the PO line will be created
            :rtype company : res.company record
        """
        original_po = self.env['purchase.order'].search([('name', '=', self.origin)], limit=1)
        # supplier_name = original_po.partner_id if original_po else ''

        supplier_name = original_po.partner_id if original_po else False


        self.ensure_one()
        # find location and warehouse, pick warehouse from company object
        warehouse = company.warehouse_id and company.warehouse_id.company_id.id == company.id and company.warehouse_id or False
        if not warehouse:
            raise UserError(_('Configure correct warehouse for company(%s) from Menu: Settings/Users/Companies', company.name))
        picking_type_id = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'), ('warehouse_id', '=', warehouse.id)
        ], limit=1)
        if not picking_type_id:
            intercompany_uid = company.intercompany_user_id.id
            picking_type_id = self.env['purchase.order'].with_user(intercompany_uid)._default_picking_type()
        return {
            'name': self.env['ir.sequence'].sudo().next_by_code('purchase.order'),
            'origin': self.name,
            'request_id': self.mr_request_id.id,
            'request_ids': self.mr_request_ids,
            'partner_id': company_partner.id,
            'picking_type_id': picking_type_id.id,
            'date_order': self.date_order,
            'company_id': company.id,
            'fiscal_position_id': self.env['account.fiscal.position']._get_fiscal_position(company_partner).id,
            'payment_term_id': company_partner.property_supplier_payment_term_id.id,
            'auto_generated': True,
            'auto_sale_order_id': self.id,
            'partner_ref': self.name,
            'currency_id': self.currency_id.id,
            'order_line': [],
            'po_overeas_ref':self.origin,
            'supplier_overseas': supplier_name.id if supplier_name else False,
        }

