# -*- coding: utf-8 -*-
import time
from datetime import datetime
from odoo import fields, models, api, _
from odoo.exceptions import  UserError, ValidationError
from odoo import exceptions


class SalaryAdvancePayment(models.Model):
    _name = "salary.advance"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'Adv/')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, help="Employee")
    employee_code = fields.Char(string='Employee Code',related="employee_id.emp_code" )
    rida_employee_type = fields.Selection(related="employee_id.rida_employee_type")
    date = fields.Date(string='Date', required=True, default=lambda self: fields.Date.today(), help="Submit date")
    reason = fields.Text(string='Reason', help="Reason")
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 related="employee_id.company_id")
    advance = fields.Float(string='Advance', required=True)
    payment_method = fields.Many2one('account.journal', string='Payment Method')
    exceed_condition = fields.Boolean(string='Exceed Than Maximum',
                                      help="The Advance is greater than the maximum percentage in salary structure")
    department = fields.Many2one('hr.department', string='Department')
    state = fields.Selection([('draft', 'Draft'),
                              ('hr_manager', 'HR payroll Manager Approval'),
                              ('ccso', 'COO Approval'),
                              ('site_manager', 'Operation Director  Approval'),
                              ('approve', 'Approved'),
                              ('finance', 'Finance Approval'),
                              ('paid', 'Paid'),
                              ('cancel', 'Cancelled'),
                              ('reject', 'Rejected')], string='Status', default='draft', track_visibility='onchange')

    employee_contract_id = fields.Many2one('hr.version', string='Contract')
    last_salary = fields.Monetary(compute="_compute_last_salary",readonly=True, store=True )



    ######################added by ekhlas code #####################################
    requested_by = fields.Many2one('res.users', 'Requested by', track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True, readonly=True)



    user_type = fields.Selection(string='User type', selection=[('hq', 'HQ Staff'),
     ('site', 'Site Staff'),('fleet','Fleet')],required=False,compute="get_user_type")


    def get_requested_by(self):
        user = self.env.user.id
        return user



    def get_user_type(self):
        for rec in self:
            rec.user_type=rec.requested_by.user_type




    ######################END  OF ekhlas code #####################################



    @api.depends('employee_id')
    def _compute_last_salary(self):
        for record in self:
            last_payslip = record.env['hr.payslip'].search([('employee_id', '=', record.employee_id.id),('state','=','done')],limit=1,order='date_from desc')
            record.last_salary = last_payslip.net_wage

    # Smart Button for last net salary
    def smart_count_of_last_salary(self):
        return {
            'name': ('Net Salary'),
            'view_type': 'form',
            'view_mode': 'list',
            'res_model': 'hr.payslip',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': "{'create': False}",
            'domain': [('employee_id','=', self.employee_id.id),('state','=','done')],
            'limit':1,
            'order':'date_from desc'
        }
        
        
        

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('salary.advance.seq') or ' '
        return super(SalaryAdvancePayment, self).create(vals)



    @api.onchange('employee_id')
    def onchange_employee_id(self):
        # self.account_id = False
        department_id = self.employee_id.department_id.id
        domain = [('employee_id', '=', self.employee_id.id)]
        if self.employee_id:
            self.employee_contract_id = self.sudo().employee_id.version_id
        return {'value': {'department': department_id}, 'domain': {
            'employee_contract_id': domain,
        }}

    @api.onchange('company_id')
    def onchange_company_id(self):
        company = self.company_id
        domain = [('company_id.id', '=', company.id)]
        result = {
            'domain': {
                'journal': domain,
            },

        }
        return result

    def update_activities(self):
        for rec in self:
            users = []
            # rec.activity_unlink(['hr_salary_advance.mail_act_approval'])
            if rec.state not in ['draft','hr_manager','ccso','approve','finance','paid','reject']:
                continue
            message = ""
            if rec.state == 'hr_manager':
                users = self.env.ref('base_rida.rida_hr_manager_notify').user_ids
                message = "Approve" 
            elif rec.state == 'reject':
                users = [self.create_uid]
                message = "Cancelled"
            for user in users:
                self.activity_schedule('hr_salary_advance.mail_act_approval', user_id=user.id, note=message)
        
    def action_submit(self):
        for rec in self:
            adv = rec.advance
            amt = rec.employee_id.payroll_wage

            # Comment by ekhlas 
            #if adv > amt and not rec.exceed_condition:
            #     raise UserError(amt)
            #     # raise UserError('Advance amount is greater than allowed amount')

            if not rec.advance:
                raise UserError('You must Enter the Salary Advance amount')
            rec.state = 'hr_officer'
            rec.update_activities()
            
    def action_hr_officer(self):
        """This Approve the employee salary advance request.
                   """
        emp_obj = self.env['hr.employee']
        # address = emp_obj.browse([self.employee_id.id]).address_home_id
        # if not address.id:
        #     raise except_orm('Error!', 'Define home address for the employee. i.e address under private information of the employee.')
        # Extract year from current advance's date
        current_year = datetime.strptime(str(self.date), '%Y-%m-%d').date().year

        # Count the number of PAID advances in the same year for this employee (excluding current record)
        count = self.search_count([
            ('employee_id', '=', self.employee_id.id),
            ('id', '!=', self.id),
            ('state', '=', 'paid'),
            ('date', '>=', f'{current_year}-01-01'),
            ('date', '<=', f'{current_year}-12-31'),
        ])

        # Raise error if the employee already has 3 or more paid advances this year
        if count >= 3:
            raise UserError('An employee cannot request more than 3 salary advances in a year.')

        adv = self.advance
        amt = self.employee_id.payroll_wage

        if adv > amt and not self.exceed_condition:
            raise UserError('Advance amount is greater than allowed amount')

        if not self.advance:
            raise UserError('You must Enter the Salary Advance amount')
        payslip_obj = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id),
                                                     ('state', '=', 'done'), ('date_from', '<=', self.date),
                                                     ('date_to', '>=', self.date)])
        if payslip_obj:
            raise UserError("This month salary already calculated")

        current_month = datetime.strptime(str(self.date), '%Y-%m-%d').date().month

        for slip in self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id)]):
            slip_moth = datetime.strptime(str(slip.date_from), '%Y-%m-%d').date().month
            if current_month == slip_moth + 1:
                slip_day = datetime.strptime(str(slip.date_from), '%Y-%m-%d').date().day
                current_day = datetime.strptime(str(self.date), '%Y-%m-%d').date().day
        self.state = 'hr_manager'
        # self.update_activities()



    def action_hr_manager(self):
        for rec in self:
            rec.state = 'finance'

  


    def action_site_manager(self):
        for rec in self:
            rec.state = 'accountant'
            # rec.update_activities()
              
 
    def action_fainance(self):
        for rec in self:
            rec.state = 'internal_audit'
            # rec.update_activities()

    def action_internal_audit(self):
        for rec in self:
            if rec.rida_employee_type=='site':
                rec.state='site_manager'
            else:
                rec.state='ccso'
            # rec.update_activities()
            

    def action_ccso(self):
        for rec in self:
            rec.state = 'accountant'
            # rec.update_activities()
            
    def reject_ccso(self):
        for rec in self:
            rec.state = 'internal_audit'


    def reject_site(self):
        for rec in self:
            rec.state = 'internal_audit'

    def reject_internal_audit(self):
        for rec in self:
            rec.state = 'finance'

    def reject_hr_manager(self):
        for rec in self:
            rec.state = 'hr_officer'



    def reject_finance_manager(self):
        for rec in self:
            rec.state = 'hr_manager'

    def reject_account(self):
        for rec in self:
            if rec.rida_employee_type=='site':
                rec.state='site_manager'
            else:
                rec.state = "ccso"


    def reject(self):
        for rec in self:
            rec.state = 'reject'



    def cancel(self):
        for rec in self:
            rec.state = 'cancel'
            if rec.state in ['approve','accountant'] and rec.move_id:
                po = self.env['account.payment'].search([('ref', '=', rec.name)])
                po.write({'state': 'cancel'})

    def set_draft(self):
        for rec in self:
            rec.state = 'draft'


    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError("You cannot delete this Request. Only DRAFT Requests can be deleted.")
            return super(SalaryAdvancePayment, self).unlink()

