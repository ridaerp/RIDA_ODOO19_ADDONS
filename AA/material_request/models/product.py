from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplete(models.Model):
    _inherit = "product.template"

    @api.model
    def default_get(self, fields):
        res = super(ProductTemplete, self).default_get(fields)
        if res.get('type', False):
            if res.get('type') == 'product':
                res.update({
                    'purchase_method': 'receive',
                })
        return res

    product_type = fields.Selection(
        [('stackable', 'Stackable'), ('asset', 'Asset (non -Stackable )')],
        string="PR Product type")
    part_number = fields.Char('Part Number')
    self_deportation = fields.Boolean("Self Deportation")
    custom_sequence = fields.Char(string="Sequence")
    custom_analytic_account_id = fields.Many2one("account.analytic.account",
                                          string="Analytic Account", )
    default_code = fields.Char(
        'Item Code', compute='_compute_default_code',
        inverse='_set_default_code', store=True)

    ########################comment by ekhlas#########################
    # part_number = fields.Char('Part Number', store=True)

    brand = fields.Char('Brand')
    model = fields.Char('Model')

    ########################ekhlas code #########################

    purchase_contract = fields.Selection(
        [('rfq', 'Create a draft purchase order'),
         ('tenders', 'Propose a call for tenders')],
        string='Procurement', default='rfq',
        help="Create a draft purchase order: Based on your product configuration, the system will create a draft "
             "purchase order.Propose a call for tender : If the 'purchase_contract' module is installed and this option "
             "is selected, the system will create a draft call for tender.")


    standard_price = fields.Float(
        'Cost', compute='_compute_standard_price',tracking=True,
        inverse='_set_standard_price', search='_search_standard_price',
        digits='Product Price', groups="base.group_user",
        help="""Value of the product (automatically computed in AVCO).
        Used to value the product when the purchase cost is not known (e.g. inventory adjustment).
        Used to compute margins on sale orders.""")

    _sql_constraints = [
        ('unique_custom_sequence', 'unique(custom_sequence)', 'The sequence must be unique!')
    ]

    is_profit_percentage=fields.Boolean("Profit %")
    is_company_percentage=fields.Boolean("Company share %")
    custom_sequence = fields.Char(string="Sequence")
    custom_analytic_account_id = fields.Many2one("account.analytic.account",
                                          string="Analytic Account", )



    _sql_constraints = [
        ('unique_custom_sequence', 'unique(custom_sequence)', 'The sequence must be unique!')
    ]



    @api.onchange("type")
    def _change_type_product(self):
        for item in self:
            if item.type == 'product':
                item.purchase_method = 'receive'



    ###############ekhlas code ###########
    ################fuction to validate duplicate item code 

    @api.constrains('default_code')
    def _check_name(self):
        for rec in self:
            product_no = self.env['product.template'].search([('default_code', '!=', False)])
            product_ids = product_no.search([('default_code', '=', rec.default_code), ('id', '!=', rec.id)])
            for rec in product_ids:
                if rec.default_code != False:
                    raise ValidationError(_('Exists ! The code already exists, please check the Coding Structure'))




