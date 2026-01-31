from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError

class LogisticPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # c = fields.Many2one(comodel_name='logistics.logistics')
    # store_external_service_management = fields.Many2one(comodel_name='purchase_custom')
    store_contract = fields.Many2one(comodel_name='change.contract')









    








