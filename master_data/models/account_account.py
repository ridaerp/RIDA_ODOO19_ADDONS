from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class RequestAccountAccount(models.Model):
    _name = 'request.account.account'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Finance Account Request '

    code_seq = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True,
                             readonly=True)
    department_id = fields.Many2one('hr.department', string="Department", readonly=True, store=True)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    state = fields.Selection(
        [('draft', 'Draft'), ('w_adv', 'Waiting Account Advisor'), ('md', 'Waiting Master Admin'),
         ('reject', 'reject'), ('done', 'Done')],
        string='Status', default='draft', track_tracking=True, copy=False)
    date = fields.Date(default=fields.Date.today(), readonly=True)

    code = fields.Char(string='Reference', index=True, tracking=True)
    name = fields.Char(string='Account Name', index=True, required=True, tracking=True)
    # user_type_id = fields.Many2one('account.account.type', string='Type',
    #     help="Account Type is used for information purpose, to generate country-specific legal reports, and set the rules to close a fiscal year and generate opening entries.")

    user_type_id = fields.Selection( [
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Bank and Cash"),
            ("asset_current", "Current Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Current Liabilities"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "Income"),
            ("income_other", "Other Income"),
            ("expense", "Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ], string='Type',  help="Account Type is used for information purpose, to generate country-specific legal reports, and set the rules to close a fiscal year and generate opening entries.")


    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    reconcile = fields.Boolean(string='Allow Reconciliation', default=False,
        help="Check this box if this account allows invoices & payments matching of journal items.")
    description = fields.Text('')
    new_account = fields.Many2one("account.account", string='Account', readonly=1, copy=False)

    def _track_subtype(self, init_values):
        self.ensure_one()
        if self.state == 'done':
            return self.env.ref('master_data.request_account_status')
        if self.state == 'reject':
            return self.env.ref('master_data.request_account_rej_status')
        return super(RequestAccountAccount, self)._track_subtype(init_values)

    def activity_update(self):
        for rec in self:
            users = []
            message = ""
            if rec.state == 'w_adv':
                users = self.env.ref('base_rida.rida_group_master_data_manager').user_ids
                message = "Please Create the Account"
                for user in users:
                    self.activity_schedule('master_data.mail_act_master_data_approval', user_id=user.id, note=message)
            else:
                continue


    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")

        return super(RequestAccountAccount, self).unlink()

    @api.model
    def create(self, vals):
        for val in vals:
            val['code_seq'] = self.env['ir.sequence'].next_by_code('account.request') or ' '
        return super(RequestAccountAccount, self).create(vals)


    def set_confirm(self):
        return self.write({'state': 'w_adv'})
    def set_advisor_confirm(self):
        self.activity_update()
        return self.write({'state': 'md'})

    def create_account(self):
        self.new_account = self.env["account.account"].create({
            'name': self.name,
            'code': self.code,
            'account_type': self.user_type_id,
            'company_ids': [(6, 0, [self.company_id.id])],
            'reconcile': self.reconcile,
        })
        return self.write({'state': 'done'})








