

from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    line_manager_id = fields.Many2one(comodel_name='res.users', string='Line Manager')
    line_line_manager_id = fields.Many2one(comodel_name='res.users', string='Line Line Manager')
    rida_employee_type = fields.Selection(string='Employee type', selection=[('hq', 'HQ Staff'), ('site', 'Site Staff')], required=True)
    bank_account_id = fields.Many2one("res.partner.bank")

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    bank_account_id = fields.Many2one("res.partner.bank")

class User(models.Model):
    _inherit = "res.users"

    user_type = fields.Selection(string='User type', selection=[('hq', 'Corporate Service'),
     ('site', 'Operation'),('fleet','Fleet'),('rohax','Rohax')],required=False,default="hq")
    fleet = fields.Boolean('Fleet')
    line_manager_id = fields.Many2one('res.users', string="Line Manager", default=lambda self: self.env.user.employee_id.line_manager_id)
    line_line_manager_id = fields.Many2one('res.users', string="Line Line Manager", default=lambda self: self.env.user.employee_id.line_line_manager_id)
    analytic_account_ids = fields.Many2many('account.analytic.account', string="Analytic Account")
    default_analytic_account_id = fields.Many2one('account.analytic.account', string='Default Analytic Account', readonly=0, compute='_compute_related_field', store=True,  domain="[('id', 'in', analytic_account_ids)]")
    product_category_ids = fields.Many2many('product.category', string="Product Categories")
    default_product_category_id = fields.Many2one('product.category', string='Default Product Category', readonly=0, compute='_compute_category_field', store=True, domain="[('id', 'in', product_category_ids)]")
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')

    @api.depends('default_analytic_account_id')
    def _compute_related_field(self):
        for record in self:
            if record.analytic_account_ids:
                record.default_analytic_account_id = record.analytic_account_ids[0]
            else:
                record.default_analytic_account_id = False

    @api.depends('default_product_category_id')
    def _compute_category_field(self):
        for record in self:
            if record.product_category_ids:
                record.default_product_category_id = record.product_category_ids[0]
            else:
                record.default_product_category_id = False


class InheritCompany(models.Model):
    _inherit = 'res.company'

    maximum_contract_amount = fields.Integer(string='maximum contract amount')

class ESMConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    maximum_contract_amount = fields.Integer(related='company_id.maximum_contract_amount',string='maximum contract amount', readonly=False)
