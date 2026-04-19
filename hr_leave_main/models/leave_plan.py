from odoo import fields , api , models , _
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

class hrLeavePlan(models.Model):
    _name = 'hr.leave.plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Leave Plan'

    def action_approve(self):
        for rec in self:
            rec.state = 'approve'

    def generate_plan(self):
        for rec in self:
            for employee in self.env['hr.employee'].search([('department_id','=',rec.department_id.id)]):
                vals = {
                    'employee_id':employee.id,
                    'plan_id':rec.id,
                }
                self.env['hr.leave.plan.line'].create(vals)

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    name  = fields.Char(string='Name')
    department_id = fields.Many2one(comodel_name='hr.department', string='Department')
    company_id=fields.Many2one("res.company",readonly=True,default=lambda self: self.env.user.company_id)
    line_ids = fields.One2many(comodel_name='hr.leave.plan.line', inverse_name='plan_id', string='Lines')
    state  = fields.Selection([
        ('draft', 'Draft'),
        ('approve','Approved'),
    ], string='Status', default = 'draft')

    def unlink(self):
        for rec in self:
            if not rec.state == "draft":
                raise UserError("Only Draft Records Can Be Deleted")
            return super(hrLeavePlan, self).unlink()
    
    
class hrLeavePlanLine(models.Model):
    _name = 'hr.leave.plan.line'
    _description = 'Leave Plan Line'
    _rec_name = 'employee_id'
    
    def action_approve(self):
        for rec in self:
            rec.state = 'approve'

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee')
    date_from = fields.Date(string='From')
    date_to = fields.Date(string='To')
    plan_id = fields.Many2one(comodel_name='hr.leave.plan', string='Leave Plan')
    company_id = fields.Many2one("res.company", string="Company", related="employee_id.company_id", store=True,readonly=True)
    state  = fields.Selection([
        ('draft', 'Draft'),
        ('approve','Approvd'),
    ], string='Status', default = 'draft')

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def unlink(self):
        for rec in self:
            if not rec.state == "draft":
                raise UserError("Only Draft Records Can Be Deleted")
            return super(hrLeavePlanLine, self).unlink()