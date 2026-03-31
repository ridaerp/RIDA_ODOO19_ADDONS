from odoo import api, fields, models



class ResCurrency(models.Model):
    _inherit = 'res.currency'

    fixed_rate = fields.Boolean(string="Fixed Rate", default=False)
    usd_rate = fields.Float(string="USD Rate")


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    usd_rate = fields.Float(string="USD Rate")


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    custom_currency_id = fields.Many2one(
        'res.currency',
        string='Custom Currency',
        default=lambda self: self.env.ref('base.USD', raise_if_not_found=False),
    )

    amount_in_usd = fields.Float(string="Amount in USD ", compute='_compute_amount_in_usd')

    @api.depends('currency_id', 'amount_currency', 'move_id.date', 'move_id.company_id')
    def _compute_amount_in_usd(self):
        Currency = self.env['res.currency']
        CurrencyRate = self.env['res.currency.rate']

        for line in self:
            currency = line.currency_id
            move = line.move_id

            usd_currency = self.env.ref('base.USD', raise_if_not_found=False)
            line.custom_currency_id = usd_currency

            if not currency or not move:
                line.amount_in_usd = 0.0
                continue

            # Case 1: USD
            if currency.name == 'USD':
                line.amount_in_usd = line.amount_currency

            elif currency.fixed_rate and currency.usd_rate:
                if currency.usd_rate:
                    line.amount_in_usd = line.amount_currency / currency.usd_rate

            # Case 2: SDG → use company_rate of USD
            elif currency.name == 'SDG':
                usd_currency = Currency.search([('name', '=', 'USD')], limit=1)
                if usd_currency:
                    usd_rate = CurrencyRate.search([
                        ('currency_id', '=', usd_currency.id),
                        ('company_id', '=', move.company_id.id),
                        ('name', '<=', move.date),
                    ], order='name desc', limit=1)
                    if usd_rate and usd_rate.company_rate:
                        line.amount_in_usd = line.amount_currency * usd_rate.company_rate
                    else:
                        line.amount_in_usd = 0.0
                else:
                    line.amount_in_usd = 0.0

            # Case 3: other currencies → use usd_rate
            else:
                currency_rate = CurrencyRate.search([
                    ('currency_id', '=', currency.id),
                    ('company_id', '=', move.company_id.id),
                    ('name', '<=', move.date),
                ], order='name desc', limit=1)

                if currency_rate and currency_rate.usd_rate:
                    line.amount_in_usd = line.amount_currency / currency_rate.usd_rate
                else:
                    line.amount_in_usd = 0.0
