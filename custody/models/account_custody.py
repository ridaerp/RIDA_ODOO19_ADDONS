# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import  UserError
from calendar import monthrange
import time
import math
from odoo.tools import float_round

class AccountCustody(models.Model):
    _name = 'account.custody'
    _description = "Custody"
    _inherit = ['mail.thread', 'mail.activity.mixin']


    def _default_analytic_account_id(self):
        if self.env.user.default_analytic_account_id.id:
            return self.env.user.default_analytic_account_id.id



# custody Workflow (IF user type: HQ ) from requester →line manager→ finance manager → ccso → accountant
# custody Workflow (IF user type: site ) from requester →line manager→ finance manager → site → accountant
    state = [
        ('draft', 'Draft'),
        ('lm_approval', 'Waiting For Line Manager Approval'),
        ('fin_mgr_approval', 'Waiting For Finance Manager Approval'),
        ('ccso_approval', 'Waiting For COO Approval'),
        ('internal_audit', 'Internal Audit'),
        ('site_approval', 'Waiting For Operation Director Approval'),
        ('fleet_approval', 'Waiting For Fleet Director Approval'),
        ('treasury_approval', 'Treasury Accountant Approval'),
        ('approve', 'Approved'),
        ('posted', 'Posted'),
        ('paid', 'Paid'),
        ('partially_cleared', 'Partially Cleared'),
        ('cleared', 'Cleared'),
        ('cancel',"Canceled")
    ]

    name = fields.Char("Number", required=True, index=True, default=lambda self: _('New'), copy=False)
    employee_id = fields.Many2one("hr.employee", string="Employee", default=lambda  self: self._get_employee())
    department_id = fields.Many2one('hr.department', "Department",default=lambda self: self._default_dept())
    account_id = fields.Many2one("account.account", string="Employee Account")
    journal_id = fields.Many2one("account.journal", string="Payment Journal")
    analytic_id = fields.Many2one("account.analytic.account",default=_default_analytic_account_id,string="Analytic Account")
    state = fields.Selection(state, string="State", required=True, default="draft", index=True, track_visibility='onchange')
    date_request = fields.Date("Request Date", default=lambda *a: time.strftime('%Y-%m-%d'))
    amount = fields.Float("Amount")
    amount_char = fields.Text("Amount(Character)", compute="compute_char_amount", store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id.id)
    move_id = fields.Many2one('account.move', 'Journal Entry', readonly=True)
    description = fields.Text("Description")
    company_id = fields.Many2one('res.company', string='Company', required=True,readonly=True, default=lambda self: self.env.company.id)
    clear_amount = fields.Float(copy=False, string="Cleared Amount")
    residual = fields.Float(compute="compute_residual")
    # is_line_manager = fields.Boolean(compute='compute_line_manager')
    account_move_id = fields.Many2one('account.move', string='Journal Entry', ondelete='restrict', copy=False, readonly=True)
    
    ###############added by ekhlas code
    requested_by = fields.Many2one('res.users', 'Requested by', track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True, readonly=True)

    ###############added by ekhlas code
    def get_requested_by(self):
        user = self.env.user.id
        return user

    @api.depends('name')
    def compute_line_manager(self):
        employee_line_manager = self.employee_id.line_manager_id
        user_employee = self.env.user.employee_ids[0] if self.env.user.employee_ids else False
        if not user_employee:
            return
        user_job_title = user_employee.job_id
        self.is_line_manager = user_job_title == employee_line_manager and self.state == 'lm_approval'

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.account_id = False
        if not self.employee_id or not self.employee_id.employee_partner_id:
            return
        partner = self.employee_id.employee_partner_id
        self.account_id = partner.property_account_receivable_id

    def _get_employee(self):
        if len(self.env.user.employee_ids) > 0:
            employee = self.env.user.employee_ids[0].id
            return employee or False

    @api.depends('amount', 'clear_amount')
    def compute_residual(self):
        for record in self:
            record.residual = record.amount - record.clear_amount

    def button_submit(self):
        self.state = "lm_approval" #lm_approval => fin_mgr_approval
        
    def button_cancel(self):
        self.state = "cancel"
        
    def button_lm_approve(self):
        ######################add below  by ekhlas code
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                pass

            else:
                self.ensure_one()
                line_managers = []
                today = fields.Date.today()
                line_manager = False
                try:
                    line_manager = rec.requested_by.line_manager_id
                except:
                    line_manager = False
                # comment by ekhlas
                if not line_manager or line_manager !=rec.env.user :
                    raise UserError("Sorry. Your are not authorized to approve this document!")

            rec.state = "fin_mgr_approval"
            
    def button_lm_reject(self):
        for rec in self:
            rec.state = "draft"

    
    def button_fin_mgr_approval(self):
        for rec in self:
            #comment by ekhlas code if rec.employee_id.employee_type == 'site':
            if rec.requested_by.user_type == 'site':
                rec.state = "internal_audit"
            elif rec.requested_by.user_type=='fleet':
                rec.state='fleet_approval'
            else : 
                self.state = "internal_audit"

    
    def button_fin_mgr_reject(self):
         self.state = "lm_approval"


    def button_site_approval(self):
        for rec in self:
            rec.state = "treasury_approval"
        
    def button_site_reject(self):
        for rec in self:
            rec.state = "internal_audit"


    def button_ccso_approval(self):
        for rec in self:
            rec.state = "treasury_approval"
        
    def button_ccso_reject(self):
        for rec in self:
            rec.state = "internal_audit"


    def button_fleet_approval(self):
        for rec in self:
            rec.state = "treasury_approval"
        
    def button_fleet_reject(self):
        for rec in self:
            rec.state = "fin_mgr_approval"            

    def button_audit_reject(self):
         self.state = "fin_mgr_approval"


    def activity_update(self):
        for rec in self:
            users = []
            # rec.activity_unlink(['hr_salary_advance.mail_act_approval'])
            # if rec.state not in ['draft','reject']:
            #     continue
            message = ""
            if rec.state == 'ccso_approval' and rec.requested_by.user_type=='hq':
                users = self.env.ref('base_rida.rida_group_CCSO').users
                message = "Waiting for Your Approval "
                for user in users:
                    self.activity_schedule('base_rida.mail_act_notification_approval', user_id=user.id, note=message)

            if rec.state == 'site_approval' and rec.requested_by.user_type=='site':
                users = self.env.ref('base_rida.rida_group_site_manager').users
                message = "Waiting for Your Approval "
                for user in users:
                    self.activity_schedule('base_rida.mail_act_notification_approval', user_id=user.id, note=message)

            else:
                continue



