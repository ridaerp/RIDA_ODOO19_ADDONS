
# -*- coding: utf-8 -*-
from odoo import api, models, fields
from odoo.tools import float_round
from datetime import datetime


class AccountStatementReport(models.AbstractModel):
    _name = 'report.account_statement.account_statement_pdf_report'

    def _get_header_info(self, data):
        date_from = data['from_date']
        date_to = data['to_date']
        account_id = data['account_id']
        account_name = data['account_name']
        account_code = data['account_code']
        return {
            'start_date': date_from,
            'end_date': date_to,
            'account_id': account_id,
            'account_name': account_name,
            'account_code': account_code,
            'today': datetime.now().date(),
        }

    def _get_initial_balance(self, data):
        i_debit = 0
        i_credit = 0
        move_line_ids1 = self.env['account.move.line'].search(
            [('date', '<', data['from_date']),
             # ('move_id.state', '=', 'posted'),
             ('account_id', '=', data['account_id'])], order='date,id asc')
        if move_line_ids1:
            for move in move_line_ids1:
                if data['currency'] == False:
                    i_debit += move.debit
                    i_credit += move.credit
                elif data['currency'] == True:
                    if move.amount_currency > 0:
                        i_debit += abs(move.amount_currency)
                        i_credit += 0
                    elif move.amount_currency < 0:
                        i_debit += 0
                        i_credit += abs(move.amount_currency)
        return {
            'i_debit': i_debit,
            'i_credit': i_credit,
            'balance': i_debit - i_credit,
        }

    def _get_data_from_report(self, data):
        res = []
        records = False
        if data:
            if data['from_date'] and data['to_date']:
                move_line_ids = self.env['account.move.line'].search(
                    [('date', '<=', data['to_date']), ('date', '>=', data['from_date']),
                     # ('move_id.state', '=', 'posted'),
                     ('account_id', '=', data['account_id'])], order='date,id asc').mapped('id')
                if move_line_ids:
                    records = self.env['account.move.line'].browse(move_line_ids)
                    # i_debit = 0
                    # i_credit = 0
                    for move in records:
                        date = move.date
                        name = move.name
                        currency_id = move.currency_id.name
                        amount_currency = move.amount_currency
                        journal_id = move.journal_id.code
                        move_id = move.move_id.name
                        if data['currency'] == False:
                            i_debit = move.debit
                            i_credit = move.credit
                        elif data['currency'] == True:
                            if move.amount_currency > 0:
                                i_debit = abs(move.amount_currency)
                                i_credit = 0
                            elif move.amount_currency < 0:
                                i_debit = 0
                                i_credit = abs(move.amount_currency)
                    # res.append({'i_debit': i_debit, 'i_credit': i_credit})
                        res.append({'date': date,'amount_currency':amount_currency,'currency_id':currency_id, 'name': name, 'journal_id': journal_id, 'move_id': move_id, 'i_debit': i_debit, 'i_credit': i_credit})

            return res

    @api.model
    def _get_report_values(self, docids, data=None):
        data['records'] = self.env['account.move.line'].browse(data)
        docs = data['records']
        sales_details_report = self.env['ir.actions.report']._get_report_from_name('account_statement.account_statement_pdf_report')
        docargs = {

            'data': data,
            'docs': docs,
        }
        return {
            'doc_ids': self.ids,
            'doc_model': sales_details_report.model,
            'docs': data,
            'get_data_from_report': self._get_data_from_report(data),
            'get_header_info': self._get_header_info(data),
            'get_initial_balance': self._get_initial_balance(data),
        }