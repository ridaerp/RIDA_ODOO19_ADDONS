# -*- coding: utf-8 -*-
from odoo import fields , api , models , _
import datetime
from dateutil.relativedelta import relativedelta

class publick_holidays(models.Model):
    _name = 'hr.public.holidays'
    _description = 'Public Holidays'

    name = fields.Char("Name", required=True)
    date_from = fields.Date("Date From", required=True)
    date_to = fields.Date("Date To", required=True)
    days = fields.Float("# of Days", compute="_get_days", store=True)
    company_id=fields.Many2one("res.company",readonly=True,default=lambda self: self.env.user.company_id)

    @api.depends('date_from', 'date_to')
    def _get_days(self):
        from_dt = fields.Datetime.from_string(self.date_from)
        to_dt = fields.Datetime.from_string(self.date_to)
        if from_dt and to_dt:
            time_delta = to_dt - from_dt
            self.days = time_delta.days + 1
