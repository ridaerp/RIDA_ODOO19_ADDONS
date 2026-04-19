# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class Move(models.Model):
    _inherit = "account.move.line"

 
    custody_id = fields.One2many(comodel_name='account.custody', inverse_name='custody_id', string='')

class AccountCustody(models.Model):
    _inherit = 'account.custody'

    custody_id = fields.Many2one(
        comodel_name='account.move.line',
        string='custody',
      )

