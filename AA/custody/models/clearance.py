# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import  UserError,ValidationError
import time
from odoo.tools import float_round

class CustodyClearLine(models.Model):
    _name = "custody.clear.line"
    account_id = fields.Many2one('account.account')
    amount = fields.Float()
    desc = fields.Char("Description")
    wizard_id = fields.Many2one('custody.clear')
    cost_center = fields.Many2one("account.analytic.account", string='Cost Center',required=True, related='wizard_id.analytic_id',readonly=False )
    attachment = fields.Binary('Attachment Document' )
    partner_id=fields.Many2one("res.partner","Partner")



    @api.onchange('partner_id')
    def get_account(self):
        self.account_id = self.partner_id.property_account_payable_id


class CustodyClear(models.Model):
    _name = "custody.clear"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Clearance'

    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('name', 'New') == 'New':
                val['name'] = self.env['ir.sequence'].next_by_code('custody.clear') or 'New'
        return super(CustodyClear, self).create(vals)

    @api.model
    def _default_amount(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        custody = self.env['account.custody'].browse(active_ids)
        return custody.residual

    def _default_currency(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        custody = self.env['account.custody'].sudo().browse(active_ids)
        return custody.currency_id.id

    def _default_journal(self):
        journal = self.env['account.journal'].search([['code', '=', 'CLR']], limit=1)
        return journal.id

    # @api.onchange('claimant')
    # def _get_uncleared_petty_cash(self):
    #     uncleared_list = []

    #     petty_cash = self.env['petty.cash'].search([('employee_id', '=', self.claimant.id), ('state', '!=', 'cleared')])
    #     for each in petty_cash:
    #         uncleared_list.append(each.id)
    #     if uncleared_list:
    #         return {
    #             'domain': {'ac_id': [('id', 'in', uncleared_list)]},
    #         }
    #     return {
    #         'domain': {'ac_id': [('id', 'in', -1)]},
    #     }
    name = fields.Char("Voucher No.", required=True, index=True, readonly=True, default=lambda self: _('New'), copy=False)

    ac_id = fields.Many2one('account.custody', string="Petty Cash", required=True,
                            index=True)  # , domain=_get_uncleared_petty_cash)
    residual = fields.Float(related="ac_id.residual")
    employee_id = fields.Many2one("hr.employee", string="Employee",related="ac_id.employee_id")
    # employee_id = fields.Many2one("hr.employee", string="Employee")
    description = fields.Text("Description", related="ac_id.description")
    # claimant = fields.Many2one("hr.employee", string="Claimant", default=lambda  self: self._get_employee())
    clearance_date = fields.Date("Requested Date", default=lambda *a: time.strftime('%Y-%m-%d'))
    company_id = fields.Many2one('res.company', string="Company",related="ac_id.company_id")

    account_id = fields.Many2one('account.account', "Clearing Account")
    amount = fields.Float(string='Amount', required=True, default=_default_amount)
    cus_amount = fields.Float(string='Amount', required=True,related="ac_id.amount")
    # old code currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=_default_currency)
    currency_id = fields.Many2one(string='Currency', related="ac_id.currency_id")
    journal_id = fields.Many2one('account.journal', default=_default_journal)
    communication = fields.Char(string='Note')
    account_ids = fields.One2many('custody.clear.line', 'wizard_id', string='Accounts')
    state = fields.Selection([
        ('draft', 'Draft'),
        # Clearance
        ('req_manager', 'Line Manager'),
        ('finance_manager', 'Finance Manager'),

        ('ccso_approval', 'Waiting For COO Approval'),

        ('site_approval', 'Waiting ForOperation Director Approval'),

        ('fleet_approval', 'Waiting For Fleet Director Approval'),
        ('internal_audit', 'Internal Audit'),

        # Payment Request
        ('site_accountant', 'Accountant'),
        ('accountant', 'Accountant'),
        ('approved', 'Approved'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected')




    ], default='draft', readonly=True,track_visibility='onchange')

    #added by ekhlas code############################
    analytic_id = fields.Many2one(related="ac_id.analytic_id" ,string="Analytic Account")
    attachment = fields.Binary('Attachment Document' )


    ###############added by ekhlas code
    requested_by = fields.Many2one('res.users', 'Requested by', track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True, readonly=True)

    ###############added by ekhlas code
    def get_requested_by(self):
        user = self.env.user.id
        return user


    #added by ekhlas code############################
    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Only draft records can be deleted!")
        return super(CustodyClear, self).unlink()



    def _get_employee(self):
        if len(self.env.user.employee_ids) > 0:
            employee = self.env.user.employee_ids[0].id
            return employee or False

    # is_manager = fields.Boolean(compute='check_manager')

    # def check_manager(self):
    #     for rec in self:
    #         if rec.claimant:
    #             rec.is_manager = False
    #             if rec.claimant.parent_id.user_id.id == self.env.user.id:
    #                 rec.is_manager = True
    #             else:
    #                 rec.is_manager = False
    #         else:
    #             rec.is_manager = False


    # @api.constrains('amount')
    # def _check_amount(self):
    #     if not self.amount > 0.0:
    #         raise ValidationError('The amount must be strictly positive.')

    @api.constrains('ac_id')
    def _check_ac_id(self):
        uncleared_list = []

        petty_cash = self.env['account.custody'].search([('state', '!=', 'cleared')])
        # raise UserWarning(petty_cash)
        for each in petty_cash:
            uncleared_list.append(each.id)
        if self.ac_id.id not in uncleared_list:
            raise ValidationError('This Custody is cleared.')


    #requester
    def action_submit_to_req_manager(self):
        self.ensure_one()
        self.write({'state': 'req_manager'})


    ################added by ekhlas code 
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


            rec.state = "finance_manager"
            




    def button_lm_reject(self):
        for rec in self:
            rec.state = "draft"


    def button_submit(self):
        self.state = "req_manager" #lm_approval => fin_mgr_approval



    #manager
    def action_submit_to_finance_manager(self):

        for rec in self:
            #comment by ekhlas code if rec.employee_id.employee_type == 'site':
            if rec.requested_by.user_type == 'site':
                rec.state = "internal_audit"
            elif rec.requested_by.user_type=='fleet':
                rec.state='fleet_approval'
            else : 
                self.state = "internal_audit"




    def button_fin_mgr_reject(self):
         self.state = "req_manager"






    #Payable Accountant actions
    def action_reject(self):
        for rec in self:
            if rec.employee_id.employee_type == 'site':
                rec.state = "site_approval"
            if rec.employee_id.employee_type == 'hq':
                rec.state = "ccso_approval"
            else : 
                self.state = "fleet_approval"


        #After Clearence actions#
    def action_draft(self):
        self.write({'state': 'draft'})








# internal audit buttons
    def button_audit_reject(self):
         self.state = "finance_manager"



    def action_internal_audit_sheets(self): 
        for rec in self:
            #comment by ekhlas code if rec.employee_id.employee_type == 'site':
            if rec.requested_by.user_type == 'site':
                # rec.state = "site_approval"
                rec.state="accountant"
            else : 
                # self.state = "ccso_approval"
                rec.state="accountant"


    def button_site_approval(self):
        for rec in self:
            rec.state = "accountant"
        
    def button_site_reject(self):
        for rec in self:
            rec.state = "internal_audit"


    def button_ccso_approval(self):
        for rec in self:
            rec.state = "accountant"
        
    def button_ccso_reject(self):
        for rec in self:
            rec.state = "internal_audit"


    def button_fleet_approval(self):
        for rec in self:
            rec.state = "accountant"
        
    def button_fleet_reject(self):
        for rec in self:
            rec.state = "finance_manager"

    def button_cancel(self):
        for rec in self:
            rec.state = "cancel"






    def validate(self):

        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        custody = self.ac_id



        partner = custody.employee_id.employee_partner_id

        journal = self.journal_id
        if not journal:
            raise ValidationError("Please the Clearing Journal")
        credit_line = debit_line = []
        ctx = dict(self._context)
        for rec in self:
            if len(rec.account_ids) < 1:
                raise ValidationError("Please select at least one account!")
            amount = 0.0
            for line in rec.account_ids:

                if not line.account_id:
                    raise ValidationError("Please enter account and make sure accout in same company!")

                amount += line.amount
            
            # comment by ekhlas 
            # if amount > custody.residual:
                # raise ValidationError(
                #     "Clearing amount cannot be greater than custody residual. (" + str(custody.residual) + ")")
            
            move = self.env['account.move'].search([['custody_id', '=', custody.id], ['state', '=', 'draft']], limit=1)

            desc = rec.communication or " "
            if move:
                move = move

            else:
                move = self.env['account.move'].create({
                    'journal_id': journal.id,
                    'ref': custody.name + "-" + desc,
                    'custody_id': custody.id,
                })
            AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False)

            credit_line = AccountMoveLine.search(
                [['move_id', '=', move.id], ['account_id', '=', custody.account_id.id]], limit=1)
            if credit_line:
                credit_line.update({
                    'credit': credit_line.credit + amount
                })
            else:
                AccountMoveLine.create({
                    'name': custody.employee_id.name,
                    'move_id': move.id,
                    'account_id': custody.account_id.id,
                    'credit': amount,
                    'partner_id':  partner.id,
                })

            analytic_distribution = []

            if custody.analytic_id:  # Ensure that the analytic ID exists
                analytic_distribution.append((0, 0, {
                    'analytic_account_id': custody.analytic_id.id,
                    'amount': 100.0  # Adjust this as per your logic
                }))



            for line in rec.account_ids:
                AccountMoveLine.create({
                    'name': line.desc or custody.employee_id.name,
                    'move_id': move.id,
                    'account_id': line.account_id.id,
                    'debit': line.amount,
                    'partner_id':line.partner_id.id or partner.id,
                    # 'analytic_account_id': custody.analytic_id.id if custody.analytic_id else False,
                    # 'analytic_distribution':analytic_distribution,
                    'analytic_distribution': {
                        str(custody.analytic_id.id): 100} if custody.analytic_id else False,
                    #                    'custody_id': custody.employee_id.employee_partner_id.id
                })


            # # Process analytic_distribution
            # account_distributions = {
            #     float_round(line[2]['amount'], decimal_precision): line[2]['analytic_account_id']
            #     for line in analytic_distribution
            # }

            move.action_post()

            to_reconcile = custody.move_id.line_ids.filtered(lambda l: l.account_id == custody.account_id)
            to_reconcile += move.line_ids.filtered(lambda l: l.account_id == custody.account_id)
            to_reconcile.reconcile()

            custody.clear_amount += amount
            # changing amount to be new_amount to make custody state = cleard after adding amedment amount in extened
            # custody module if custody.clear_amount == custody.amount:
            if custody.clear_amount == custody.amount:
                custody.state = "cleared"
            else:
                custody.state = "partially_cleared"
            self.write({'state': 'approved'})

        return {'type': 'ir.actions.act_window_close'}
