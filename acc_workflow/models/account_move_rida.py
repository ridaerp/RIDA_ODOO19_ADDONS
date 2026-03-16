from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast
import copy
import json
import io
import logging
import lxml.html
import datetime
import ast
from collections import defaultdict
from math import copysign

from dateutil.relativedelta import relativedelta

import xlsxwriter
from odoo.tools import config, date_utils, get_lang
from odoo.osv import expression
from babel.dates import get_quarter_names
from odoo.tools.misc import formatLang, format_date

_logger = logging.getLogger(__name__)

class AccountReport(models.AbstractModel):
    _inherit = 'account.report'


    def open_journal_items(self, options, params):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_line_select")
        ctx = self.env.context.copy()
        if params and 'id' in params:
            active_id = self._get_caret_option_target_id(params['id'])
            ctx.update({
                    'active_id': active_id,
                    'search_default_account_id': [active_id],
            })
        if options:
            if options.get('journals'):
                selected_journals = [journal['id'] for journal in options['journals'] if journal.get('selected')]
                if selected_journals: # Otherwise, nothing is selected, so we want to display everything
                    ctx.update({
                        'search_default_journal_id': selected_journals,
                    })
            domain = expression.normalize_domain(ast.literal_eval(action.get('domain') or '[]'))
            if options.get('analytic_accounts'):
                analytic_ids = [int(r) for r in options['analytic_accounts']]
                domain = expression.AND([domain, [('analytic_account_id', 'in', analytic_ids)]])
            # In case the line has been generated for a "group by" financial line, append the parent line's domain to the one we created
            if params.get('financial_group_line_id'):
                # In case the hierarchy is enabled, 'financial_group_line_id' might be a string such
                # as 'hierarchy_xxx'. This will obviously cause a crash at domain evaluation.
                if not (isinstance(params['financial_group_line_id'], str) and 'hierarchy_' in params['financial_group_line_id']):
                    parent_financial_report_line = self.env['account.financial.html.report.line'].browse(params['financial_group_line_id'])
                    domain = expression.AND([domain, ast.literal_eval(parent_financial_report_line.domain)])
            line_domain=False
            if not options.get('all_entries'):
                ctx['search_default_posted'] = True
            if options['unfolded_lines']:
                numbers = [item for item in options['unfolded_lines'] if
                           isinstance(item, int) or isinstance(item, float)]
                number = numbers[-1] if numbers else None
                if number:
                    current_report_line = self.env['account.financial.html.report.line'].browse(number)
                    if current_report_line.exists():
                        line_domain = ast.literal_eval(current_report_line.domain) or False
            action['domain'] = domain
            if line_domain:
                combined_domain = expression.AND([action['domain'],line_domain])
                action['domain']=combined_domain
        action['context'] = ctx
        return action


