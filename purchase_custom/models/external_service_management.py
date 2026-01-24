from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime
from odoo.exceptions import  ValidationError
import logging
_logger = logging.getLogger(__name__)

class external_service_management(models.Model):
    _name = 'external.service.management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'External Service Management'
    
    name = fields.Char('Reference', required=True, index=True, copy=False, default='New')
    requested_by = fields.Many2one('res.users', 'Requested by', track_visibility='onchange', default=lambda self: self.get_requested_by(), store=True, readonly=True)
    date = fields.Date(string='Date', default=datetime.today())
    department_id = fields.Many2one('hr.department', string='Department', default=lambda self: self._get_default_department())
    vendor_id = fields.Many2one(comodel_name='res.partner', string='Vendor', related='contract_number.partner_id', readonly=True)
    contract_number = fields.Many2one('purchase.order', string='Contract Number')
    job_description = fields.Text(string='Job Description')
    estimated_cost = fields.Float(string='Estimated Cost', related='work_ids.estimated_cost')
    duration = fields.Char(string='Contract Duration' , compute='compute_contract_duration')
    start_date = fields.Date(string='Start Date')
    finish_date = fields.Date(string='Finish Date')
    # state = fields.Selection(string='Status', selection=[('draft', 'Draft'), ('department_manger', 'Department Manager'),
    #                                                     ('approved', 'Approved'),
    #                                                     ('reject', 'Rejected')],default='draft')
    state = fields.Selection(string='Status', selection=[('draft', 'Draft'), ('waiting', 'Waiting For Approval'),
                                                        ('approved', 'Approved'),
                                                        ('reject', 'Rejected')],default='draft')
    inherit_po = fields.Many2one(comodel_name='purchase.order')
    attatchment = fields.Binary(string='Attatchment')
    work_ids = fields.One2many(comodel_name='external.service.management.lines', inverse_name='work_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, )
    pr_type = fields.Selection(string='Pr type', selection=[('material', 'Material'), ('service', 'Service'),], default='service')
    source_document = fields.Char(string='Source Document')
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.company)
    #Lgistic purchase_custom fields
    # logistic = fields.Boolean(string='Logistic', default=False)
    # number_of_loads = fields.Integer(string='No. of loads')
    # estimated_distance = fields.Float(string='Estimated Distance')
    # service_type = fields.Selection(string='Service Type', selection=[('transportation', 'Transportation'), 
    #                                                                   ('backload', 'Backload'),
    #                                                                   ('custom_clearance', 'Custom Clearance'),
    #                                                                   ('rig_move', 'Rig Move')])
    # current_location = fields.Many2one(comodel_name='stock.location', string='Current Location', related='company_id.current_location', store=True, readonly=False)
    # new_location = fields.Many2one(comodel_name='stock.location', string='New Location', related='company_id.new_location', store=True, readonly=False)
    # collection_point = fields.Many2one(comodel_name='stock.location', string='Collection point', related='company_id.collection_point', store=True, readonly=False)
    # release_date = fields.Date(string='Release Date')
    # collection_mobile_number = fields.Float(string='Collection person Mobile Number')
    # delivery_mobile_number = fields.Float(string='Delivery person Mobile Number')
    # scope = fields.Text(string='Scope')
    # logistic_attatchment = fields.Binary(string='Attatchment')
    # delivery_point = fields.Many2one(comodel_name='stock.location', string='Delivery point', related='company_id.delivery_point', store=True, readonly=False)    
    invoice_count = fields.Integer(string="Count", compute='compute_invoice_count')
    store_invoice = fields.Many2one(comodel_name='account.move')
    original_contract_sum = fields.Monetary(string='Original contract sum')
    this_claim = fields.Float(string='This clame')
    address = fields.Char(string='Address')
    fax_number = fields.Integer(string='Fax number')
    telephone_number = fields.Char(string='Telephone No.')
    email = fields.Char(string='Email')
    # clicked = fields.Boolean(string='', default=False)
    inherit_logistic = fields.Many2one(comodel_name='logistics.logistics')
    #rida new fields
    location_type= fields.Many2one(comodel_name='stock.location')
    project_no = fields.Integer(string='Project No')
    company_signatory =fields.Char(string='Company Signatory')
    company_signatory_title=fields.Char(string='Company Signatory Title')
    contract_amount =  fields.Integer(string='Contract Amount')
    contract_type =  fields.Selection(string='Contract Type', selection=[('corporate','Corporate'),('operation','Operation')], readonly=True, compute='get_contract_type')
    t_c = fields.Text(string='Terms and Conditions')
    t_c_attatchment = fields.Binary(string='Terms & conditions Attatchment')
    # state = fields.Selection(string='Status', selection=[('draft', 'Draft'), ('supply_chain_specific', 'Supply Chain Specific'),('supply_chain_director', 'Supply Chain Director'),
    #                                                     ('contract_specialist', 'Contract Specialist'),('purchase_manager', 'Purchase Manager'),('supply_chain_manager', 'Supply Chain Manager'),('general_manager', 'Grneral Manager'),
    #                                                     ('approved', 'Approved'),
    #                                                     ('reject', 'Rejected')],default='draft')
    corporate_states = fields.Selection( selection=[ ('draft', 'Draft'),('supply_chain_specific', 'Supply Chain Specific'),('supply_chain_director', 'Supply Chain Director')],default='draft')
    operation_states = fields.Selection( selection=[('draft', 'Draft'),  ('contract_specialist', 'Contract Specialist'),('purchase_manager', 'Purchase Manager'),('supply_chain_manager', 'Supply Chain Manager'),('general_manager', 'Grneral Manager')],default='draft')
    message_main_attachment_id = fields.Many2one(groups="hr.group_hr_user")
 
    @api.constrains( 'start_date', 'finish_date')
    def _check_dates(self):
        for date in self:
            if  date.finish_date < date.start_date:
                raise ValidationError('The finishing date cannot be earlier than the starting date .') 
    
    def compute_contract_duration(self):
        self.duration=self.finish_date-self.start_date

    def compute_invoice_count(self):
        self.ensure_one()
        self.invoice_count = self.env['account.move'].search_count([('wo_account_id', '=', self.id)])

    @api.depends('contract_amount')
    def get_contract_type(self):
        self.ensure_one()
        if self.contract_amount < self.company_id.maximum_contract_amount:
            self.contract_type = 'operation'
        else:
            self.contract_type = 'corporate'
    
    
    def button_create_invoice(self):
        # self.clicked = True
        create_invoice = {
            'partner_id':self.vendor_id,
            'wo_account_id': self.id,
            'move_type': 'in_invoice',
            'payment_reference': self.name,
            'original_contract_sum': self.original_contract_sum,
            'this_claim': self.this_claim,
            'address': self.address,
            'fax_number': self.fax_number,
            'telephone_number': self.telephone_number,
            'email': self.email,
            
            }
        invoice = self.env['account.move'].create(create_invoice)
        self.store_invoice = invoice.id

        for line in self.work_ids:
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
        return{
            'name': "Bills",
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('wo_account_id', '=', self.id)],
        }
    
    # def button_confirm(self):
    #     for rec in self:
    #         rec.write({'state': 'department_manger'})
    
    # def button_approve(self):
    #     for rec in self:
    #         rec.write({'state': 'approved'})
    


    #Rirda workflow
        #croporate workfow
    def button_supplychain_specific(self):
        for rec in self:
            rec.write({'state': 'waiting'})
            rec.write({'corporate_states': 'supply_chain_specific'})
    def button_supplychain_director_approve(self):
        for rec in self:
            rec.write({'state': 'approved'})
            rec.write({'corporate_states': 'supply_chain_director'})

        #operation workfow
    def button_contract_specialist(self):
        for rec in self:
            rec.write({'state': 'waiting'})
            rec.write({'operation_states': 'contract_specialist'})
    def button_purchase_manager(self):
        for rec in self:
            rec.write({'operation_states': 'purchase_manager'})
    def button_supply_chain_manager(self):
        for rec in self:
            rec.write({'operation_states': 'supply_chain_manager'})
    def button_general_manager_approve(self):
        for rec in self:
            rec.write({'state': 'approved'})
            rec.write({'operation_states': 'general_manager'})
    
    
    def get_requested_by(self):
        user = self.env.user.id
        return user
    
    def _get_default_department(self):
        return self.env.user.department_id.id if self.env.user.department_id else False
    
    def action_reject(self):
        self.write({'state': 'reject'})
        
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('external_service_management.sequence') or _('New')
        result = super(external_service_management, self).create(vals)
        return result
   
   
    # def _send_reminder_mail(self, send_single=False):
    @api.model
    def _send_reminder_mail(self):
    #     if not self.user_has_groups('purchase.group_send_reminder'):
    #         return
        # _logger.info("@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@ " )
        template = self.env.ref('purchase_custom.email_template_purchase_custom_contract_reminder', raise_if_not_found=False)
        # _logger.info("@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@ "+str(template) )

        orders = self.env['external.service.management'].search([])
        _logger.info("@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@   self    "+str(orders.finish_date) )
        if template:
            # orders = self if send_single else self._get_orders_to_remind()
            for order in self.env['external.service.management'].search(['finish_date','=',datetime.today().date()]):
                _logger.info("@#@#@#@#@#@#@#@#@#@#@#@#@#@#@   order   "+str(order.finish_date) )
                date = order.finish_date
                _logger.info("@#@#@#@#@#@#@#@#@#@#@#@#@#@#@   date   "+str(date) )
                _logger.info("@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@  today   "+str(datetime.today().date()) )
                if date == datetime.today().date():
                        order.message_post_with_template(template.id, email_layout_xmlid="mail.mail_notification_paynow", composition_mode='comment')
                        _logger.info("@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@send " )

    # @api.model
    # def _get_orders_to_remind(self):
    #     """When auto sending a reminder mail, only send for unconfirmed purchase
    #     order and not all products are service."""
    #     return self.search([
    #         ('receipt_reminder_email', '=', True),
    #         ('state', 'in', ['purchase', 'done']),
    #         ('mail_reminder_confirmed', '=', False)
    #     ]).filtered(lambda p: p.mapped('order_line.product_id.product_tmpl_id.type') != ['service'])

    
