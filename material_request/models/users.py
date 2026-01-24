# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError


class User(models.Model):
    _inherit = "res.users"

    fleet = fields.Boolean('Fleet')

    ######################add code by ekhlas ######################################

    line_manager_id = fields.Many2one('res.users', string="Line Manager",
                                      default=lambda self: self.env.user.employee_id.line_manager_id)

    line_line_manager_id = fields.Many2one('res.users', string="Line Line Manager",
                                           default=lambda self: self.env.user.employee_id.line_line_manager_id)
    analytic_account_ids = fields.Many2many('account.analytic.account', string="Analytic Account")
    default_analytic_account_id = fields.Many2one('account.analytic.account', string='Default Analytic Account',
                                                  readonly=0, compute='_compute_related_field', store=True,
                                                  domain="[('id', 'in', analytic_account_ids)]")
    product_category_ids = fields.Many2many('product.category', string="Product Categories")
    default_product_category_id = fields.Many2one('product.category', string='Default Product Category',
                                                  readonly=0, compute='_compute_category_field', store=True,
                                                  domain="[('id', 'in', product_category_ids)]")

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


class ResPartner(models.Model):
    _inherit = "res.partner"

    max_grade = fields.Float(
        string="Max Grade for 0 Transportatin Cost (0)",
        digits="Discount",
        tracking=True,
    )

    # is_employee = fields.Boolean(
    #     string="Is Employee",
    #     compute="_compute_is_employee",
    #     store=True
    # )

    # @api.depends('employee_ids')
    # def _compute_is_employee(self):
    #     for partner in self:
    #         # employee_ids comes from One2many via work_contact_id
    #         partner.is_employee = bool(partner.employee_ids)


    # partner_type = fields.Selection(
    #     selection=[
    #         ('local', 'Local'),
    #         ('overseas', 'Overseas'),
    #     ],
    #     string='Partner Type',
    #     default="overseas",
    #     required=True,
    # )
