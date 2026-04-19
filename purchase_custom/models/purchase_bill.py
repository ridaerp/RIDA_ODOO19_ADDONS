from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime


class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    pyment_req_id = fields.Many2one('payment.request')

    risk_cost = fields.Monetary(string='Risk cost')

    # Restore stored behavior safely
    purchase_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        store=True  # this ensures Odoo ORM treats it as stored
    )