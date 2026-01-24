from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.addons import decimal_precision as dp
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError



class InheritPurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    # contract_refrence = fields.Char(string='Contract Refrence', required=True,
                                    # copy=False, readonly=True, index=True, default=lambda self: _('New'),compute='get_contract_ref')
    pr_type = fields.Selection(string='PR type', selection=[('material', 'Material'), ('service', 'Service')], default='material')
    validity_date = fields.Date(string='Validity Date')
    buyer = fields.Many2one('res.users', string='Buyer')
    deliver_to = fields.Many2one(comodel_name='stock.warehouse', string='Deliver to')
    # source_type = fields.Selection(related='request_id.source_type', string="S")
    state = fields.Selection(selection=[('draft', 'RFQ'),
                                        ('sent', 'RFQ Sent'),
                                        # ('buyer', 'Buyer'),
                                        ('user_department', 'User Department'),
                                        ('contract_sh', 'Contract SH'), 
                                        ('department_manger', 'Department manager'),
                                        ('cost_control', 'Cost Control'),
                                        ('procurement_manger', 'Procurement manager'), 
                                        ('managing_director', 'Managing Director'),
                                        ('purchase', 'Purchase Order'), 
                                        ('cancel', 'cancelled'), 
                                        ('reject', 'Rejectedd')], default='draft')
    tech_specification = fields.Binary(string='Technical evaluation')
    commercial_justification = fields.Text(string='Commercial evaluation')
    vendor_id = fields.Many2one(comodel_name='res.partner', string='Vendor Name')
    total_cost = fields.Float(string='Total Cost')
    or_percentage = fields.Char(string='Total Percentage', compute="set_percentage")
    price = fields.Float(string='Price')
    currency = fields.Monetary(string='Currency')
    comments = fields.Text(string='Technical Comments')
    commercial_comments = fields.Text(string='Comments')
    invisible_fields = fields.Boolean(string='', default=False)
    chk_source = fields.Boolean(string='Source', compute="change_source_document",default=False)
    request_id = fields.Many2one('material.request')
    request_id_line = fields.Many2one('material.request.line')
    buyer_comments = fields.Text(string='Comments')
    depart_manager_comments = fields.Text(string='Comments')
    analytic_account_account = fields.Char(string='Cost center', readonly=True)
    account_id = fields.Many2one(comodel_name='account.budget.department.form')
    procurement_manager_comments = fields.Text(string='Comments')
    managing_director_commecdnts = fields.Text(string='Comments')
    # requester_description = fields.Text(related='request_id.requester_description', string="Parts /  Items Description")
    dm_date = fields.Datetime(string="Approved date")
    # check_user = fields.Boolean(related='request_id.check_user', string="Check")
    check_user = fields.Boolean('Check', compute='get_user')
        # department_id = fields.Many2one(related='request_id.department_id', string="Department")
    department_id = fields.Many2one('hr.department', string="Department")
    # description = fields.Char(related='request_id_line.name',  size=256,string="Parts /Item Description")
    # vendor_id = fields.Many2one(related='request_id.vendor_id', string='Buyer')
    vendor_id = fields.Many2one(comodel_name='res.partner', string='Vendor', related='contract_number.partner_id', readonly=True)
    mr_date = fields.Date(string='MR date')
    po_date = fields.Date(string='PO date')
    pr_date = fields.Date(string='PR date')
    no_of_days = fields.Integer(string='No of days')
    ustomer_type = fields.Selection(string='Vendor type', related='partner_id.partner_custom_type')
    multiple_mr = fields.Many2many(comodel_name='material.request', string="MR's")
    customer_type = fields.Selection([('public', 'Public'), ('private', 'Private'), ('sub', 'Subdistributor')], "Customer Type")
    sole_source = fields.Selection([('technical', 'Technical'), ('standard', 'Standardization'), ('inter', 'Interchangeability'),
                                    ('market', 'Market') , ('replace', 'Replacement')
                                       ,  ('emergency', 'Emergency') ,  ('delivery', 'Best Delivery ') ,
                                    ('client', 'Client Preference'), ('terms', 'Terms'), ('others', 'Others')], "Reasons")

    terms = fields.Text(string='Comments', default='only one supplier / provider can meet our payment / delivery terms.')
    technical = fields.Text(string='Comments', default='There is only one supplier / provider who can meet the technical'
                                               'specifications.')
    standard = fields.Text(string='Comments', default='There is an existing equipment in place and in order to maintain'
                                               'standardization of spare parts / services, we would single source.')
    inter = fields.Text(string='Comments', default='Single sourcing is done to provide us with the flexibility of interchanging like '
                                               'equipment / materials / services.')
    market = fields.Text(string='Comments', default='Due to tight market conditions, only one supplier / provider can provide '
                                               'the goods or services by the on-site date specified or because of the '
                                               'nature of the product and type of market, it is preferable to negotiate'
                                               ' with one supplier / provider.')
    replace = fields.Text(string='Comments', default='A replacement or extension of an existing item / service is required.')
    emergency = fields.Text(string='Comments', default='A true emergency (not a procurement planning deficiency) has occurred '
                                               '(i.e. s  tock-out for maintenance, etc.).')
    delivery = fields.Text(string='Comments', default='as per delivery requirements of user department.')
    client = fields.Text(string='Comments', default='As indicated by Client. ')
    others = fields.Text(string='Comments',  )

    # def __init__(self):
    #     self.percentage= 0
    def get_user(self):
        if self.requested_by.id == self.env.user.id:
            self.check_user = True
        else:
            self.check_user = False

    @api.onchange('requisition_id')
    def change_source_document(self):
        # raise UserError(self.source_type)
        for rec in self:
            rec.origin = rec.requisition_id.origin
            rec.request_id = rec.requisition_id.id



    @api.depends('source_type')
    def change_source_document(self):
        for rec in self:
            if rec.source_type== 'single':
                rec.chk_source = True
            else:
                rec.chk_source = False





    
    def button_submit_to_contract_sh(self):
        for rec in self:
            if rec.pr_type == 'service':
                rec.write({'state': 'contract_sh'})
    
    def button_to_user_department(self):
        for rec in self:
            rec.write({'state': 'user_department'}) 






    def action_back(self):
        for rec in self:
            if self.state == 'sent':
                rec.write({'state': 'draft'})
        if self.state == 'user_department':
            rec.write({'state': 'draft'})
        if self.state == 'contract_sh':
            rec.write({'state': 'user_department'})
        if self.state == 'department_manger':
            rec.write({'state': 'user_department'})
        if self.state == 'cost_control':
            rec.write({'state': 'department_manger'})
        if self.state == 'procurement_manger':
            rec.write({'state': 'cost_control'})
        if self.state == 'managing_director':
            rec.write({'state': 'procurement_manger'})

    def button_to_submit(self):
        for rec in self:
            rec.write({'state': 'department_manger'})

    def button_to_cost_control(self):
        for rec in self:
            rec.write({'state': 'cost_control'})

    def department_approve(self):
        for rec in self:
            rec.write({'state': 'procurement_manger'})
            # self.proc_recipt = fields.Datetime.now()

    def button_to_approve(self):
        # for rec in self:
        for order in self:
            # Deal with double validation process
            if order.company_id.po_double_validation == 'two_step'\
                    and order.amount_total > order.company_id.md_validation_amount:
                # order.button_approve()
                order.write({'state': 'managing_director'})
            else:
                self.write({'state': 'purchase'})

    def button_reject(self):
        for rec in self:
            rec.write({'state': 'reject'})
            
    def button_confirm(self):
        for order in self:
            if order.po_date and order.mr_date:
                order.po_date = fields.datetime.today()
                order.no_of_days = (order.po_date - order.mr_date).timedelta(days)
                order.no_of_days_sr = (order.po_date - order.sr_date).timedelta(days)
            if order.state not in ['draft', 'sent','managing_director']:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.po_double_validation == 'one_step'\
                    or (order.company_id.po_double_validation == 'two_step'\
                        and order.amount_total < self.env.company.currency_id._convert(
                            order.company_id.po_double_validation_amount, order.currency_id, order.company_id, order.date_order or fields.Date.today()))\
                    or order.user_has_groups('purchase.group_purchase_manager'):
                order.button_approve()

            else:
                order.write({'state': 'to approve'})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return True

    def button_confirming(self):
        self.write({'state': 'purchase'})
        # self.order_issue = fields.Datetime.now()
        # self.compute_contract_status()
        res = super(InheritPurchaseOrder,self).button_confirm()
        return res


    def action_create_invoice(self): 
        self.pr_date = fields.Datetime.now()
        res = super(InheritPurchaseOrder,self).action_create_invoice()
        return res

    
    def button_rfq_send(self):
        for rec in self:
            res = super(InheritPurchaseOrder,self).action_rfq_send()
            rec.write({'state': 'user_department'})
        return res
    
    def button_to_user(self):
        for rec in self:
            if rec.pr_type == 'material':
                rec.write({'state': 'user_department'})
    
    def make_invisible(self):
        self.invisible_fields = True

    @api.depends('amount_total','invoice_ids.amount_residual',)
    def set_percentage(self):
        for record in self:

            if record.invoice_ids:

                for rec in record.invoice_ids:
                    # raise UserError(record.amount_total - rec.amount_residual)
                    # if rec.amount_residual:
                    part = (record.amount_total - rec.amount_residual)

                    percentage= 100 * (part / record.amount_total)
                    # raise UserError(str(percentage) + "%")
                    record.or_percentage= str(percentage) + "%"
            else:
                # raise UserError("there")
                record.or_percentage = ""

    # def percentage(part, whole):
    #     percentage = 100 * float(part) / float(whole)
    #     return str(percentage) + "%"
    #
    # print(percentage(3, 5))