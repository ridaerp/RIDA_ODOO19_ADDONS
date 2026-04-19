# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class CompletionCertificate(models.Model):
    _name = "completion.certificate"
    _description = "Certificate of Completion"
    _order = "id desc"

    name = fields.Char(string="Reference", default=lambda self: self.env['ir.sequence'].next_by_code('completion.certificate') or '/', copy=False)
    date = fields.Date(string="Date", default=fields.Date.context_today, required=True)
    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="purchase_order_id.company_id", store=True)
    partner_id = fields.Many2one(related="purchase_order_id.partner_id", store=True , string="Vendor")

    description = fields.Text(string="Description of Works")
    duration_from = fields.Date(string="Execution Duration From")
    duration_to = fields.Date(string="To")
    total_cost = fields.Monetary(string="Total Cost", currency_field="currency_id")
    currency_id = fields.Many2one(related="purchase_order_id.currency_id", store=True)
    materials = fields.Text(string="Materials & Spares")
    contractor_name = fields.Char(string="Contractor Name")
    phone = fields.Char(string="Phone")
    remarks = fields.Text(string="Supervisor Remarks")

    approver_id = fields.Many2one('res.users', string="Approved By", readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Line Manger Approved'),
    ], default='draft', string="State", tracking=True)

    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'
            rec.approver_id = self.env.user
            # Auto mark PO as service_done
            if rec.purchase_order_id:
                rec.purchase_order_id.action_mark_service_done()
