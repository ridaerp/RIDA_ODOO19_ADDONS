from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date, timedelta, datetime
from odoo.exceptions import UserError


class LowestPriceEvaluation(models.Model):
    _name = 'lowest.price.evaluation'
    _description = 'Commercial Evaluation'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'name'


    @api.model
    def default_get(self, fields):
        res = super(LowestPriceEvaluation, self).default_get(fields)

        # Prepare the lines for the evaluation
        line_values = []

        line_values.append({
            'supplier': '<b>Supplier 1</b>',
            'display_type': 'line_section',  # This marks it as a section
            'order_of_supplier': 'a',  # This marks it as a section
        })
        line_values.append({
            'supplier': '<b>Supplier 2</b>',
            'display_type': 'line_section',  # This marks it as a section
            'order_of_supplier': 'b',  # This marks it as a section
        })
        line_values.append({
            'supplier': '<b>Supplier 3</b>',
            'display_type': 'line_section',  # This marks it as a section
            'order_of_supplier': 'c',  # This marks it as a section
        })

        score_ids = self.env['lowest.price.evaluation.line'].create(line_values)
        res.update({
            'score_ids': score_ids
        })
        return res

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Evaluation Prepared', default=lambda self: self.env.user,
                             tracking=True)
    material_request_id = fields.Many2one('material.request', 'Material Request')
    title = fields.Char(related='material_request_id.title', string='MR/SR Description:')
    date_request = fields.Datetime("Evaluation Date", default=fields.Datetime.now, required=True)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    state = fields.Selection(
        [('draft', 'Draft'),
         ('w_proc_manager', 'Waiting Procurement Manager'),
         ('reject', 'reject'),
         ('approved', 'Approved')],
        string='Status', default='draft', track_visibility='onchange')
    a_supplier_id = fields.Many2one('res.partner', string="Supplier A")
    b_supplier_id = fields.Many2one('res.partner', string="Supplier B")
    c_supplier_id = fields.Many2one('res.partner', string="Supplier C")
    comment = fields.Text(string="Additional Comments", required=False, )
    awarded_supplier = fields.Text(string="Awarded Supplier:", required=False, )
    award_supplier = fields.Many2one("res.partner", domain="[('id', 'in', [a_supplier_id, b_supplier_id, c_supplier_id])]",string="Awarded Supplier:", required=False, )
    score_ids = fields.One2many('lowest.price.evaluation.line', 'supplier_id', string='Scores')
    purchase_count = fields.Integer(string="Count", compute='compute_purchase_count')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id)


    def compute_purchase_count(self):
        self.purchase_count = self.env['purchase.order'].search_count(
            [('request_id', '=', self.material_request_id.id)])

    def action_view_purchase_order(self):
        return {
            'name': "RFQ/ Order",
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_id': False,
            'view_mode': 'list,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('request_id', '=', self.material_request_id.id)],
        }

    def action_w_proc_exective(self):
        return self.write({'state': 'w_proc_manager'})

    def action_w_proc_manager(self):
        if self.material_request_id:
            self.material_request_id.sudo().write({'state': 'waiting_po'})

        return self.write({'state': 'approved'})

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry ! only draft records can be deleted!")
        return super(LowestPriceEvaluation, self).unlink()

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('lowest.price.evaluation') or ' '
            res = super(LowestPriceEvaluation, self).create(vals)
            res.fill_prices_from_rfq()
        return res


    def action_draft(self):
        for rec in self.score_ids:
            rec.price = 0
            rec.payment_term_id = False
            rec.delivery_period = False
        return self.write({'state': 'draft'})


    def fill_prices_from_rfq(self):
        """Fill the price in evaluation lines based on Supplier A/B/C and RFQs."""
        if not self.material_request_id:
            return

        rfqs = self.env['purchase.order'].search([('request_id', '=', self.material_request_id.id)])

        for line in self.score_ids:
            supplier_partner = False
            if line.order_of_supplier == 'a' and self.a_supplier_id:
                supplier_partner = self.a_supplier_id
            elif line.order_of_supplier == 'b' and self.b_supplier_id:
                supplier_partner = self.b_supplier_id
            elif line.order_of_supplier == 'c' and self.c_supplier_id:
                supplier_partner = self.c_supplier_id

            if supplier_partner:
                supplier_rfq = rfqs.filtered(lambda r: r.partner_id == supplier_partner)
                if supplier_rfq:
                    rfq_line = supplier_rfq[0].order_line and supplier_rfq[0].order_line[0]
                    if rfq_line:
                        line.price = supplier_rfq[0].amount_total
                        line.currency_id = supplier_rfq[0].currency_id.id
                        line.payment_term_id = supplier_rfq[0].payment_term_id.id
                        line.delivery_period = supplier_rfq[0].x_studio_delivery_period or ''

class LowestPriceEvaluationLine(models.Model):
    _name = 'lowest.price.evaluation.line'

    supplier_id = fields.Many2one('lowest.price.evaluation', string='Supplier Evaluation Reference')
    supplier = fields.Text(string="Supplier", required=False, )
    price = fields.Monetary(string='Price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Terms')
    product_availability = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('partially', 'Partially'),
    ], string="Products Availability (Yes/No)")
    delivery_period = fields.Char(string="Delivery Period", required=False, )
    type = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string="Minimum Quality Requirements Met (Yes/No)")
    order_of_supplier = fields.Char()
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], string="Display Type")
    is_colored = fields.Boolean(default=False)
