# -*- coding: utf-8 -*-
from odoo import models, fields, api, _



class MazayaLine(models.Model):
    _name = 'rida.mazaya.line'


    month = fields.Selection(string='Months', selection=[('1', 'January'), ('2', 'February'),('3', 'March'), ('4', 'April'),('5', 'May'), ('6', 'June'),('7', 'July'), ('8', 'August'),('9', 'September'), ('10', 'October'),('11', 'November'), ('12', 'December')])
    cash_allow = fields.Float(string='Cash Allowance %')
    dress_allow = fields.Float(string='Dress Allowance %')
    midical_allow = fields.Float(string='Medical Allowance %')
    grant_allow = fields.Float(string='Grant %')
    new_allow = fields.Float(string='New %' ,compute='compute_allownce')
    tax_allow = fields.Float(string='Tax %')
    mazaya_id = fields.Many2one(comodel_name='rida.mazaya', string='Lines')

        
    @api.depends('cash_allow','dress_allow','midical_allow','grant_allow')
    def compute_allownce(self):
        for rec in self:
            rec.new_allow = rec.cash_allow + rec.dress_allow + rec.midical_allow + rec.grant_allow
