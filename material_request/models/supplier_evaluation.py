from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date, timedelta,datetime


class SupplierPerformanceEvaluation(models.Model):
    _name = 'supplier.performance.evaluation'
    _description = 'Supplier Performance Evaluation'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'name'

    @api.model
    def default_get(self, fields):
        res = super(SupplierPerformanceEvaluation, self).default_get(fields)
        # Prepare the lines for the evaluation
        line_values = []

        # Price Evaluation Section
        line_values.append({
            'evaluation_category': '<b>Price Evaluation</b>',
            # 'display_type': 'line_section',  # This marks it as a section
            'is_colored': True,  # This marks it as a section
        })

        # Sub-categories under the Price Evaluation section
        line_values.append({
            'evaluation_sub_category': '<b>Meet the targeted price/Budget</b>',
            'sup_weight': 15,
            'display_type': 'line_section',  # This marks it as a section
        })
        line_values.append({
            'evaluation_sub_category': '<b>Provides discounted price</b>',
            'sup_weight': 3,
            'display_type': 'line_section',  # This marks it as a section
        })
        line_values.append({
            'evaluation_sub_category': '<b>Includes Warranty</b>',
            'display_type': 'line_section',  # This marks it as a section
            'sup_weight': 2,
        })

        line_values.append({
            'evaluation_category': '<b>Order Accuracy </b>',
            # 'display_type': 'line_section',  # This marks it as a section
            'is_colored': True,
        })

        line_values.append({
            'display_type': 'line_section',  # This marks it as a section
            'evaluation_sub_category': '<b>Quality of supplied product/service</b>',
            'sup_weight': 15,
        })
        line_values.append({
            'display_type': 'line_section',  # This marks it as a section
            'evaluation_sub_category': '<b>Conformity to Specifications</b>',
            'sup_weight': 15,
        })

        line_values.append({
            'evaluation_category': '<b>Supplier Availability </b>',
            # 'display_type': 'line_section',  # This marks it as a section
            'is_colored': True,
        })

        line_values.append({
            'evaluation_sub_category': '<b>Effective Communication & Response to Inquiries</b>',
            'display_type': 'line_section',  # This marks it as a section
            'sup_weight': 5,
        })
        line_values.append({
            'display_type': 'line_section',  # This marks it as a section
            'evaluation_sub_category': '<b>Ability to solve arising issues/problems</b>',
            'sup_weight': 4,
        })
        line_values.append({
            'display_type': 'line_section',  # This marks it as a section
            'evaluation_sub_category': '<b>Ability to respond to emergency requirements</b>',
            'sup_weight': 3,
        })
        line_values.append({
            'display_type': 'line_section',  # This marks it as a section
            'evaluation_sub_category': '<b>Technical Support</b>',
            'sup_weight': 3,
        })

        line_values.append({
            'evaluation_category': '<b>Payment Terms</b>',
            # 'display_type': 'line_section',  # This marks it as a section
            'is_colored': True,
        })
        line_values.append({
            'evaluation_sub_category': '<b>Meet required payment terms</b>',
            'display_type': 'line_section',  # This marks it as a section
            'sup_weight': 10,
        })
        line_values.append({
            'evaluation_sub_category': '<b>Provides payment facilities</b>',
            'display_type': 'line_section',  # This marks it as a section
            'sup_weight': 5,
        })
        # Update the result with the lines for supplier performance

        line_values.append({
            'evaluation_category': '<b>On-Time Delivery</b>',
            # 'display_type': 'line_section',  # This marks it as a section
            'is_colored': True,
        })
        line_values.append({
            'evaluation_sub_category': '<b>Meet agreed delivery period</b>',
            'display_type': 'line_section',  # This marks it as a section
            'sup_weight': 20,
        })
        sup_lines_ids = self.env['supplier.performance.line'].create(line_values)
        res.update({
            'sup_lines_ids': sup_lines_ids
        })
        return res

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Evaluation Prepared', default=lambda self: self.env.user,
                             tracking=True)
    date_from = fields.Date(string="From")
    date_to = fields.Date(string="To")
    vendor_name = fields.Many2one('res.partner', string="Vendor Name")
    state = fields.Selection(
        [('draft', 'Draft'), ('w_proc_manager', 'Waiting Procurement Manager'),
         ('w_scm_director', 'Waiting Supply Chain Director'),
         ('reject', 'reject'),
         ('approved', 'Approved')],
        string='Status', default='draft', track_visibility='onchange')
    # vendor_code = fields.Char(related='',string="Vendor Code")
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    approve_by = fields.Many2one('res.users', string="Approved By", readonly=1)
    approve_date = fields.Datetime(string='Date Evaluation Completed', readonly=1)
    sup_lines_ids = fields.One2many(comodel_name="supplier.performance.line", inverse_name="request_id",
                                    string="Supplier Performance Evaluation", copy=1)
    performance_measure = fields.Text(string="PERFORMANCE MEASUREMENT ")
    overall_eval_comment = fields.Text(string="OVERALL EVALUATION COMMENTS")
    recommendation = fields.Text(string="Recommendation")
    po_count = fields.Integer(string="Count", compute='compute_po_count')
    contract_count = fields.Integer(string="Count", compute='compute_contracts_count')
    quarter = fields.Selection([
        ('Q1', 'Q1'),
        ('Q2', 'Q2'),
        ('Q3', 'Q3'),
        ('Q4', 'Q4'),
    ], string='Quarter', required=True)
    year = fields.Integer(string="Year", default=date.today().year)
    rating = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('satisfactory', 'Satisfactory'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ], string='Performance Rating', compute='_compute_rating', store=True)

    @api.depends('sup_lines_ids')
    def _compute_rating(self):
        for record in self:
            if record.sup_lines_ids:
                total_score_weight = sum(rec.sup_score for rec in record.sup_lines_ids)
                if total_score_weight >= 81:
                    record.rating = 'excellent'
                elif total_score_weight >= 61:
                    record.rating = 'good'
                elif total_score_weight>= 41:
                    record.rating = 'satisfactory'
                elif total_score_weight >= 21:
                    record.rating = 'fair'
                else:
                    record.rating = 'poor'

    @api.onchange('quarter')
    def _onchange_quarter(self):
        for record in self:
            if record.quarter == 'Q1':
                record.date_from = date(record.year, 1, 1)
                record.date_to = date(record.year, 3, 31)
            elif record.quarter == 'Q2':
                record.date_from = date(record.year, 4, 1)
                record.date_to = date(record.year, 6, 30)
            elif record.quarter == 'Q3':
                record.date_from = date(record.year, 7, 1)
                record.date_to = date(record.year, 9, 30)
            elif record.quarter == 'Q4':
                record.date_from = date(record.year, 10, 1)
                record.date_to = date(record.year, 12, 31)
            else:
                record.date_from = False
                record.date_to = False


    @api.depends('vendor_name')
    def compute_po_count(self):
        self.po_count = self.env['purchase.order'].search_count(
            [('partner_id', '=', self.vendor_name.id)])

    @api.depends('vendor_name')
    def compute_contracts_count(self):
        self.contract_count = self.env['purchase.contract'].search_count(
            [('vendor_id', '=', self.vendor_name.id)])


    def action_view_purchase_orders(self):
        self.ensure_one()
        # Find all purchase orders linked to the selected vendor
        purchase_orders = self.env['purchase.order'].search([('partner_id', '=', self.vendor_name.id)])

        # Define the action to open the purchase orders in list view
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Orders',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.vendor_name.id)],
            'context': dict(self.env.context),
        }

    def action_view_contract(self):
        self.ensure_one()
        # Find all purchase orders linked to the selected vendor
        contract_orders = self.env['purchase.contract'].search([('vendor_id', '=', self.vendor_name.id)])

        # Define the action to open the purchase orders in list view
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Contracts',
            'res_model': 'purchase.contract',
            'view_mode': 'tree,form',
            'domain': [('vendor_id', '=', self.vendor_name.id)],
            'context': dict(self.env.context),
        }


    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('supplier.evaluation.code') or ' '
        res = super(SupplierPerformanceEvaluation, self).create(vals)
        return res

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")

        return super(SupplierPerformanceEvaluation, self).unlink()


    def set_submit(self):
        return self.write({'state': 'w_proc_manager'})

    def set_confirm(self):
        return self.write({'state': 'w_scm_director'})

    def action_draft(self):
            if self.sup_lines_ids:
                for rec in self.sup_lines_ids:
                    rec.sup_weight=False
                    rec.sup_rating=False
                    rec.sup_score=False
                    self.rating=False
            return self.write({'state': 'draft'})

    def set_approve(self):
        self.approve_by = self.env.user
        self.approve_date = fields.Datetime.now()
        return self.write({'state': 'approved'})

    @api.constrains('sup_lines_ids')
    def constraint_sup_lines_ids(self):
        for rec in self:
            if rec.sup_lines_ids:
                total_score_weight = sum(rec.sup_score for rec in rec.sup_lines_ids)
                if total_score_weight > 100:
                    raise UserError("The WEIGHTED SCORE Must be Less or Equal 100")

class SupplierPerformanceLine(models.Model):
    _name = 'supplier.performance.line'

    request_id = fields.Many2one("supplier.performance.evaluation", string="Supplier")
    evaluation_category = fields.Text(string="Evaluation Category")
    evaluation_sub_category = fields.Text(string="Evaluation Sub-Category")
    sup_weight = fields.Integer(string="WEIGHT (%)")
    sup_rating = fields.Float(string="Supplier Rating (%)")
    sup_score = fields.Float(string="WEIGHTED SCORE", compute='_compute_score')
    is_colored = fields.Boolean(default=False)
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], string="Display Type")


    @api.depends('sup_weight','sup_rating')
    def _compute_score(self):
        for rec in self:
            if rec.sup_weight and rec.sup_rating:
                rec.sup_score = rec.sup_weight * rec.sup_rating / 100
            else:
                rec.sup_score =0