# internal audit buttons
    def action_internal_audit_sheets(self): 
        for rec in self:
            #comment by ekhlas code if rec.employee_id.employee_type == 'site':
            if rec.requested_by.user_type == 'site':
                rec.state = "site_approval"
                self.activity_update()
            else : 
                rec.state = "ccso_approval"
                self.activity_update()


    def button_treasury_approval(self):
        for rec in self:
            rec.state = "approve"
        
    def button_treasury_reject(self):
        for rec in self:
            if rec.employee_id.employee_type == 'site':
                rec.state = "site_approval"
            if rec.employee_id.employee_type == 'hq':
                self.state = "ccso_approval"
            else:
                self.state = "fleet_approval"


    def button_set_Draft(self):
        self.state = "draft"
        
    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'in_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', filter(None, map(self.TYPE2JOURNAL.get, inv_types))),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    def button_payment(self):
        return {
            'name': _('Payment'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('ref', '=', self.name)],
        }
    def button_journal_entries(self):
        return {
            'name': _('Journal Entiry'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('ref', '=', self.name)],
        }

    def button_journals(self):
        return {
            'name': _('Clearing Journals'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('custody_id', '=', self.id)],
        }

    def action_post(self):
        for record in self:
            if not record.account_id:
                raise UserError("Please select Employee Account")
            if not record.journal_id:
                raise UserError("Pleas select payment journal")
            # journal = self._default_journal()
            journal = record.journal_id
            credit_line = debit_line = []
            ctx = dict(record._context)
            for rec in record:
                amount = 0.0
    #            ctx['date'] = date_invoice
                company_currency = rec.company_id.currency_id
                if rec.currency_id != company_currency:
                    amount_currency = rec.amount
                    amount = rec.currency_id.with_context(ctx).compute(rec.amount, company_currency)
                    currency_id = rec.currency_id
                else:
                    amount_currency = False
                    currency_id = False
                    amount = rec.amount

                move = self.env['account.move'].create({
                    'journal_id': journal.id,
                    'date': rec.date_request,
                    'ref': rec.name,
                    'company_id': rec.company_id.id,
                })
                AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False)

                partner = record.employee_id.employee_partner_id
                if not partner :
                    raise UserError ("employee Partner is not defined for this employee")
                base_line = {
                    'name': rec.employee_id.name,
                    'move_id': move.id,
                    'currency_id': record.currency_id.id,
                    'partner_id': partner.id,
                }

                credit_line = dict(base_line, account_id=rec.journal_id.default_account_id.id)
                debit_line = dict(base_line, account_id=rec.account_id.id)

                diff = record.amount
                debit_line['amount_currency'] = amount_currency
                debit_line['debit'] = amount
                credit_line['amount_currency'] = -amount_currency
                credit_line['credit'] = amount
                # if self.analytic_id:
                #     credit_line['analytic_account_id'] = rec.analytic_id.id
    #                credit_line['analytic_account_id'] = rec.analytic_id.id
                AccountMoveLine.create(debit_line)
                AccountMoveLine.create(credit_line)
                move.post()
                rec.state = "paid"
                rec.move_id = move.id
                # rec.journal_id = move.id
        return True
    
    # comment by ekhlas code
    #def action_register_payment(self):
    #     for rec in self:          
    #         create_payment = {
    #             'payment_type': 'inbound',
    #             'partner_type': 'customer',
    #             'partner_id': rec.employee_id.employee_partner_id.id,
    #             'destination_account_id':rec.account_id.id,
    #             'company_id': rec.company_id.id,
    #             'amount': rec.amount,
    #             'currency_id': rec.currency_id.id,
    #             'ref': rec.name,
    #             'journal_id': rec.journal_id.id,
    #         } 
    #         po = self.env['account.payment'].create(create_payment)
    #         rec.state = "paid"
    #         return po
    


    def action_register_payment(self):
        for rec in self:          
            create_payment = {
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': rec.employee_id.employee_partner_id.id,
                'destination_account_id':rec.account_id.id,
                'company_id': rec.company_id.id,
                'amount': rec.amount,
                'currency_id': rec.currency_id.id,
                'ref': rec.name,
                'journal_id': rec.journal_id.id,

            } 
            po = self.env['account.payment'].create(create_payment)
            # po.state = "posted"
            self.account_move_id=po.move_id
            # po.move_id.state=='posted'
            self.button_action_post()
            # rec.state = "paid"
        return po
    
    def button_action_post(self):
        for record in self:
            po = self.env['account.payment'].search([('ref', '=', record.name)])
            po.action_post()
            record.state = "paid"

   
    def unlink(self):
        if self.state != 'draft':
            raise UserError("You cannot delete this Custody. Only DRAFT records can be deleted.")
        return super(AccountCustody, self).unlink()

    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('name', 'New') == 'New':
                val['name'] = self.env['ir.sequence'].next_by_code('account.custody') or 'New'
        return super(AccountCustody, self).create(vals)

    @api.model
    def _default_dept(self):
        emp = self.env.user.employee_ids
        if len(emp)<1:
            raise  UserError("This user is not linked to employee!")
        user_department_id = self.env.user.employee_ids[0].department_id.id
        if not user_department_id:
            raise UserError("The current user is not linked to a department.")
        return user_department_id

    @api.depends('amount')
    def compute_char_amount(self):
        check_amount_in_words = amount_to_text_en.amount_to_text(math.floor(self.amount), lang='en', currency='')
        check_amount_in_words = check_amount_in_words.replace(' and Zero Cent', '')  # Ugh
        decimals = self.amount % 1
        if decimals >= 10 ** -2:
            check_amount_in_words += _(' and %s/100') % str(
                int(round(float_round(decimals * 100, precision_rounding=1))))
        self.amount_char = check_amount_in_words

    @api.depends('amount', 'currency_id')
    def compute_char_amount(self):
        for rec in self:
            check_amount_in_words = rec.currency_id.amount_to_text(rec.amount)
            if rec.amount and rec.currency_id:
                rec.amount_char = check_amount_in_words
            else:
                rec.amount_char = "Zero"