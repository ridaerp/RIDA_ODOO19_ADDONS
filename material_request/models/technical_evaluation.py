from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date, timedelta, datetime
from odoo.exceptions import UserError


class WeightedScoringEvaluation(models.Model):
    _name = 'weight.scoring.evaluation'
    _description = 'Technical Evaluation'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'name'

    @api.model
    def default_get(self, fields):
        res = super(WeightedScoringEvaluation, self).default_get(fields)
        # Prepare the lines for the evaluation
        line_values = []
        line_2_values = []

        line_values.append({
            'question': 'Technical',
            'display_type': 'line_section',  # This marks it as a section
            'is_colored': True,  # This marks it as a section
        })

        # Price Evaluation Section
        line_values.append({
            'question': (
                'Product Type (OEM/ Aftermarket):Identify whether the product is OEM or Aftermarket. OEM is preferred for better compatibility, reliability, and quality'
            ),

            'weighted': 10,
            'type': 'technical',
        })
        line_values.append({
            'question': (
                'Technical Specification Compliance:Check how well the product meets the required technical specifications to ensure it fulfills all functional and quality needs'
            ),
            'weighted': 35,
            'type': 'technical',
        })
        line_values.append({
            'question': 'Technical Performance: Evaluate the product’s efficiency, durability, reliability, and expected service life under normal operating conditions',
            'weighted': 15,
            'type': 'technical',
        })

        line_2_values.append({
            'question': 'Commercial ',
            'display_type': 'line_section',  # This marks it as a section
            'is_colored': True,  # This marks it as a section
        })
        line_2_values.append({
            'question': 'Price',
            'type': 'commercial',
            'weighted': 10,
        })
        line_2_values.append({
            'question': 'Payment Terms',
            'type': 'commercial',
            'weighted': 5,
        })
        line_2_values.append({
            'question': 'Product/QTY Availability',
            'type': 'commercial',
            'weighted': 10,
        })
        line_2_values.append({
            'question': 'Delivery Period',
            'type': 'commercial',
            'weighted': 5,
        })
        line_2_values.append({
            'question': 'Warranty',
            'type': 'commercial',
            'weighted': 5,
        })
        line_2_values.append({
            'question': 'Supplier Type (Manufacturer/ Agent/ Trader)',
            'type': 'commercial',
            'weighted': 5,
        })
        score_ids = self.env['supplier.score'].create(line_values)
        comm_score_ids = self.env['supplier.score'].create(line_2_values)
        res.update({
            'score_ids': score_ids,
            'comm_score_ids': comm_score_ids
        })


        # Get the active Material Request ID from context
        active_id = self.env.context.get('active_id')
        if not active_id:
            return res

        mr = self.env['material.request'].browse(active_id)

        # Build product lines for One2many supplier.score.line
        product_lines = []
        for line in mr.line_ids:
            product_lines.append((0, 0, {
                'product_id': line.product_id.id,
            }))

        # Populate One2many field
        res['product_line_ids'] = product_lines


        return res

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Evaluation Prepared', default=lambda self: self.env.user,
                             tracking=True)

    additional_evaluator=fields.Many2one('res.users', string="Assigned Evaluator")
    material_request_id = fields.Many2one('material.request', 'Material Request')


    # material_request_ids = fields.Many2many(
    #     'material.request',  # Related model
    #     'material_request_lower_price_rel',  # Relation table name
    #     'lp_id',  # Column for this model
    #     'mr_id',  # Column for related model
    #     string='Material Requests'
    # )

    mr_requester = fields.Many2one(related='material_request_id.requested_by', string='MR/SR Requester:')
    title = fields.Char(related='material_request_id.title', string='MR/SR Description:')
    date_request = fields.Datetime("Evaluation Date", default=fields.Datetime.now, required=True)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    state = fields.Selection(
        [('draft', 'Draft'), ('dept_manager', 'Department Manager'),
         ('w_proc_exective', 'Waiting Procurement Exective'), ('w_proc_manager', 'Waiting Procurement Manager'),
         ('reject', 'reject'),
         ('approved', 'Approved')],
        string='Status', default='draft', track_tracking=True)
    comment = fields.Text(string="Recommendation:", required=False, )
    a_supplier_id = fields.Many2one('res.partner', string="Supplier A")
    b_supplier_id = fields.Many2one('res.partner', string="Supplier B")
    c_supplier_id = fields.Many2one('res.partner', string="Supplier C")
    score_ids = fields.One2many('supplier.score', 'supplier_id', string='Scores')
    comm_score_ids = fields.One2many('supplier.score', 'comm_supplier_id', string='Scores')
    product_line_ids = fields.One2many('supplier.score.line', 'product_supplier_id', string='Product Acceptance')    ########## Result
    awarded_supplier = fields.Many2many("res.partner",
     # domain="[('id', 'in', [a_supplier_id, b_supplier_id, c_supplier_id])]",
     string="Awarded Supplier:", required=False, )


    accepted_suppliers_ids = fields.Many2many(
        'res.partner',
        compute='_compute_accepted_suppliers',
        string='Accepted Suppliers',
    )
    supplier_a_rating = fields.Selection([
        ('unsatisfactory', 'Unsatisfactory'),
        ('partially_meets', 'Partially Meets Requirements'),
        ('fully_meets', 'Fully Meets Requirements'),
        ('exceeds', 'Exceeds Requirements & Target')
    ], string='Supplier A Rating', compute='_compute_supplier_a_rating', store=True)

    supplier_b_rating = fields.Selection([
        ('unsatisfactory', 'Unsatisfactory'),
        ('partially_meets', 'Partially Meets Requirements'),
        ('fully_meets', 'Fully Meets Requirements'),
        ('exceeds', 'Exceeds Requirements & Target')
    ], string='Supplier B Rating', compute='_compute_supplier_b_rating', store=True)

    supplier_c_rating = fields.Selection([
        ('unsatisfactory', 'Unsatisfactory'),
        ('partially_meets', 'Partially Meets Requirements'),
        ('fully_meets', 'Fully Meets Requirements'),
        ('exceeds', 'Exceeds Requirements & Target')
    ], string='Supplier C Rating', compute='_compute_supplier_c_rating', store=True)


    supplier_a_rating_new = fields.Selection([
        ('accept', 'Accept'),
        ('reject', 'Reject'),
    ], string='Supplier A Rating', compute='_compute_supplier_a_rating', store=True)

    reject_reason1 = fields.Char("Reject Reason")
    reject_reason2 = fields.Char("Reject Reason")
    reject_reason3 = fields.Char("Reject Reason")

    supplier_b_rating_new = fields.Selection([
        ('accept', 'Accept'),
        ('reject', 'Reject'),
    ], string='Supplier b Rating', compute='_compute_supplier_b_rating', store=True)


    supplier_c_rating_new = fields.Selection([
        ('accept', 'Accept'),
        ('reject', 'Reject'),
    ], string='Supplier C Rating', compute='_compute_supplier_c_rating', store=True)


    assigned_date=fields.Datetime("Date of assigned Evaluation",readonly=True)


    total_supplier_a_weighted_score = fields.Float(string='Total Supplier A Weighted Score',
                                                   compute='_compute_total_scores')
    total_supplier_b_weighted_score = fields.Float(string='Total Supplier B Weighted Score',
                                                   compute='_compute_total_scores')
    total_supplier_c_weighted_score = fields.Float(string='Total Supplier C Weighted Score',
                                                   compute='_compute_total_scores')
    purchase_count = fields.Integer(string="Count", compute='compute_purchase_count')


    total_t_supplier_a_weighted_score = fields.Float(string='Total Supplier A Weighted Score',
                                                   compute='_compute_total_scores')
    total_t_supplier_b_weighted_score = fields.Float(string='Total Supplier B Weighted Score',
                                                   compute='_compute_total_scores')
    total_t_supplier_c_weighted_score = fields.Float(string='Total Supplier C Weighted Score',
                                                   compute='_compute_total_scores')



    # Computed booleans to control visibility in the comm_score_ids tree
    hide_supplier_a = fields.Boolean(compute='_compute_total_scores')
    hide_supplier_b = fields.Boolean(compute='_compute_total_scores')
    hide_supplier_c = fields.Boolean(compute='_compute_total_scores')



    # Add these after your supplier rating fields

    supplier_a_rating_html = fields.Html(
        compute='_compute_rating_html', string='Supplier A Rating', sanitize=False
    )
    supplier_b_rating_html = fields.Html(
        compute='_compute_rating_html', string='Supplier B Rating', sanitize=False
    )
    supplier_c_rating_html = fields.Html(
        compute='_compute_rating_html', string='Supplier C Rating', sanitize=False
    )
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id)




    # Totals for Supplier A
    a_total_accept = fields.Integer(string="Total Accept (Sup 1)", readonly=True, compute='_compute_supplier_totals')
    a_total_reject = fields.Integer(string="Total Reject (Sup 1)", readonly=True, compute='_compute_supplier_totals')
    a_performance = fields.Float(string="Performance (Sup 1)", readonly=True, compute='_compute_supplier_totals')

    # Totals for Supplier B
    b_total_accept = fields.Integer(string="Total Accept (Sup 2)", readonly=True, compute='_compute_supplier_totals')
    b_total_reject = fields.Integer(string="Total Reject (Sup 2)", readonly=True, compute='_compute_supplier_totals')
    b_performance = fields.Float(string="Performance (Sup 2)", readonly=True, compute='_compute_supplier_totals')

    # Totals for Supplier C
    c_total_accept = fields.Integer(string="Total Accept (Sup 3)", readonly=True, compute='_compute_supplier_totals')
    c_total_reject = fields.Integer(string="Total Reject (Sup 3)", readonly=True, compute='_compute_supplier_totals')
    c_performance = fields.Float(string="Performance (Sup 3)", readonly=True, compute='_compute_supplier_totals')

    @api.depends('product_line_ids.product_accept_sup1',
                 'product_line_ids.product_accept_sup2',
                 'product_line_ids.product_accept_sup3')
    def _compute_supplier_totals(self):
        for record in self:
            # Supplier A
            record.a_total_accept = sum(1 for line in record.product_line_ids if line.product_accept_sup1 == 'accept')
            record.a_total_reject = sum(1 for line in record.product_line_ids if line.product_accept_sup1 == 'reject')
            record.a_performance = record.a_total_accept / max(1, len(record.product_line_ids)) * 100

            # Supplier B
            record.b_total_accept = sum(1 for line in record.product_line_ids if line.product_accept_sup2 == 'accept')
            record.b_total_reject = sum(1 for line in record.product_line_ids if line.product_accept_sup2 == 'reject')
            record.b_performance = record.b_total_accept / max(1, len(record.product_line_ids)) * 100

            # Supplier C
            record.c_total_accept = sum(1 for line in record.product_line_ids if line.product_accept_sup3 == 'accept')
            record.c_total_reject = sum(1 for line in record.product_line_ids if line.product_accept_sup3 == 'reject')
            record.c_performance = record.c_total_accept / max(1, len(record.product_line_ids)) * 100



    @api.depends('a_supplier_id', 'b_supplier_id', 'c_supplier_id',
                 'supplier_a_rating_new', 'supplier_b_rating_new', 'supplier_c_rating_new')
    def _compute_accepted_suppliers(self):
        for rec in self:
            suppliers = []
            if rec.a_supplier_id and rec.supplier_a_rating_new == 'accept':
                suppliers.append(rec.a_supplier_id.id)
            if rec.b_supplier_id and rec.supplier_b_rating_new == 'accept':
                suppliers.append(rec.b_supplier_id.id)
            if rec.c_supplier_id and rec.supplier_c_rating_new == 'accept':
                suppliers.append(rec.c_supplier_id.id)
            rec.accepted_suppliers_ids = [(6, 0, suppliers)]




    @api.depends('supplier_a_rating_new','supplier_b_rating_new','supplier_c_rating_new')

    def _compute_rating_html(self):
        # color_map = {
        #     'unsatisfactory': 'red',
        #     'partially_meets': 'blue',
        #     'fully_meets': 'green',
        #     'exceeds': 'gold',
        # }
        # label_map = {
        #     'unsatisfactory': 'Unsatisfactory',
        #     'partially_meets': 'Partially Meets Requirements',
        #     'fully_meets': 'Fully Meets Requirements',
        #     'exceeds': 'Exceeds Requirements & Target'
        # }

        color_map = {
            'accept': 'green',
            'reject': 'red',
        }
        label_map = {
            'accept': 'Accepted',
            'reject': 'Rejected',
        }

        for rec in self:
            rec.supplier_a_rating_html = f'<span style="color:{color_map.get(rec.supplier_a_rating_new, "black")}; font-weight:bold;">{label_map.get(rec.supplier_a_rating_new, "")}</span>'
            rec.supplier_b_rating_html = f'<span style="color:{color_map.get(rec.supplier_b_rating_new, "black")}; font-weight:bold;">{label_map.get(rec.supplier_b_rating_new, "")}</span>'
            rec.supplier_c_rating_html = f'<span style="color:{color_map.get(rec.supplier_c_rating_new, "black")}; font-weight:bold;">{label_map.get(rec.supplier_c_rating_new, "")}</span>'






    def compute_purchase_count(self):
        self.purchase_count = self.env['purchase.order'].search_count(
            [('request_id', '=', self.material_request_id.id)])

    def action_view_purchase_order_read(self):
        view_form = self.env.ref('material_request.rfq_tehincal_inherit').id

        return {
            'name': "RFQ / Order",
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'domain': [('request_id', '=', self.material_request_id.id)],
            'target': 'current',
            'view_mode': 'list,form',
            'views': [
                (False, 'list'),      # default tree view
                (view_form, 'form'),  # your inherited form view
            ],
        }


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

    @api.depends('score_ids.supplier_a_weighted_score', 'score_ids.supplier_b_weighted_score',
                 'score_ids.supplier_c_weighted_score',
                 'comm_score_ids.supplier_a_weighted_score', 'comm_score_ids.supplier_b_weighted_score',
                 'comm_score_ids.supplier_c_weighted_score')

    def _compute_total_scores(self):
        for record in self:
            total_a = sum(score.supplier_a_weighted_score for score in record.score_ids) + \
                      sum(score.supplier_a_weighted_score for score in record.comm_score_ids)
            total_b = sum(score.supplier_b_weighted_score for score in record.score_ids) + \
                      sum(score.supplier_b_weighted_score for score in record.comm_score_ids)
            total_c = sum(score.supplier_c_weighted_score for score in record.score_ids) + \
                      sum(score.supplier_c_weighted_score for score in record.comm_score_ids)

            record.total_supplier_a_weighted_score = total_a
            record.total_supplier_b_weighted_score = total_b
            record.total_supplier_c_weighted_score = total_c

            total_t_a = sum(score.supplier_a_weighted_score for score in record.score_ids) 
            total_t_b = sum(score.supplier_b_weighted_score for score in record.score_ids)  
            total_t_c = sum(score.supplier_c_weighted_score for score in record.score_ids)  


            record.total_t_supplier_a_weighted_score = total_t_a
            record.total_t_supplier_b_weighted_score = total_t_b
            record.total_t_supplier_c_weighted_score = total_t_c


            # Hide if total technical score < 30
            record.hide_supplier_a = record.total_t_supplier_a_weighted_score < 30
            record.hide_supplier_b = record.total_t_supplier_b_weighted_score < 30
            record.hide_supplier_c = record.total_t_supplier_c_weighted_score < 30




    @api.depends('total_supplier_a_weighted_score')
    def _compute_supplier_a_rating(self):
        for record in self:
            score = record.total_supplier_a_weighted_score
            t_score = record.total_t_supplier_a_weighted_score

            
            if score > 50:
                record.supplier_a_rating_new = 'accept'
            else:
                record.supplier_a_rating_new = 'reject'

           

            if t_score > 30:
                record.supplier_a_rating_new = 'accept'
            else:
                record.supplier_a_rating_new = 'reject'

    @api.depends('total_supplier_b_weighted_score')
    def _compute_supplier_b_rating(self):

        for record in self:
            score = record.total_supplier_b_weighted_score
            t_score = record.total_t_supplier_b_weighted_score
            if score > 50:
                record.supplier_b_rating_new = 'accept'
            else:
                record.supplier_b_rating_new = 'reject'

            if t_score > 30:
                record.supplier_b_rating_new = 'accept'
            else:
                record.supplier_b_rating_new = 'reject'

        # for record in self:
        #     score = record.total_supplier_b_weighted_score
        #     if score < 20:
        #         record.supplier_b_rating = 'unsatisfactory'
        #     elif score < 50:
        #         record.supplier_b_rating = 'partially_meets'
        #     elif score < 90:
        #         record.supplier_b_rating = 'fully_meets'
        #     else:
        #         record.supplier_b_rating = 'exceeds'

    @api.depends('total_supplier_c_weighted_score')
    def _compute_supplier_c_rating(self):

        for record in self:
            score = record.total_supplier_c_weighted_score
            t_score = record.total_t_supplier_c_weighted_score

            if score > 50:
                record.supplier_c_rating_new = 'accept'
            else:
                record.supplier_c_rating_new = 'reject'

            if t_score > 30:
                record.supplier_c_rating_new = 'accept'
            else:
                record.supplier_c_rating_new = 'reject'




    def action_submit(self):
        """Allow submission by requester, line manager, or additional evaluator"""
        # Get the line manager safely
        line_manager = getattr(self.material_request_id, 'line_manager_id', False)

        # Get the additional evaluator
        additional_eval = getattr(self, 'additional_evaluator', False)

        # Check if current user is allowed
        allowed_users = [
            self.material_request_id.requested_by.id,
        ]
        if line_manager:
            allowed_users.append(line_manager.id)
        if additional_eval:
            allowed_users.append(additional_eval.id)

        if self.env.user.id not in allowed_users:
            raise UserError('Sorry, only MR requester, their line manager, or Enter the Assinged evaluator can submit this document!')


        # --- Score Validation ---
        score_entered = any(
            line.supplier_a_percentage > 0 or line.supplier_b_percentage > 0 or line.supplier_c_percentage > 0
            for line in self.score_ids 
        )

        if not score_entered:
            raise UserError("Please enter at least one score before submitting the evaluation.")



        if self.supplier_a_rating_new == 'reject' and not self.reject_reason1 and self.total_t_supplier_a_weighted_score >=40:
            raise UserError("Please enter a Reject Reason why you reject sup 1.")
        if self.supplier_b_rating_new == 'reject' and not self.reject_reason2 and self.total_t_supplier_b_weighted_score >=40:
            raise UserError("Please enter a Reject Reason why you reject sup 2.")
        if self.supplier_c_rating_new == 'reject' and not self.reject_reason3 and self.total_t_supplier_c_weighted_score >=40:
            raise UserError("Please enter a Reject Reason why you reject sup 3.")


        # Update state
        return self.write({'state': 'dept_manager'})

    
                
    # def action_submit(self):
    #     line_manager = False
    #     try:
    #         line_manager = self.material_request_id.line_manager_id
    #     except:
    #         line_manager = False
    #     if not (self.material_request_id.requested_by.id == self.env.user.id and  line_manager != self.env.user) or self.additional_evaluator==self.env.user.id:
    #         raise UserError('Sorry, Only MR requester can submit this document!')

    #     # self.activity_update()

    #     return self.write({'state': 'dept_manager'})

    # def action_lmn_approve(self):
    #     line_manager = False
    #     try:
    #         line_manager = self.material_request_id.line_manager_id
    #     except:
    #         line_manager = False
    #     if not line_manager or line_manager != self.env.user:
    #         raise UserError("Sorry. Your are not authorized to approve this document!")
    #     if  self.material_request_id:
    #           self.material_request_id.sudo().write({'state': 'w_ce'})
    #     return self.write({'state': 'w_proc_exective'})



    def action_lmn_approve(self):
        line_manager = False
        additional_evaluator = False
        try:
            line_manager = self.material_request_id.line_manager_id
        except:
            line_manager = False

        try:
            additional_evaluator = self.additional_evaluator.line_manager_id
        except:
            additional_evaluator = False

        # Check if current user is either the line manager or the additional evaluator
        if not ((line_manager and line_manager == self.env.user) or 
                (additional_evaluator and additional_evaluator == self.env.user)):
            raise UserError("Sorry. You are not authorized to approve this document!")

        if self.material_request_id:
            self.material_request_id.sudo().write({'state': 'w_ce'})

        return self.write({'state': 'w_proc_exective'})





    def action_w_proc_exective(self):
        return self.write({'state': 'w_proc_manager'})

    def action_w_proc_manager(self):
        if  self.material_request_id:
              self.material_request_id.sudo().write({'state': 'waiting_po'})

        return self.write({'state': 'approved'})

    def action_draft(self):
        for rec in self.score_ids:
            rec.supplier_a_percentage=0
            rec.supplier_b_percentage=0
            rec.supplier_c_percentage=0
        for rec in self.comm_score_ids:
            rec.supplier_a_percentage=0
            rec.supplier_b_percentage=0
            rec.supplier_c_percentage=0
        return self.write({'state': 'draft'})


    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('weight.scoring.evaluation') or ' '

        return super(WeightedScoringEvaluation, self).create(vals)

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry ! only draft records can be deleted!")
        return super(WeightedScoringEvaluation, self).unlink()


