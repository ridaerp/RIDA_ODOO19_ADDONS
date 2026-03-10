# -*- coding: utf-8 -*-
import datetime
from email.policy import default
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil import relativedelta
from datetime import datetime as dt
from datetime import datetime, timedelta


class HRGradeLine(models.Model):
    _name='hr.grade.line'
    _description = 'Grade Line'
    
    
    name  = fields.Char(string='Name' , required=True, )
    type  = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage','Percentage (Basic)'),
    ], string='Type', required=True, default='fixed')
    percentage = fields.Float(string='Percentage (%)')
    amount = fields.Float(string='Amount')
    code  = fields.Char(string='Salary Rule Code', required=True, )
    grade_id = fields.Many2one('hr.grade.configuration', string="Grade")
    contract_id  = fields.Many2one(comodel_name='hr.version', string='Contract')
    benifit_id = fields.Many2one('hr.grade.benefits', string="Benifit")

class HRGradeConfiguration(models.Model):
    _name='hr.grade.configuration'
    _description = 'Grade'

    def get_benifits(self):
        for rec in self:
            # rec.grade_line_id.unlink()
            for line in self.env['hr.grade.benefits'].search([('id','not in', rec.grade_line_id.mapped('benifit_id').ids)]):
                self.env['hr.grade.line'].create({
                    'name': line.name,
                    'type': line.type,
                    'code': line.code,
                    'percentage': line.percentage,
                    'amount': line.amount,
                    'grade_id': rec.id,
                    'benifit_id': line.id
                })
            rec.get_amount_perecentage()

    @api.onchange('basic','grade_line_id')
    def get_amount_perecentage(self):
        for rec in self:
            for line in rec.grade_line_id:
                if line.type == 'percentage':
                    line.amount = ((line.percentage)/100) * rec.basic
                else:
                    pass
        
    @api.constrains('sequence')
    def _check_sequence(self):
        ids = self.env['hr.grade.configuration'].search([('id','!=',self.id),('sequence','=',self.sequence)])
        if len(ids)>0:
            raise UserError(_('Sequence Should Be Unique!'))

    name = fields.Char(string="Grade",required=True)
    sequence  = fields.Integer(string='Sequence',required=True , copy=False)
    grade_line_id = fields.One2many(comodel_name='hr.grade.line', inverse_name='grade_id', string='Benefits')
    basic = fields.Float(string='Basic')
    job_ids  = fields.Many2many(comodel_name='hr.job', string='Job Positions')
    band_id = fields.Many2one(comodel_name='job.band', string='Job Band')
    min = fields.Float(string='Min. Amount')
    max = fields.Float(string='Max. Amount')

class EmployeePublicInherit(models.Model):
    _inherit = 'hr.employee.public'

    basic = fields.Float(string='Net Salary')
    total_allowance = fields.Float(string='Total Allowance',)
    grade_id = fields.Many2one('hr.grade.configuration', string="Grade",)
    payroll_wage = fields.Float(string='Gross')
    min = fields.Float(string='Min. Amount',  related='grade_id.min', readonly=True,  store=True)
    max = fields.Float(string='Max. Amount',  related='grade_id.max',readonly=True,store=True)
    location = fields.Selection(string='Location', selection=[('site', 'Site'), ('administrative', 'Administrative')])
    basic_percentage = fields.Float(string='Basic Salary(%)' , default= 61.00)
    cola_percentage = fields.Float(string='Cola(%)', default= 15.00)
    housing_percentage = fields.Float(string='Housing(%)', default= 10.00)
    transportion_percentage = fields.Float(string='Transportion(%)', default= 14.00)
    wage = fields.Float(string='Take Home',)
    salary_currency = fields.Many2one("res.currency", string="Contract Currency",)
    is_worker = fields.Boolean(string='Is Worker')

