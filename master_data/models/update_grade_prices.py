from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class UpdateGradePrices(models.Model):
    _name = 'update.grade.price'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True,
                             readonly=True)
    department_id = fields.Many2one('hr.department', string="Department", store=True)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    description = fields.Text('')
    date = fields.Date(default=fields.Date.today(), readonly=True)
    state = fields.Selection(
        [('draft', 'Draft'),
         ('wlm_approve', 'Waiting Line Manager'),
         ('coo', 'COO Approval'),
         ('md', 'Waiting Master Admin'),
         ('reject', 'reject'), ('done', 'Done')],
        string='Status', default='draft', tracking=True)
    update_grade_price_line_ids = fields.One2many(comodel_name="update.grade.price.line", inverse_name="update_price",
                                                  string="", required=False, )

    @api.onchange('req_id')
    def onchange_req_id(self):
        if self.req_id:
            self.department_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.req_id.id)],
                                                                limit=1).department_id

    def action_submit(self):
        return self.write({'state': 'wlm_approve'})

    def set_confirm(self):
        line_manager = False
        try:
            line_manager = self.req_id.line_manager_id
        except:
            line_manager = False
        if not line_manager or line_manager != self.env.user:
            raise UserError("Sorry. Your are not authorized to approve this document!")
        return self.write({'state': 'coo'})

    def set_draft(self):
        return self.write({'state': 'draft'})

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(UpdateGradePrices, self).unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code('update.grade.prices') or ' '
        return super(UpdateGradePrices, self).create(vals_list)


    def get_grade(self):
        grade_prices = self.env['purchase.price.list'].sudo().search([])
        self.update_grade_price_line_ids = False
        for grade in grade_prices:
            self.env['update.grade.price.line'].create([{'update_price': self.id,
                                                         'grade': grade.id,
                                                         'min': grade.qty_min,
                                                         'max': grade.qty_max,
                                                         'previous_unit_price': grade.unit_price,
                                                         'previous_discount': grade.discount,
                                                         'unit_price': grade.unit_price,
                                                         'discount': grade.discount,
                                                         }])

    def ccso_approve(self):
        return self.write({'state': 'md'})


    def get_grade_with_price(self):
        self.ensure_one()
        tree_view_id = self.env.ref('master_data.update_grade_price_line_tree_view').id
        if self.state == 'draft':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Update Grade Price List',
                'view_id': tree_view_id,
                'view_mode': 'list',
                'res_model': 'update.grade.price.line',
                'domain': [('update_price', '=', self.id)],
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Update Grade Price List',
                'view_id': tree_view_id,
                'view_mode': 'list',
                'res_model': 'update.grade.price.line',
                'domain': [('update_price', '=', self.id)],
                'context': "{'create': False}"
            }

    def update_grade_price(self):
        for rec in self:
            if rec.update_grade_price_line_ids:
                for grade in rec.update_grade_price_line_ids:
                    grade.sudo().grade.sudo().unit_price = grade.unit_price
                    grade.sudo().grade.sudo().discount = grade.discount
        return self.write({'state': 'done'})


class UpdateGradePriceLine(models.Model):
    _name = 'update.grade.price.line'

    update_price = fields.Many2one('update.grade.price')
    grade = fields.Many2one(comodel_name="purchase.price.list", string="Grade")
    min = fields.Float(string="Min", readonly=1)
    max = fields.Float(string="Max", readonly=1)
    previous_unit_price = fields.Float(string="Previous Unit Price", readonly=1)
    previous_discount = fields.Float(string="Previous Discount", readonly=1)
    unit_price = fields.Float(string="Unit Price")
    discount = fields.Float(string="Discount")
    is_colored = fields.Boolean(compute='_compute_is_colored')

    @api.depends('unit_price','discount')
    def _compute_is_colored(self):
        for record in self:
            if record.unit_price != record.previous_unit_price or record.discount != record.previous_discount:
                record.is_colored = True
            else:
                record.is_colored = False