class SupplierScore(models.Model):
    _name = 'supplier.score'
    _description = 'Supplier Score'

    supplier_id = fields.Many2one('weight.scoring.evaluation', string='Supplier Evaluation Reference')
    comm_supplier_id = fields.Many2one('weight.scoring.evaluation', string='Supplier Evaluation Reference')
    a_supplier_id = fields.Many2one('res.partner', string="Supplier A")
    b_supplier_id = fields.Many2one('res.partner', string="Supplier B")
    c_supplier_id = fields.Many2one('res.partner', string="Supplier C")
    question = fields.Text(string="Selection Criteria", required=False, )
    weighted = fields.Float(string='Weighted')
    supplier_a_weighted_score = fields.Float(string='Weighted Score', compute='_compute_weighted_score')
    supplier_a_percentage = fields.Float(string='Percentage % Score')
    supplier_b_weighted_score = fields.Float(string='Weighted Score', compute='_compute_weighted_score')
    supplier_b_percentage = fields.Float(string='Percentage % Score')
    supplier_c_weighted_score = fields.Float(string='Weighted Score', compute='_compute_weighted_score')
    supplier_c_percentage = fields.Float(string='Percentage % Score')
    type = fields.Selection([
        ('technical', 'Technical'),
        ('commercial', 'Commercial'),
        ('sum', 'sum')
    ], string="Type")
    type_sum = fields.Char()
    is_colored = fields.Boolean(default=False)
    is_green_colored = fields.Boolean(default=False)
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], string="Display Type")

    @api.depends('supplier_a_percentage', 'supplier_b_percentage', 'supplier_c_percentage')
    def _compute_weighted_score(self):
        for rec in self:
            rec.supplier_a_weighted_score = 0
            rec.supplier_b_weighted_score = 0
            rec.supplier_c_weighted_score = 0
            for record in rec.supplier_id:
                for rec in record.score_ids:
                    if not rec.is_green_colored:
                        if rec.supplier_a_percentage:
                            rec.supplier_a_weighted_score = rec.supplier_a_percentage * rec.weighted / 100
                        else:
                            rec.supplier_a_weighted_score = 0
                        if rec.supplier_b_percentage:
                            rec.supplier_b_weighted_score = rec.supplier_b_percentage * rec.weighted / 100
                        else:
                            rec.supplier_b_weighted_score = 0
                        if rec.supplier_c_percentage:
                            rec.supplier_c_weighted_score = rec.supplier_c_percentage * rec.weighted / 100
                        else:
                            rec.supplier_c_weighted_score = 0
            for record in rec.comm_supplier_id:
                for rec in record.comm_score_ids:
                    if not rec.is_green_colored:
                        if rec.supplier_a_percentage:
                            rec.supplier_a_weighted_score = rec.supplier_a_percentage * rec.weighted / 100
                        else:
                            rec.supplier_a_weighted_score = 0
                        if rec.supplier_b_percentage:
                            rec.supplier_b_weighted_score = rec.supplier_b_percentage * rec.weighted / 100
                        else:
                            rec.supplier_b_weighted_score = 0
                        if rec.supplier_c_percentage:
                            rec.supplier_c_weighted_score = rec.supplier_c_percentage * rec.weighted / 100
                        else:
                            rec.supplier_c_weighted_score = 0

    @api.constrains('supplier_a_percentage', 'supplier_b_percentage', 'supplier_c_percentage')
    def _check_total_percentage(self):
        for record in self:
            if record.supplier_a_percentage > 100 or record.supplier_b_percentage > 100 or record.supplier_c_percentage > 100:
                if not record.is_green_colored:
                    raise UserError("The Percentage % Score Must be Less or Equal 100")