class Employee(models.Model):
    _inherit = 'hr.employee'

    basic = fields.Float(string='Net Salary')
    band_id = fields.Many2one(comodel_name='job.band', string='Job Band', related='grade_id.band_id')
    grade_id = fields.Many2one('hr.grade.configuration', string="Grade", related='contract_id.grade_id')
    is_worker = fields.Boolean(string='Is Worker')
    is_section_head = fields.Boolean(string='Is Section head')
    total_allowance = fields.Float(string='Total Allowance', compute="get_total_allowance")
    grade_id = fields.Many2one('hr.grade.configuration', string="Grade", readony=True)
    grade_line_id = fields.One2many(comodel_name='hr.grade.line', inverse_name='contract_id', string='Old Benefits')
    wage = fields.Monetary(string='Take Home', compute="get_gross", store=True)
    payroll_wage = fields.Monetary(string='Gross')
    min = fields.Float(string='Min. Amount',  related='grade_id.min', readonly=True,  store=True)
    max = fields.Float(string='Max. Amount',  related='grade_id.max',readonly=True,store=True)
    location = fields.Selection(string='Location', selection=[('site', 'Site'), ('administrative', 'Administrative')])
    basic_percentage = fields.Float(string='Basic Salary(%)' , default= 61.00)
    cola_percentage = fields.Float(string='Cola(%)', default= 15.00)
    housing_percentage = fields.Float(string='Housing(%)', default= 10.00)
    transportion_percentage = fields.Float(string='Transportion(%)', default= 14.00)
    basic_salary = fields.Float(string='Basic Salary' , readonly=True,compute="compute_salary_amount" )
    cola = fields.Float(string='Cola', readonly=True,compute="compute_salary_amount" )
    housing = fields.Float(string='Housing' ,readonly=True,compute="compute_salary_amount" )
    transportion = fields.Float(string='Transportion', readonly=True,compute="compute_salary_amount" )
    salary_currency = fields.Many2one("res.currency",required=True,string="Contract Currency",default=lambda self: self.env.company.currency_id)
    contract_date_start = fields.Date(readonly=False, related="version_id.contract_date_start", inherited=True, groups="base.group_user")
    wage_type = fields.Selection(readonly=False, related="version_id.wage_type", inherited=True, groups="base.group_user")

    @api.onchange('payroll_wage','basic_percentage','cola_percentage','housing_percentage','transportion_percentage')
    @api.depends('payroll_wage','basic_percentage','cola_percentage','housing_percentage','transportion_percentage')
    def compute_salary_amount(self):
        for rec in self:
            rec.basic_salary = (rec.basic_percentage/100) * rec.payroll_wage
            rec.cola = (rec.cola_percentage/100) * rec.payroll_wage
            rec.housing = (rec.housing_percentage/100) * rec.payroll_wage
            rec.transportion = (rec.transportion_percentage/100) * rec.payroll_wage

    @api.onchange('basic')
    def _onchange_wage(self):
        if self.basic:
            res = {}
            for rec in self:
                if int(rec.basic) > int(rec.max):
                    res = {'warning':{
                        'title': _('Warning'),
                        'message': _('The Gross Is More Than This Grade Maximoum Amount.'),}
                    }
                
                if int(rec.basic) < int(rec.min):
                    res = {'warning':{
                        'title': _('Warning'),
                        'message': _('The Gross Is Less Than This Grade Minimoum Amount.'),}
                }
            return res
    
    @api.constrains('grade_id.job_ids','grade_id','job_id')
    def _check_job_positions(self):
        if self.grade_id and self.grade_id.job_ids:
            if self.job_id not in self.grade_id.job_ids:
                raise UserError(_("Employee Job Position is not Allowed To Take This Grade")) 
    
    @api.depends('basic','total_allowance')
    def get_gross(self):
        for rec in self:
            rec.wage =  rec.total_allowance + rec.basic
        
    @api.onchange('grade_id')
    def get_benifits(self):
        for rec in self:
            rec.basic = rec.grade_id.basic
            lines = [(5, 0, 0)]
            for line in self.grade_id.grade_line_id:
                vals = {
                    'name': line.name,
                    'type': line.type,
                    'code': line.code,
                    'percentage': line.percentage,
                    'amount': line.amount,
                    'contract_id':rec.id
                }
                lines.append((0, 0, vals))
            rec.grade_line_id = lines

    @api.onchange('basic', 'grade_line_id')
    def get_amount_perecentage(self):
        for rec in self:
            for line in rec.grade_line_id:
                if line.type == 'percentage':
                    line.amount = ((line.percentage) / 100) * rec.basic
                else:
                    pass
    
    @api.depends('grade_id','grade_line_id','grade_line_id.amount')
    def get_total_allowance(self):
        for rec in self:
            total = 0.0
            if rec.grade_id and rec.grade_line_id:
                for line in rec.grade_line_id:
                    total += line.amount
            rec.total_allowance = total 







class EmployeeVersion(models.Model):
    _inherit = 'hr.version'

    basic = fields.Float(string='Net Salary')
    band_id = fields.Many2one(comodel_name='job.band', string='Job Band')
    grade_id = fields.Many2one('hr.grade.configuration', string="Grade")
    total_allowance = fields.Float(string='Total Allowance')
    grade_id = fields.Many2one('hr.grade.configuration', string="Grade", readony=True)
    grade_line_id = fields.One2many(comodel_name='hr.grade.line', inverse_name='contract_id', string='Old Benefits')
    wage = fields.Monetary(string='Take Home', store=True)
    payroll_wage = fields.Monetary(string='Gross')
    min = fields.Float(string='Min. Amount',  readonly=True,  store=True)
    max = fields.Float(string='Max. Amount', readonly=True,store=True)
    location = fields.Selection(string='Location', selection=[('site', 'Site'), ('administrative', 'Administrative')])
    basic_percentage = fields.Float(string='Basic Salary(%)' , default= 61.00)
    cola_percentage = fields.Float(string='Cola(%)', default= 15.00)
    housing_percentage = fields.Float(string='Housing(%)', default= 10.00)
    transportion_percentage = fields.Float(string='Transportion(%)', default= 14.00)
    basic_salary = fields.Float(string='Basic Salary' , readonly=True )
    cola = fields.Float(string='Cola', readonly=True)
    housing = fields.Float(string='Housing' ,readonly=True,)
    transportion = fields.Float(string='Transportion', readonly=True, )
    salary_currency = fields.Many2one("res.currency",required=True,string="Contract Currency",default=lambda self: self.env.company.currency_id)

