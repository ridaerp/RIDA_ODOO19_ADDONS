from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime

class PaymentRequest(models.Model):
    _name = 'payment.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _description = 'Payment request details'
    
    
    name = fields.Char('Payment Request', required=True, index=True, copy=False, default='New')
    vendor_id = fields.Many2one(comodel_name='res.partner', string='Contractor',
                                related='contract_number.vendor_id', track_visibility='onchange')
    contract_number = fields.Many2one(comodel_name='contract.contract',string='Contract ID')
    risk_cost = fields.Monetary(string='Risk cost')
    actual_estimated_cost = fields.Float(comodel_name='contract.contract',
                                  related='contract_number.estimated_cost' ,string='Actual Payment Amount')
    estimated_cost = fields.Float(string='Payment Amount')
    currency_id = fields.Many2one('res.currency', related='contract_number.currency_id' )
    curr_rate = fields.Float(string='Currency Rate', compute='_get_default_currency_rate')
    date = fields.Date(string='Request date')
    pay_date = fields.Date(string='Payment date')

    contract_ids = fields.Many2one(comodel_name='contract.contract.lines')
    voucher = fields.Many2one(comodel_name='purchase.order',string='Voucher(PO/ PR) No')
    receipt = fields.Many2one(comodel_name='stock.picking',string='Receipt No')
    state = fields.Selection(string="Status", selection=[('draft', 'Draft'),
                                                         ('approve', 'Approve'),
                                                         ('reject', 'Reject'),
                                                         ('pending', 'Pending'),
                                                         ('reject_approve', 'Reject Then Approved'),], default='draft', track_visibility='onchange')
    #     draft,approve-reject-pending) add status( reject then approve
    total = fields.Monetary(string='Total', 
    )
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, )
    remark = fields.Text(string='Remark')
    store_invoice = fields.Many2one(comodel_name='account.move')
    invoice_count = fields.Integer(string="Count", compute='compute_invoice_count')
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('payment.request.sequence') or _('New')
        result = super(PaymentRequest, self).create(vals)
        return result    

    @api.model
    def _get_default_currency_rate(self):
        rate=self.env['res.currency.rate'].search([('id','=',self.currency_id.id)], limit=1).rate
        c_rate=rate
        self.curr_rate=c_rate

# Contract speciliest approv
    def approve_button(self):
        for rec in self:
            rec.write({'state': 'approve'})

    def approve_reject_button(self):
        for rec in self:
            rec.write({'state': 'reject_approve'})

    def action_reject(self):
        for rec in self:
            rec.write({'state': 'reject'})

    def compute_invoice_count(self):
        self.ensure_one()
        self.invoice_count = self.env['account.move'].search_count([('pyment_req_id', '=', self.id)])

    def button_create_invoice(self):
        # self.clicked = True
        create_invoice = {
            'partner_id': self.vendor_id.id,
            'pyment_req_id': self.id,
            'move_type': 'in_invoice',
            'payment_reference': self.name,

        }
        invoice = self.env['account.move'].create(create_invoice)
        self.store_invoice = invoice.id

        for line in self.contract_ids:
            vals = []
            vals.append((0, 0, {
                'quantity': line.quantity,
                'product_id': line.product_id.id,
                # 'analytic_account_id': line.analytic_account_account,
                'price_subtotal': line.total,
                'price_unit': line.estimated_cost,
                'account_id': line.account_id,
                'name': 'name',
            }))
            invoice.update({'invoice_line_ids': vals})
            # self.store_invoice = invoice.id
        return self.action_view_invoice()

    def action_view_invoice(self):
        return {
            'name': "Bills",
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('pyment_req_id', '=', self.id)],
        }