class Product(models.Model):
    _inherit = "product.product"


    @api.model
    def default_get(self, fields):
        res = super(Product, self).default_get(fields)
        if res.get('type', False):
            if res.get('type') == 'product':
                res.update({
                    'purchase_method': 'receive',
                })
        return res

    standard_price = fields.Float(
        'Cost', company_dependent=True,tracking=True,
        digits='Product Price',
        groups="base.group_user",
        help="""Value of the product (automatically computed in AVCO).
        Used to value the product when the purchase cost is not known (e.g. inventory adjustment).
        Used to compute margins on sale orders.""")



    warehouse_quantity = fields.Float(compute='_get_warehouse_quantity', string='Quantity per warehouse')
    is_profit_percentage=fields.Boolean("Profit %")
    custom_sequence = fields.Char(string="Sequence")
    custom_analytic_account_id = fields.Many2one("account.analytic.account",string="Analytic Account", )

    last_delivery_date = fields.Datetime(
        string='Last Delivery Date',
        compute='_compute_last_delivery_date',
        store=False 
    )

    @api.depends('stock_move_ids')
    def _compute_last_delivery_date(self):
        for product in self:
            # (Delivery Orders
            move = self.env['stock.move'].search([
                ('product_id', '=', product.id),
                ('picking_type_id.code', '=', 'outgoing'),
                ('state', '=', 'done'),
            ], order='date desc', limit=1)

            product.last_delivery_date = move.date if move else False




    _sql_constraints = [
        ('unique_custom_sequence', 'unique(custom_sequence)', 'The sequence must be unique!')
    ]

    
    ########################comment by ekhlas#########################
    # part_number = fields.Char('Part Number', store=True)
    ###########################################

    # old code comment by ekhlas # @api.one
    # def _get_warehouse_quantity(self):
    #     qty_on_hand = 0
    #     quant_ids = self.env['stock.quant'].sudo().search([
    #         ('product_id', '=', self.id),
    #         ('location_id.usage', '=', 'internal')
    #     ])
    #     qty_on_hand = sum(line.quantity - line.reserved_quantity for line in quant_ids)
    #     self.warehouse_quantity = qty_on_hand

    # @api.one
    def _get_warehouse_quantity(self):
        qty_on_hand = 0
        for rec in self:
            quant_ids = self.env['stock.quant'].search([
                ('product_id', '=', rec.id),
                ('location_id.usage', '=', 'internal')
            ])
        qty_on_hand = sum(line.quantity - line.reserved_quantity for line in quant_ids)
        self.warehouse_quantity = qty_on_hand

    ############################ekhlas code ##############################################
    #####################from purchase requiestion 
    def _prepare_sellers(self, params=False):
        sellers = super(Product, self)._prepare_sellers(params=params)
        if params and params.get('order_id'):
            return sellers.filtered(
                lambda s: not s.purchase_contract_id or s.purchase_contract_id == params['order_id'].contract_id)
        else:
            return sellers

    @api.onchange('type')
    def _change_type(self):
        for rec in self:
            if rec.type == 'product':
                rec.purchase_method = 'receive'
                print('>>>>>>>>>>>', rec.purchase_method)

    # @api.constrains('default_code')
    # def check_duplicate_code(self):
    #     product = False
    #     if self.default_code:
    #         product = self.search([('default_code', '=', self.default_code), ('id', '!=', self.id)], limit=1)
    #         if product:
    #             raise ValidationError("Internal Reference must be unique!")

    # @api.model
    # def create(self, vals):
    # res = super(Product, self).create(vals)
    # if res.default_code:
    #   return res
    # type = "CO"
    # if res.type == 'product':
    #   type = "ST"
    # elif res.type == 'service':
    #   type = "SE"
    # elif res.can_be_expensed:
    #   type = "EX"

    # category_id = res.categ_id
    # if not category_id.code:
    #   return res
    # code = type + category_id.display_code
    # next_code = str(category_id.next_code)
    # code += str(next_code.zfill(3))
    # res.default_code = code
    # category_id.next_code += 1
    # return res


#############################comment by ekhlas ###########################
# class ProductTemplate(models.Model):
#     _inherit = "product.template"


#     default_code = fields.Char(
#         'Item Code', compute='_compute_default_code',
#         inverse='_set_default_code', store=True)
#     part_number = fields.Char('Part Number', store=True)
#     brand = fields.Char('Brand')
#     model = fields.Char('Model')

##########################################################################


########################ekhlas code #########################
class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    purchase_contract_id = fields.Many2one('purchase.contract', related='purchase_contract_line_id.contract_id',
                                           string='Agreement', readonly=False)
    purchase_contract_line_id = fields.Many2one('purchase.contract.line')
