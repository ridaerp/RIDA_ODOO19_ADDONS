from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime

class ChangeContract(models.Model):
    _name = 'change.contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Change in Contract'
    
    
    name = fields.Char('Change Contract Reference', required=True, index=True, copy=False, default='New')
    vendor_id = fields.Many2one(comodel_name='res.partner', string='Contracer', track_visibility='onchange')
    contract_number = fields.Many2one(comodel_name='contract.contract',string='Contract Reference')
    date = fields.Date(string='Date', default=datetime.today())
    type_of_change = fields.Selection(string='Type of change', selection=[('change_order', 'Change Order'), 
                                                                          ('amendment', 'Amendment'),
                                                                          ('extension', 'Extension'),
                                                                          ('renewal ', 'Renewal'),
                                                                          ('other ', 'Other')])
    
    portion_of_agreement_affected = fields.Text(string='Portion of agreement affected')
    reason_for_change = fields.Binary(string='Reason for change',track_visibility='onchange')
    contract_ids = fields.One2many(comodel_name='contract.lines', inverse_name='contract_id')
    inherit_po = fields.Many2one(comodel_name='purchase.order')
    state = fields.Selection(string="Status", selection=[('user_department', 'User Department'), 
                                                         ('procurement_manger', 'Procurement manager'),
                                                         ('buyer', 'Buyer'),
                                                         ('managing_director', 'Managing Director'),
                                                         ('changed', 'Changed'),
                                                         ('reject', 'Rejected'),], default='user_department', track_visibility='onchange')
        
    total = fields.Monetary(string='Total', compute='compute_totals')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, )
    contract_duration = fields.Char(string='Contract Duration',)
    start_date = fields.Date(string='Start Date', track_visibility='onchange')
    end_date = fields.Date(string='End Date', track_visibility='onchange')
    description = fields.Text(string='Descriprtion of services')
    terms_and_conditions = fields.Binary(string='Terms and conditions', )
    buyer = fields.Many2one(comodel_name='res.users', string='Assign buyer', track_visibility='onchange')
    contract_status=fields.Char(string='Contract State' )
    scope_work = fields.Text('Scope of work')
    scope_doc = fields.Binary()
    remarks = fields.Text('Remarks And Notes')
    contracts = fields.Many2one(comodel_name='contract.contract')

    
    @api.onchange('contract_number')
    def onchange_contract_number(self):
        if self.contract_number:
            self.vendor_id=self.contract_number.vendor_id
            self.contract_status=self.contract_number.contract_status
            self.scope_work=self.contract_number.scope_work
            self.scope_doc=self.contract_number.scope_doc
            self.remarks=self.contract_number.remarks
            self.start_date=self.contract_number.start_date
            self.end_date=self.contract_number.finish_date
            self.contract_duration=self.contract_number.duration
            # self.buyer=self.contract_number.buyer
            # self.description=self.contract_number.description
            
        
    def button_submit(self):
        for rec in self:
            rec.write({'state': 'procurement_manger'})
    
    def button_to_buyer(self):
        for rec in self:
            rec.write({'state': 'buyer'})
    
    def button_confirm(self):
        for rec in self:
            rec.write({'state': 'managing_director'})
    
    def change(self):
        contract_lines = self.contract_ids.search([('contract_id','=',self.id)])
        self.inherit_po.start_date = self.start_date
        self.inherit_po.partner_id  = self.vendor_id.id
        self.inherit_po.end_date = self.end_date
        for contract in contract_lines:
            lines_to_update = self.inherit_po.order_line.filtered(lambda r:r.product_id.id == contract.product_id.id)            
            for line in lines_to_update:
                line.price_unit = contract.unit_price
                line.product_qty = contract.quantity

    def button_approve(self):
        for rec in self:
            rec.write({'state': 'changed'})
        self.change()
    
    def action_reject(self):
        self.write({'state': 'reject'})
        
    @api.depends('contract_ids.unit_price')
    def compute_totals(self):
        self.ensure_one()
        totals = purchase_total = 0.0
        for line in self.contract_ids:
            totals += line.unit_price * line.quantity
        self.update({'total': totals, })

    
    
        
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'change_contract.sequence') or _('New')
        result = super(ChangeContract, self).create(vals)
        return result
    
class ContractLines(models.Model):
    _name = 'contract.lines'
    
    contract_id = fields.Many2one(comodel_name='change.contract', string='')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    description = fields.Char(string='Description', related='product_id.name')
    quantity = fields.Float(string='Quantity', required=True)
    # unit_price = fields.Monetary(string='Unit Price')
    unit_price = fields.Monetary(string='Unit Price')
    total = fields.Float(string='Total')
    currency_id = fields.Many2one(related='contract_id.currency_id')
    rate = fields.Integer( string='Rate')
