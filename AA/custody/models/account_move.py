# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class Move(models.Model):
    _inherit = "account.move"

    custody_id = fields.Many2one('account.custody')