# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta
from odoo import models, fields, api
from odoo.exceptions import   UserError


class HrLoaneLine(models.Model):
    _name = 'hr.loan.config.line'

   
    line_id = fields.Many2one(comodel_name='hr.loan.config', string='') 
    date = fields.Date("Date")
    amount = fields.Float("Amount")
    number = fields.Integer("Number")
    join_date_comparison = fields.Selection([('number', 'Number Of Month'),('date', 'Date')])
    interval_base = fields.Selection([('year', 'Year'), ('month', 'Month')])
    sign = fields.Selection([('>','>'),('<','<'),('==','='),('>=','>='),('<=','<=')])


    
    @api.constrains('sign')
    def _check_(self):
        for rec in self:
            if rec.sign == False :
                raise UserError("Please Enter Sign In Formula")