class SupplierScoreLine(models.Model):
    _name = 'supplier.score.line'
    _description = 'Product Score'

    name = fields.Char(string='Name')

    product_supplier_id = fields.Many2one('weight.scoring.evaluation', string='Supplier Evaluation Reference')
    product_id = fields.Many2one('product.product', string='Product')
    note = fields.Char(string='Justification for rejection, if any, for each supplier')

    # Supplier decisions
    product_accept_sup1 = fields.Selection([('accept', 'Accept'), ('reject', 'Reject')], string='Sup 1')
    product_accept_sup2 = fields.Selection([('accept', 'Accept'), ('reject', 'Reject')], string='Sup 2')
    product_accept_sup3 = fields.Selection([('accept', 'Accept'), ('reject', 'Reject')], string='Sup 3')




    # Note fields
    note_sup1 = fields.Text(string='Reject Reason')
    note_sup2 = fields.Text(string='Reject Reason')
    note_sup3 = fields.Text(string='Reject Reason')


    @api.constrains('product_accept_sup1', 'product_accept_sup2', 'product_accept_sup3', 
                    'note_sup1', 'note_sup2', 'note_sup3')
    def _check_reject_note(self):
        for line in self:
            if line.product_accept_sup1 == 'reject' and not line.note_sup1:
                raise UserError(f"Please enter a note for Supplier 1 on product '{line.product_id.name}'")
            if line.product_accept_sup2 == 'reject' and not line.note_sup2:
                raise UserError(f"Please enter a note for Supplier 2 on product '{line.product_id.name}'")
            if line.product_accept_sup3 == 'reject' and not line.note_sup3:
                raise UserError(f"Please enter a note for Supplier 3 on product '{line.product_id.name}'")

