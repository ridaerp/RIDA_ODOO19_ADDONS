# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError

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
