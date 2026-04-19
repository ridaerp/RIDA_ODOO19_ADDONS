from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.tools import float_round
from odoo.exceptions import ValidationError


from datetime import datetime



class InheritStockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'


    state=fields.Selection(selection=[
        ('store_supervisor', 'Store Supervisor'),('store_manager', 'Store Manager'),('site_manager', 'Operation Director'),('done','Done'),
    ],  )
    partner_no=fields.Many2one(comodel_name='res.partner', string='Partner')
    # Product Name
    max_month_cons=fields.Integer(string='Max Consumption Qty per Month')
    min_month_cons=fields.Integer(string='MIN Consumption Qty per Month')
    conumption_rate=fields.Float(compute='_get_computation_rate',string='Conumption Rate',store='True') 
    month_lead_time=fields.Integer(string='Lead Time In Months')
    lead_time_stock=fields.Float(compute='_get_lead_time_stock', string='Lead Time Stock',store='True')
    max_delay=fields.Float(strinng='Max delay')
    safety_stock=fields.Float(compute='_get_safety_stock', string='Safety Stock')
    max_avg=fields.Float(compute='_get_max_average',string='Max Average',store='True')
    ssc=fields.Float(compute='_get_ssc', string='Safty Stock For Consumption')
    tss=fields.Float(compute='_get_tss',string='Total Safty Stock Consumption')
    roundup_tss=fields.Integer(compute='_get_roundup_tss',string='Total Safty Stock Consumption',store='True')
    reorder_level=fields.Integer(comute='_get_reorder_level',string='Re Order Level')
    reorder_stock=fields.Integer(string='Reorder Stock')
    max_stock=fields.Float(compute='_get_max_stock',string='Max Stock',store='True')
    order_qty=fields.Float(compute='_get_order_qty',string='Order Quantity')
    spec_cons=fields.Text(string='Special Considerations')


    
    @api.constrains('max_month_cons','min_month_cons')
    def validate_month_cons(self):
        for rec in self:
            if rec.min_month_cons>rec.max_month_cons:
                raise ValidationError(_("Max Consumption Qty per Month must be grater than min Consumption Qty per Month"))


    @api.depends('max_month_cons','min_month_cons')
    def _get_computation_rate(self):
        for rec in self:
            if rec.max_month_cons and rec.min_month_cons!=0:
                rec.conumption_rate=(rec.max_month_cons+rec.min_month_cons)/2
            else:
                rec.conumption_rate=0
        # print("conumption_rate",rec.conumption_rate)

    @api.depends('conumption_rate','month_lead_time')
    def _get_lead_time_stock(self):
        for rec in self:
            if rec.conumption_rate and rec.month_lead_time:
                rec.lead_time_stock=(rec.conumption_rate+rec.month_lead_time)
            else:
                rec.lead_time_stock=0
            # print("lead_time_stock",rec.lead_time_stock)
        
    @api.depends('conumption_rate','max_delay')
    def _get_safety_stock(self):
        for rec in self:
            if rec.conumption_rate and rec.max_delay!=0:
                rec.safety_stock=(rec.conumption_rate*rec.max_delay)
            else:
                rec.safety_stock=0
            # print("safety_stock",rec.safety_stock)

    @api.depends('max_month_cons','conumption_rate')
    def _get_max_average(self):
        for rec in self:
            if rec.max_month_cons and rec.conumption_rate!=0:
                rec.max_avg=(rec.max_month_cons-rec.conumption_rate)
            else:
                rec.max_avg=0
            # print("max_avg",rec.max_avg)
        
    @api.depends('max_avg','month_lead_time')
    def _get_ssc(self):
        for rec in self:
            if rec.max_avg and rec.month_lead_time!=0:
                rec.ssc=(rec.max_avg*rec.month_lead_time)
            else:
                rec.ssc=0
            # print("ssc",rec.ssc)

    @api.depends('safety_stock','ssc')
    def _get_tss(self):
        for rec in self:
            if rec.safety_stock and rec.ssc:
                rec.tss=(rec.safety_stock+rec.ssc)
            else:
                rec.tss=0
            # print("tss",rec.tss)

    @api.depends('tss')
    def _get_roundup_tss(self):
        for rec in self:
            rec.roundup_tss=float_round(rec.tss, precision_rounding=0.01, rounding_method='UP')
            # print("roundup_tss",rec.roundup_tss)

    @api.depends('lead_time_stock','tss')
    def _get_reorder_level(self):
        for rec in self:
            if rec.lead_time_stock and rec.tss:
                rec.reorder_level=float_round(rec.lead_time_stock+rec.tss, precision_rounding=0.01, rounding_method='UP')
            else:
                rec.reorder_level=0
            # print("reorder_level",rec.reorder_level)

    @api.depends('max_month_cons')
    def _get_max_stock(self):
        for rec in self:
            if rec.max_month_cons !=0:
                rec.max_stock=(rec.max_month_cons*12)
            else:
                rec.max_stock=0
            # print("max_stock",rec.max_stock)

    @api.depends('max_stock','roundup_tss')
    def _get_order_qty(self):
        for rec in self:
            if rec.max_stock and rec.roundup_tss!=0:
                rec.order_qty=(rec.max_stock-rec.roundup_tss)
            else:
                rec.order_qty=0
            # print("oorder_qty",rec.order_qty)
     #Rirda workflow
        #Replenishment workfow
    def action_store_supervisor_approve(self):
        for rec in self:
            rec.write({'state': 'store_manager'})
    def action_store_manager_approve(self):
        for rec in self:
            rec.write({'state': 'site_manager'})
    def action_site_manager_approve(self):
        for rec in self:
            rec.write({'state': 'site_manager'})


