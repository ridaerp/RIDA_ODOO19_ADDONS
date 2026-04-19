# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'
    edi_show_force_cancel_button = fields.Boolean(string='EDI Show Cancel Button')
    show_commercial_partner_warning = fields.Boolean(string='show_commercial_partner_warning')
    show_update_fpos = fields.Boolean(string='show update fpos')




class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    # has_abnormal_deferred_dates = fields.Boolean(string='has_abnormal_deferred_dates')

class AccountMoveLine(models.TransientModel):
    _inherit = 'account.payment.register'
    writeoff_is_exchange_account = fields.Boolean(string='writeoff_is_exchange_account')
    qr_code = fields.Char(string='QR Code')

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"


    is_quantity_copy2 = fields.Boolean(string="",default=True)
    payment_term_id = fields.Many2one(
        'account.payment.term',
        string="Payment Terms",
        domain=lambda self: [
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.env.user.company_id.id)
        ],
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="Partner",
        domain=lambda self: [
            '|',
            ('company_id', '=', False),  # For single company users
            ('company_id', '=', self.env.user.company_id.id)  # For multi-company users
        ]
    )


class StockMove(models.Model):
    _inherit = "stock.move"

    analytic_account_id = fields.Many2one('account.analytic.account')
    analytic_tag_ids = fields.Char()


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    # analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    analytic_tag_ids = fields.Char(string='Analytic Tags')
