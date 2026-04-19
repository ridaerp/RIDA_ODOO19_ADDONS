# -*- coding: utf-8 -*-

from email.policy import default
from odoo import models, fields, api
import time
from datetime import datetime, timedelta
from dateutil import relativedelta






class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	overtime_account_id = fields.Many2one('account.account',related='company_id.overtime_account_id', string='Overtime Account',store=True, readonly=False)
	tax_account_id = fields.Many2one('account.account',related='company_id.tax_account_id', string='Tax Account',store=True, readonly=False)
	net_overtime_account_id = fields.Many2one('account.account',related='company_id.net_overtime_account_id', string='Net Overtime Account',store=True, readonly=False)

