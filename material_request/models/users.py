# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError

class ResPartner(models.Model):
    _inherit = "res.partner"

    max_grade = fields.Float(
        string="Max Grade for 0 Transportatin Cost (0)",
        digits="Discount",
        tracking=True,
    )
