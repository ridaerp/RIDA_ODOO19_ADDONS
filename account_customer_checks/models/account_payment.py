# -*- coding: utf-8 -*-
import ast

from odoo import models, fields, api, tools, _

class StockMove(models.Model):

    _inherit = "stock.move"
    equipment_id =  fields.Many2one('maintenance.equipment', 'Equipment', ondelete="cascade",readonly=True)
class AnalyticLine(models.Model):

    _inherit = "account.analytic.line"
    equipment_id =  fields.Many2one('maintenance.equipment', 'Equipment', ondelete="cascade",readonly=True)

class AccountMoveLine(models.Model):

    _inherit = "account.move.line"
    def _prepare_analytic_line(self):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            an analytic account. This method is intended to be extended in other modules.
            :return list of values to create analytic.line
            :rtype list
        """
        result = []
        for move_line in self:
            amount = (move_line.credit or 0.0) - (move_line.debit or 0.0)
            default_name = move_line.name or (move_line.ref or '/' + ' -- ' + (move_line.partner_id and move_line.partner_id.name or '/'))
            result.append({
                'name': default_name,
                'date': move_line.date,
                'equipment_id': move_line.equipment_id.id,
                'account_id': move_line.analytic_account_id.id,
                'group_id': move_line.analytic_account_id.group_id.id,
                'tag_ids': [(6, 0, move_line._get_analytic_tag_ids())],
                'unit_amount': move_line.quantity,
                'product_id': move_line.product_id and move_line.product_id.id or False,
                'product_uom_id': move_line.product_uom_id and move_line.product_uom_id.id or False,
                'amount': amount,
                'general_account_id': move_line.account_id.id,
                'ref': move_line.ref,
                'move_id': move_line.id,
                'user_id': move_line.move_id.invoice_user_id.id or self._uid,
                'partner_id': move_line.partner_id.id,
                'company_id': move_line.analytic_account_id.company_id.id or move_line.move_id.company_id.id,
            })
        return result


class AccountJournal(models.Model):
    _inherit = 'account.journal'
    is_check_journal = fields.Boolean('Check Journal')

    def open_action(self):
        """return action based on type for related journals"""
        self.ensure_one()
        action_name = self._select_action_to_open()

        # Set 'account.' prefix if missing.
        if not action_name.startswith("account."):
            action_name = 'account.%s' % action_name

        action = self.env["ir.actions.act_window"]._for_xml_id(action_name)
        context = self._context.copy()

        if 'context' in action and isinstance(action['context'], str):
            try:
                # Clean up the string by removing unnecessary newlines and indentation
                cleaned_context = action['context'].replace('\n', '').replace('    ', '')
                context.update(ast.literal_eval(cleaned_context))
            except (SyntaxError, ValueError) as e:
                raise ValueError(f"Invalid context format in action: {e}")
        else:
            context.update(action.get('context', {}))



        action['context'] = context
        action['context'].update({
            'default_journal_id': self.id,
        })

        domain_type_field = action['res_model'] == 'account.move.line' and 'move_id.move_type' or 'move_type' # The model can be either account.move or account.move.line

        # Override the domain only if the action was not explicitly specified in order to keep the
        # original action domain.
        if action.get('domain') and isinstance(action['domain'], str):
            action['domain'] = ast.literal_eval(action['domain'] or '[]')
        if not self._context.get('action_name'):
            if self.type == 'sale':
                action['domain'] = [(domain_type_field, 'in', ('out_invoice', 'out_refund', 'out_receipt'))]
            elif self.type == 'purchase':
                action['domain'] = [(domain_type_field, 'in', ('in_invoice', 'in_refund', 'in_receipt', 'entry'))]

        action['domain'] = (action['domain'] or []) + [('journal_id', '=', self.id)]
        return action


class account_payment(models.Model):
    _inherit = 'account.payment'



    check_ref = fields.Char('Check Reference')
    check_no = fields.Char('Check Number')
    # check_date = fields.Date('Maturity Date')
    check_journal_id = fields.Many2one('account.journal', 'Clearing Journal',domain=[('type', 'in', ('bank', 'cash')), ('is_check_journal', '!=', True)])
    is_check_journal = fields.Boolean(related='journal_id.is_check_journal',store=True)
    # active = fields.Boolean()
    state = fields.Selection([('draft', 'Draft'), ('in_process', 'In Process'),('posted', 'Posted'), ('sent', 'Sent'), ('reconciled', 'Reconciled'),('cancel', 'Cancelled')],
                             readonly=True, default='draft', copy=False, string="Status")


    @api.depends('journal_id','check_journal_id')
    def _get_check_formate(self):
        formate_id = self.env['cheque.setting'].search(['|',('journal_id','=',self.journal_id.id),('journal_id','=',self.check_journal_id.id)],limit=1)
        # formate_id = self.env['cheque.setting'].search([('journal_id','=',self.journal_id.id)],limit=1)
        # if self.check_journal_id :
        #     self.cheque_formate_id=formate2_id.id
        # else:
        #     self.check_journal_id=False
        self.cheque_formate_id = formate_id.id



    @api.depends('journal_id', 'currency_id')
    def compute_pdc_journal(self):
        company_currency = self.env.user.company_id.currency_id
        for rec in self:
            if not rec.journal_id or not rec.currency_id:
                continue
            if rec.journal_id and rec.journal_id.is_check_journal and rec.currency_id.id == company_currency.id:
                rec.is_check_journal = True

    def action_post(self):
        PDC = self.env['account.pdc']

        company_currency = self.env.user.company_id.currency_id
        for rec in self:
            if rec.is_check_journal:
                PDC.create({
                    'name': rec.cheque_no or '/',
                    'check_no': rec.cheque_no ,
                    'maturity_date': rec.check_date,
                    'clear_date': rec.check_date,
                    'journal_id': rec.check_journal_id.id if rec.check_journal_id else False,
                    'type': 'customer' if rec.payment_type == 'inbound' else 'vendor',
                    'payment_id': rec.id,
                    'partner_id': rec.partner_id.id,
                    'currency_id': company_currency.id,
                    'amount': rec.amount,
                })
            rec.state = 'posted'
        return super(account_payment, self).action_post()