class external_service_managementLine(models.Model):
    _name = 'external.service.management.lines'
    
    work_id = fields.Many2one(comodel_name='external.service.management')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', related='work_id.contract_number.order_line.product_id', required=True)
    description = fields.Char(string='Description', related='product_id.name')
    quantity = fields.Float(string='Quantity', related='work_id.contract_number.order_line.product_qty', required=True)
    unit_price = fields.Monetary(string='Price subtotal', related='work_id.contract_number.order_line.price_subtotal')
    total = fields.Monetary(string='Total',related='work_id.contract_number.order_line.price_total')
    currency_id = fields.Many2one(related='work_id.currency_id')  
    estimated_cost = fields.Float('Estimated Cost', related='work_id.contract_number.order_line.price_unit')
    account_id = fields.Many2one(comodel_name='account.move', string="Account")
    # analytic_account_account = fields.Many2one(string='Cost center', related="work_id.department_id.analytic_account_id", readonly=True)
    analytic_account_account = fields.Many2one(string='Cost center', readonly=True)
    
    

class Company(models.Model):
    _inherit = 'res.company'
    current_location = fields.Many2one(comodel_name='stock.location', string='Current Location', store=True)
    new_location = fields.Many2one(comodel_name='stock.location', string='New Location', store=True)
    collection_point = fields.Many2one(comodel_name='stock.location', string='Collection point', store=True)
    delivery_point = fields.Many2one(comodel_name='stock.location', string='Delivery point', store=True)
    #rida configuration field
    maximum_contract_amount = fields.Integer(string='maximum contract amount', store='True')

    

class ESMConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    maximum_contract_amount = fields.Integer(related='company_id.maximum_contract_amount',string='maximum contract amount', readonly=False)

# class InheritCompany(models.Model):
#     _inherit = 'res.company'

#     maximum_contract_amount = fields.Integer(string='maximum contract amount')
