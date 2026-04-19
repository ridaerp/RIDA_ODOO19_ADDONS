# -*- coding: utf-8 -*-
import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil import relativedelta
from datetime import datetime as dt
from datetime import datetime, timedelta

class HRGradeBenfit(models.Model):
    _name='hr.grade.benefits'
    _description = 'Grade Benefits'
    
    @api.constrains('code')
    def _check_code(self):
        ids = self.env['hr.grade.benefits'].search([('id','!=',self.id),('code','=',self.code)])
        if len(ids)>0:
            raise UserError(_('Code Should Be Unique!'))
        
    
    name  = fields.Char(string='Name' , required=True, )
    type  = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage','Percentage'),], string='Type', required=True, default='fixed')
    code  = fields.Char(string='Salary Rule Code', required=True,)
    percentage = fields.Float(string='Percentage (%)')
    amount = fields.Float(string='Amount')



class HRSalaryBenfits(models.Model):
    _name='hr.salary.benefits'
    _description = 'Salary Benefits'

    name  = fields.Char(string='Name' , required=True, )
    type  = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage','Percentage'),
    ], string='Type', required=True, default='fixed')
    code  = fields.Char(string='Salary Rule Code', required=True,)
    percentage = fields.Float(string='Percentage (%)')
    amount = fields.Float(string='Amount')
    contract_id = fields.Many2one('hr.version', string='')
    benifit_id = fields.Many2one('hr.grade.benefits')

class Contract(models.Model):
    _inherit = 'hr.employee'

    salary_benefit_ids = fields.One2many('hr.salary.benefits', 'contract_id', string='Salary Benefits')
    basic = fields.Float(string='Basic')
    total_allowance = fields.Float(string='Total Allowance', compute="get_total_allownace", store=True)
    wage = fields.Monetary(string='Gross', compute="get_gross", store=True, required=False)
    

    def get_benifits(self):
        for rec in self:
            for line in rec.env['hr.grade.benefits'].search([('id','not in', rec.salary_benefit_ids.mapped('benifit_id').ids)]):
                rec.env['hr.salary.benefits'].create({
                    'name': line.name,
                    'type': line.type,
                    'code': line.code,
                    'percentage': line.percentage,
                    'amount': line.amount,
                    'contract_id': rec.id,
                    'benifit_id': line.id
                })
            rec.compute_amount()


    @api.onchange('salary_benefit_ids','wage','salary_benefit_ids.percentage')
    def compute_amount(self):
        for rec in self:
            for line in self.salary_benefit_ids:
                if line.type == 'percentage':
                    line.amount = (line.percentage/100) * rec.basic
                else:
                    pass

    @api.depends('salary_benefit_ids')
    def get_total_allownace(self):
        for rec in self:
            rec.total_allowance = sum(rec.salary_benefit_ids.mapped('amount'))


    @api.depends('basic','salary_benefit_ids')
    def get_gross(self):
        for rec in self:
            total_allowance = sum(rec.salary_benefit_ids.mapped('amount'))
            rec.wage =  total_allowance + rec.basic


    @api.onchange('basic', 'salary_benefit_ids')
    def get_amount_perecentage(self):
        for rec in self:
            for line in rec.salary_benefit_ids:
                if line.type == 'percentage':
                    line.amount = ((line.percentage) / 100) * rec.basic
                else:
                    pass
                    