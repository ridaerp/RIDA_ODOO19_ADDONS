from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

ACCOUNT_DOMAIN = "[('active', '=', False), ('internal_type','=','other'), ('company_id', '=', current_company_id), ('is_off_balance', '=', False)]"


class RequestProductCategoty(models.Model):
    _name = 'request.product.categoty'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Product Category  Request'

    code_seq = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True,
                             readonly=True)
    department_id = fields.Many2one('hr.department', string="Department", readonly=True, store=True)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    state = fields.Selection(
        [('draft', 'Draft'), ('w_adv', 'Waiting Account Advisor'),
         ('md', 'Waiting Master Admin'),
         ('reject', 'reject'), ('done', 'Done')],
        string='Status', default='draft', track_visibility='onchange', copy=False)
    date = fields.Date(default=fields.Date.today(), readonly=True)

    name = fields.Char('Name', index=True, )
    # parent_id = fields.Many2one('product.category', 'Parent Category', index=True, ondelete='cascade')
    product_category_id = fields.Many2one('product.category', 'Parent Category', index=True, ondelete='cascade')
    property_valuation = fields.Selection([
        ('manual_periodic', 'Manual'),
        ('real_time', 'Automated')], string='Inventory Valuation',
        company_dependent=True, copy=True, default='manual_periodic',
        help="""Manual: The accounting entries to value the inventory are not posted automatically.
        Automated: An accounting entry is automatically created to value the inventory when a product enters or leaves the company.
        """)
    property_cost_method = fields.Selection([
        ('standard', 'Standard Price'),
        ('fifo', 'First In First Out (FIFO)'),
        ('average', 'Average Cost (AVCO)')
        ,('last', 'Last Purchase Price')], string="Costing Method",
        company_dependent=True, copy=True,
        help="""Standard Price: The products are valued at their standard cost defined on the product.
        Average Cost (AVCO): The products are valued at weighted average cost.
        First In First Out (FIFO): The products are valued supposing those that enter the company first will also leave it first.
        """)
    property_stock_account_input_categ_id = fields.Many2one(
        'account.account', 'Stock Input Account', company_dependent=True,
        domain="[('company_ids', '=', allowed_company_ids[0]), ('active', '=', False)]", check_company=True,
        help="""Counterpart journal items for all incoming stock moves will be posted in this account, unless there is a specific valuation account
                set on the source location. This is the default value for all products in this category. It can also directly be set on each product.""")
    property_stock_account_output_categ_id = fields.Many2one(
        'account.account', 'Stock Output Account', company_dependent=True,
        domain="[('company_ids', '=', allowed_company_ids[0]), ('active', '=', False)]", check_company=True,
        help="""When doing automated inventory valuation, counterpart journal items for all outgoing stock moves will be posted in this account,
                unless there is a specific valuation account set on the destination location. This is the default value for all products in this category.
                It can also directly be set on each product.""")
    property_stock_valuation_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account', company_dependent=True,
        domain="[('company_ids', '=', allowed_company_ids[0]), ('active', '=', False)]", check_company=True,
        help="""When automated inventory valuation is enabled on a product, this account will hold the current value of the products.""", )
    property_stock_journal = fields.Many2one(
        'account.journal', 'Stock Journal', company_dependent=True,
        domain="[('company_id', '=', allowed_company_ids[0])]", check_company=True,
        help="When doing automated inventory valuation, this is the Accounting Journal in which entries will be automatically posted when stock moves are processed.")
    property_account_income_categ_id = fields.Many2one('account.account', company_dependent=True,
                                                       string="Income Account",
                                                       domain=ACCOUNT_DOMAIN,
                                                       help="This account will be used when validating a customer invoice.")
    property_account_expense_categ_id = fields.Many2one('account.account', company_dependent=True,
                                                        string="Expense Account",
                                                        domain=ACCOUNT_DOMAIN,
                                                        help="The expense is accounted for when a vendor bill is validated, except in anglo-saxon accounting with perpetual inventory valuation in which case the expense (Cost of Goods Sold account) is recognized at the customer invoice validation.")
    property_account_creditor_price_difference_categ = fields.Many2one(
        'account.account', string="Price Difference Account",
        company_dependent=True,
        help="This account will be used to value price difference between purchase price and accounting cost.")
    new_pr_cat = fields.Many2one("product.category", string='Product Category', readonly=1, copy=False)


    def _track_subtype(self, init_values):
        self.ensure_one()
        if self.state=='done':
            return self.env.ref('master_data.product_categoty_status')
        if self.state=='reject':
            return self.env.ref('master_data.product_categoty_rej_status')
        return super(RequestProductCategoty, self)._track_subtype(init_values)

    def activity_update(self):
        for rec in self:
            users = []
            message = ""
            if rec.state == 'w_adv':
                users = self.env.ref('base_rida.rida_group_master_data_manager').user_ids
                message = "Please Create the Product Category"
                for user in users:
                    self.activity_schedule('master_data.mail_act_master_data_approval', user_id=user.id, note=message)
            else:
                continue


    @api.model
    def create(self, vals):
        for val in vals:
            val['code_seq'] = self.env['ir.sequence'].next_by_code('prod.cat.request') or ' '

        return super(RequestProductCategoty, self).create(vals)


    @api.onchange('categ_id')
    def _categ_id(self):
        for rec in self:
            rec.property_cost_method=rec.product_category_id.property_cost_method
            rec.property_valuation=rec.product_category_id.property_valuation
            rec.property_account_creditor_price_difference_categ=rec.product_category_id.property_account_creditor_price_difference_categ.id
            rec.property_account_income_categ_id=rec.product_category_id.property_account_income_categ_id.id
            rec.property_stock_journal=rec.product_category_id.property_stock_journal.id
            rec.property_account_expense_categ_id=rec.product_category_id.property_account_expense_categ_id.id
            rec.property_stock_valuation_account_id=rec.product_category_id.property_stock_valuation_account_id.id




    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")

        return super(RequestProductCategoty, self).unlink()

    def set_confirm(self):
        self.property_valuation = 'real_time'
        return self.write({'state': 'w_adv'})

    def set_advisor_confirm(self):
        self.activity_update()
        return self.write({'state': 'md'})

    def create_product_category(self):
        self.new_pr_cat = self.env["product.category"].create({
            'name': self.name,
            'parent_id': self.product_category_id.id,
            'property_cost_method': self.property_cost_method,
            'property_valuation': self.property_valuation,
            'property_account_income_categ_id': self.property_account_income_categ_id.id,
            'property_account_expense_categ_id': self.property_account_expense_categ_id.id,
            'property_stock_valuation_account_id': self.property_stock_valuation_account_id.id,
            'property_stock_journal': self.property_stock_journal.id,
        })
        return self.write({'state': 'done'})
