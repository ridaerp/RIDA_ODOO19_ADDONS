from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError




#################################ekhlas code ##############################
############################add new form contract #########################

# class PurchaseContract(models.Model):
#     _name= "purchase.contract"
#     _inherit = "purchase.requisition"
#     request_id = fields.Many2one('material.request', 'Material Request')
#     line_ids = fields.One2many('purchase.contract.line', 'requisition_id', string='Products to Purchase', states={'done': [('readonly', True)]}, copy=True)


# class PurchaseContractLine(models.Model):
#     _name = "purchase.contract.line"
#     _inherit= "purchase.requisition.line"
#     _description = "Purchase Requisition Line"

#     requisition_id = fields.Many2one('purchase.contract', required=True, string='Purchase Contract', ondelete='cascade')
#     supplier_info_ids = fields.One2many('product.supplierinfo', 'purchase_contract_line_id')




class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    request_id = fields.Many2one('material.request', 'Material Request')
    request_ids = fields.Many2many(
        'material.request',  # Related model
        'material_request_purchase_req_rel',  # Relation table name
        'po_id',  # Column for this model
        'mr_id',  # Column for related model
        string='Material Requests'
    )
    item_type = fields.Selection([('material', 'Material'), ('service', 'Service')], default="material", string='Item Type', required=True)
    commercial_justification = fields.Text(string='Commercial justification')
    tech_specification = fields.Text(string='Technical justification')
    scope_of_work = fields.Text(string='Scope of work')
    scope_attatch = fields.Binary(string='Attachment')
    tech_comments = fields.Text(string='Comments')
    commercial_comments = fields.Text(string='Comments')
    purchase_type = fields.Selection(
        [('local', 'Local Payment'), ('overseas', 'Overseas Payment')],
        string="Purchase Payment",
        default='local'
    )
    def transfer_data(self):
        """Transfers Many2one field data to Many2many field for all records."""
        records = self.sudo().search([])  # Fetch all records of the model
        for record in records:
            if record.sudo().request_id:
                record.sudo().request_ids = [(4, record.request_id.id)]


    # picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type', required=True, default=_get_picking_in, domain="['|',('warehouse_id', '=', False), ('warehouse_id.company_id', '=', company_id)]")


    # ############################the function replace the super to set contract from MR company
    # ##########################################ekhlas code ####################################

    # def _get_picking_in(self):
    #     super(PurchaseRequisition, self)._get_picking_in()
    #     pick_in = self.env.ref('stock.picking_type_in', raise_if_not_found=False)
    #     company = self.env.company
    #     if not pick_in or not pick_in.sudo().active or pick_in.sudo().warehouse_id.company_id.id != request_id.company.id:
    #         pick_in = self.env['stock.picking.type'].search(
    #         [('warehouse_id.company_id', '=', self.request_id.company_id.id), ('code', '=', 'incoming')],
    #         limit=1,)
    #     else:
    #         pick_in = self.env['stock.picking.type'].search([('warehouse_id.company_id', '=', company.id), ('code', '=', 'incoming')],
    #             limit=1,)
    #     return pick_in

    # PURCHASE_REQUISITION_STATES = [
    #     ('draft', 'Draft'),
    #     ('prm', 'Waiting for Procurement Manager Approval'),
    #     ('ongoing', 'Ongoing'),
    #     ('in_progress', 'Waiting for Supply chain Manager Approval'),
    #     ('open', 'Bid Selection'),
    #     ('done', 'Closed'),
    #     ('reject', 'Rejected'),
    #     ('cancel', 'Cancelled')
    # ]
    # state = fields.Selection(PURCHASE_REQUISITION_STATES,
    #                          'Status', track_visibility='onchange', required=True,  
    #                          copy=False, default='draft')
    # state_blanket_order = fields.Selection(PURCHASE_REQUISITION_STATES, compute='_set_state')

    # @api.depends('state')
    # def _set_state(self):
    #     self.state_blanket_order = self.state

    # def action_to_prm(self):
    #     self.state = 'prm'