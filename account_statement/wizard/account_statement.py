# -*- coding: utf-8 -*-


# -*- coding: utf-8 -*-
import time
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountStatementPDF(models.TransientModel):
    _name = 'account.statement.pdf'

    from_date = fields.Date('From Date', required=True, default=time.strftime('%Y-01-01'))
    to_date = fields.Date('To Date', required=True, default=time.strftime('%Y-12-31'))
    account_id = fields.Many2one('account.account', 'Account', required=True)
    currency = fields.Boolean('Currency')


    # @api.multi
    def print_report(self):
        # """
        # To get the date and print the report
        # @return : return report
        # """
        # if (not self.env.user.company_id.logo):
        #     raise UserError(_("You have to set a logo or a layout for your company."))
        # elif (not self.env.user.company_id.external_report_layout):
        #     raise UserError(_("You have to set your reports's header and footer layout."))

        data = {}
        res = {}
        if self.from_date and self.to_date:
            move_line_ids = self.env['account.move.line'].search(
                [('date', '<=', self.to_date), ('date', '>=', self.from_date), 
                # ('move_id.state', '=', 'posted'),
                 ('account_id', '=', self.account_id.id)], order='date,id asc').mapped('id')

            move_line_ids1 = self.env['account.move.line'].search(
                [('date', '<', self.from_date),
                 ('move_id.state', '=', 'posted'),
                 ('account_id', '=', self.account_id.id)], order='date,id asc').mapped('id')

        data['from_date'] = self.from_date
        data['to_date'] = self.to_date
        data['account_id'] = self.account_id.id
        data['account_name'] = self.account_id.name
        data['account_code'] = self.account_id.code
        data['currency'] = self.currency
        # print(data)
        return self.env.ref('account_statement.account_statement_pdf_report_id').report_action([], data=data)