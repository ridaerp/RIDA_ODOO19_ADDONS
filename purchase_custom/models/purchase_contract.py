from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError


class PurchaseContractType(models.Model):
    _name = 'purchase.contract.type'
    _description = 'Purchase Contract Type'

    name = fields.Char(string='Contchange_orderract Type', required=True)
    sequence = fields.Integer(help="Gives the sequence when displaying a list of Contract.", default=10)


class InheritPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    contract_refrence = fields.Char(string='Contract Reference', required=True,
                                    readonly=False, index=True, )
    # default=lambda self: _('New'),
    # compute='get_contract_ref')
    title = fields.Char('Title')
    portion_of_agreement_affected = fields.Text(string='Portion of agreement affected')
    description = fields.Text('Description of service')
    scope_work = fields.Text('Scope of work')
    terms_doc = fields.Binary()
    scope_doc = fields.Binary()
    remarks = fields.Text('Remarks And Notes')
    terms = fields.Text('Term And Conditions')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, )
    order_line = fields.One2many('purchase.order.line', 'order_id', string='Order Lines',
                                 states={'cancel': [('readonly', True)]},
                                 attrs={'readonly': [('state', '!=', ['draft', 'running'])]}, copy=True, auto_join=True)

    contract_value = fields.Float('Contract Value', required=True)
    contract_type = fields.Many2one('purchase.contract.type', string="Contract Type", required=True,
                                    # default=lambda self: self.env['purchase.contract.type'].search([], limit=1)
                                    )
    type_of_change = fields.Selection(string='Type of change', required=True,
                                      selection=[('change_order', 'Change Order'),
                                                 ('amendment', 'Amendment'),
                                                 ('extension', 'Extension'),
                                                 ('renewal ', 'Renewal'),
                                                 ('others ', 'Other')
                                                 ], default='change_order')
    date_start = fields.Date('Start date', help="Date when the Contract will be Effective.",
                             track_visibility='onchange')
    end_start = fields.Date('End date', help="Contract will be Expired on this Date.", track_visibility='onchange')
    time = fields.Integer(string='Duration')
    store_contract = fields.Many2one(comodel_name='change.contract')
    contract_count = fields.Integer(string='Contract Count', compute='compute_contract_count')
    contract_status = fields.Selection(string='Contract Status', selection=[('running', 'Running'),
                                                                            ('renewal', 'Renewal'),
                                                                            ('changed', 'Changed')], readonly=True)
    check_user = fields.Boolean(string='user', compute='_compute_user_check', default=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Contract Sent'),
        ('purchase', 'Section Head Approval'),
        ('running', 'Running'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')

    purchase_type = fields.Selection(string='purchase type',
                                 selection=[('contract', 'Contract'),
                                            ('purchase', 'Purchase Order')], default="contract")

    def get_contract_ref(self):
        for rec in self:
            rec.contract_refrence = 'SC/000' + str(self.id)

    def _compute_user_check(self):
        if self.env.user.has_group('purchase_contract.group_bd_section_head'):
            self.check_user = True
        else:
            self.check_user = False

    # def button_submit(self):
    #     for rec in self:
    #         rec.write({'state': 'contact_s_h'})

    def button_approve(self):
        for rec in self:
            # rec.write({'state': 'running'})
            rec.contract_status = 'running'

    @api.constrains('date_start', 'end_start')
    def _check_dates(self):
        if self.filtered(lambda c: c.end_start and c.date_start > c.end_start):
            raise ValidationError(_('Contract start date must be less than contract end date.'))

    def button_change_contract(self):
        view_id = self.env.ref('purchase_contract.change_purchase_contract_view_form')
        create_change_contract = {
            'customer': self.partner_id.id,
            'contract_value': self.contract_value,
            'contract_refrence': self.contract_refrence,
            'scope_work': self.scope_work,
            'terms_doc': self.terms_doc,
            'remarks': self.remarks,
            'terms': self.terms,
            'contract_status': self.contract_status,
            'date_start': self.date_start,
            'end_start': self.end_start,
            'time': self.time,
            'portion_of_agreement_affected': self.portion_of_agreement_affected,
            'inherit_sc': self.id,
        }
        for line in self.order_line:
            lines = [(0, 0, {
                'name': line.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'name': line.name,
                'rate': line.rate,
                'price_subtotal': line.price_subtotal,
                'price_unit': line.price_unit,
            })]
        create_change_contract.update({'contract_ids': lines})
        ctr = self.env['change.contract'].create(create_change_contract)
        self.store_contract = ctr
        return self.action_view_contracts()

    def action_view_contracts(self):
        return {
            'name': "Change in Contracts",
            'type': 'ir.actions.act_window',
            'res_model': 'change.contract',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('inherit_sc', '=', self.id)],
        }

    def compute_contract_count(self):
        self.ensure_one()
        self.contract_count = self.env['change.contract'].search_count(
            [('inherit_sc', '=', self.id)])


####### Contract Type  #########

class PurchaseProductType(models.Model):
    _inherit = 'purchase.order.line'
    rate = fields.Integer('Rates')

    order_id = fields.Many2one('purchase.order', string='Order Reference', )
