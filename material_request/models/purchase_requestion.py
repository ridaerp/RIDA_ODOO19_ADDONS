from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError




#################################ekhlas code ##############################
############################add new form contract #########################


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