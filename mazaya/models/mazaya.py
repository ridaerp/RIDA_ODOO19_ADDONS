# -*- coding: utf-8 -*-
from email.policy import default
from odoo import models, fields, api, _
from odoo.exceptions import   UserError


class Mazaya(models.Model):
    _name = 'rida.mazaya'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = ''

    name = fields.Char(string='Mazaya Name' ,required=True)
    based_on = fields.Selection(string='Based On', selection=[('basic', 'Basic'), ('gross', 'Gross')],required=True)
    start_date = fields.Date(string='Start Date' ,required=True)
    end_date = fields.Date(string='End Date',required=True)
    grades = fields.Many2many('hr.grade.configuration', string='Allowed Grades',required=True)
    company = fields.Many2one(comodel_name='res.company', string='Company' , required=True, index=True)
    mazaya_lines = fields.One2many(comodel_name='rida.mazaya.line', inverse_name='mazaya_id' ,string='Mazaya', copy=True)
    state = fields.Selection(string='Status', selection=[('draft', 'Draft'),('waiting', 'To Approved'),('approved', 'Approved'), ('cancel', 'Cancelled')], default='draft')
    currency_id = fields.Many2one("res.currency",required=True,string="Currency")
    active = fields.Boolean(string='Active', default= True)
   
    def unlink(self):
        for rec in self:
            if not rec.state == "draft":
                raise UserError("Only Draft Records Can Be Deleted")
            return super(Mazaya, self).unlink()

    
    @api.depends('start_date', 'end_date')
    def expiration_date(self):
        for rec in self:
            today = fields.Date.today()
            if today >= rec.start_date and today <= rec.end_date and rec.state == 'approved':
                rec.active = False 
    

    def submit(self):  
        mazaya = self.search([('company', '=', self.company.id),('currency_id', '=', self.currency_id.id),('state', '=', 'approved')])
        if mazaya:
                raise UserError(_("This Company Already has Mazaya"))
        else:
            self.write({                
            'state': 'waiting'})
        

    def approve(self):  
        self.write({    
        'state': 'approved'})  


    def reject(self):  
        self.write({    
        'state': 'cancel'})  

    def set_to_draft(self):  
        self.write({                
        'state': 'draft'})