class Bills_Workflow(models.Model):
    _inherit = 'account.move'

    user_type_ = fields.Selection(related="create_uid.user_type")

    comment = fields.Text(placeholder="Insert your Comment Here...")
    dm_dep = fields.Many2one('res.users', string = 'Depratment User')
    dm_man = fields.Many2one('res.users', string = 'Manager')
    dm_account = fields.Many2one('res.users', string = 'Accountant')
    dm_adv = fields.Many2one('res.users', string = 'Advisor')
    dm_aud = fields.Many2one('res.users', string = 'Auditor')
    dm_gm = fields.Many2one('res.users', string = 'General Manager')


    dm_date_dep = fields.Date(string='Deprartment User Approval Date')
    dm_date_man = fields.Date(string='Manager Approval Date')
    dm_date_account = fields.Date(string='Accountant Approval Date')
    dm_date_adv = fields.Date(string='Advisor Approval Date')
    dm_date_aud = fields.Date(string='Auditor Approval Date')
    dm_date_gm = fields.Date(string='General Manager Approval Date')

    assigned_to_accountant = fields.Many2one('res.users', 'Assign To', track_visibility='onchange' , domain= lambda self: [("group_ids", "=", self.env.ref("account.group_account_user").id)] )
    ######################################comment by ekhlas#########3
    accountant_type = fields.Selection(string='Employee type', related="assigned_to_accountant.employee_id.rida_employee_type")
    # invoice_date=fields.Date(states=False)
    invoice_date = fields.Date(string='Invoice/Bill Date', readonly=False ,
        states=None)
    status_in_payment = fields.Selection(
        selection_add=[
            ('validate', 'Validated'),
            ('finance', 'Finance Manager'),
            ('internal_audit', 'Internal Audit'),
            ('fleet_director', 'Fleet Director'),
            ('finance_director', 'Finance Director'),
            ('ccso', 'CCSO'),
            ('site', 'Operation Director'),
            ('accountant', 'Accountant'),
            ('rejected', 'Rejected'),
        ],
        # Change 'set default' to 'cascade' or specify 'draft' explicitly
        ondelete={
            'validate': 'cascade',
            'finance': 'cascade',
            'internal_audit': 'cascade',
            'fleet_director': 'cascade',
            'finance_director': 'cascade',
            'ccso': 'cascade',
            'site': 'cascade',
            'accountant': 'cascade',
            'rejected': 'cascade'
        }
    )

    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('validate', 'Validated'),
        ('finance', 'Finance Manager'),
        ('internal_audit', 'Internal Audit'),
        ('fleet_director', 'Fleet Director'),
        ('finance_director', 'Finance Director'),
        ('ccso', 'CCSO'),
        ('site', 'Operation Director'),
        ('accountant', 'Accountant'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('rejected', 'Rejected'),
    ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')

    ############################## change function by ekhlas    
    def action_submit(self):
        for rec in self:
            if not rec.invoice_date:
                raise ValidationError(_("Please write and check The Bill date."))

            rec.write({'state': 'validate'})


    def action_finance(self):
       for rec in self:
            # if rec.landed_cost_id:
            #     if rec.landed_cost_id.state != 'done':
            #         raise UserError("Landed Cost must be Posted first.")

            if not rec.assigned_to_accountant:
                raise UserError("Please Assign Accountant !")


            ###################3comment by ekhlas ###################
            # if rec.accountant_type == 'site':
            if rec.assigned_to_accountant.user_type == 'site':
                rec.write({'state': 'internal_audit',})
            elif rec.assigned_to_accountant.user_type == 'fleet':
                rec.write({'state': 'fleet_director',})                
            ###################3comment by ekhlas ###################
            # elif rec.accountant_type == 'hq':
            elif rec.assigned_to_accountant.user_type == 'hq':
                rec.write({'state': 'internal_audit',})

            elif rec.assigned_to_accountant.user_type == 'rohax':
                rec.write({'state': 'accountant',}) 

            else:
                raise UserError("The Employee Has No type!")

    def action_internal_audit(self):
        for rec in self:
            ###ekhlas code#################change status 
            # rec.write({'state': 'ccso'})
            # if rec.assigned_to_accountant.user_type == 'hq':
            #     rec.write({'state': 'accountant'})
            # else:
            #     rec.write({'state': 'site'})


            ############################new change by thiqup comments

            rec.write({'state': 'accountant'})





    def action_finance_director(self):
        for rec in self:
            rec.write({'state': 'accountant'})

    
    def action_ccso(self):
        for rec in self:
            rec.write({'state': 'accountant'})
    
    
    def action_site(self):
        for rec in self:
            rec.write({'state': 'accountant'})


    def action_reject(self):
        for rec in self:
            rec.write({'state': 'draft'})

    def action_draft(self):
        return self.write({'state': 'draft'})
    
    def action_fleet(self):
        for rec in self:
            rec.write({'state': 'accountant'}) 


    def button_draft(self):
        return super(Bills_Workflow, self).button_draft()

 

    # def write(self, vals):
    #     result = super(Bills_Workflow, self).write(vals)
    #     if 'payment_state' in vals:
    #         self._check_related_purchase_payment_status()
    #     return result


    # def _check_related_purchase_payment_status(self):
    #     for move in self:
    #         if move.move_type != 'in_invoice':
    #             continue
    #         purchase_orders = move.purchase_id
    #         for po in purchase_orders:
    #             linked_records = self.env['overseas.payment'].search([('purchase_order_id', '=', po.id)])
    #             for record in linked_records:
    #                 record.check_payment_status()


class AnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    type = fields.Selection(string="", selection=[('dept', 'Department'), ('asset_mach', 'Asset / Machine'),('plant', 'Plant'),('process', 'Process'),('project', 'Project'),('supplier', 'Material Minds/supplier'),('other', 'Others'),], required=False, )
    analytic_type = fields.Selection(string="", selection=[('ser_cost_center', 'Service Cost Centers'), ('prod_cost_center', 'Productive Cost Center'),('admin_cost_center', 'Administrative Cost Center'),('capitalized', 'Capitalized Cost Centers'),
                                                           ('group_business_dev','Group Business Development '),('group_cost_center', 'Group Cost Centers'),('none', 'None'),], required=False, )



# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'
#
#     journal_type = fields.Selection(
#         related='move_id.journal_id.type',
#         store=True,
#         string="Journal Type",
#     )


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _compute_journal_dashboard_data(self):
        """Override to hide cash journals for users with the `rohax_audit` group."""
        self = self.filtered(lambda j: j.type != 'cash' or not self.env.user.has_group('base_rida.rohax_audit'))
        return super(AccountJournal, self)._compute_journal_dashboard_data()
