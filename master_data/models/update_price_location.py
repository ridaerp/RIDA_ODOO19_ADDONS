from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class UpdateTransportationPrices(models.Model):
    _name = 'update.transportation.prices'
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
         ('wfm', 'Waiting Finance Manager'),
         ('coo', 'COO Approval'),
         ('reject', 'reject'), ('done', 'Done')],
        string='Status', default='draft', tracking=True)
    update_transportation_price_line_ids = fields.One2many(comodel_name="update.transportation.prices.line",
                                                           inverse_name="update_trasnportation_price",
                                                           string="", required=False, )

    @api.onchange('req_id')
    def onchange_categ_id(self):
        if self.req_id:
            self.department_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.req_id.id)],
                                                                limit=1).department_id

    def set_confirm(self):
        return self.write({'state': 'wlm_approve'})

    def action_submit(self):
        line_manager = False
        try:
            line_manager = self.req_id.line_manager_id
        except:
            line_manager = False
        if not line_manager or line_manager != self.env.user:
            raise UserError("Sorry. Your are not authorized to approve this document!")
        return self.write({'state': 'wfm'})

    def approve_finance_manager(self):
        return self.write({'state': 'coo'})

    def get_transpoartion_fees(self):
        location_prices = self.env['locations.detail'].sudo().search([])
        self.update_transportation_price_line_ids = False
        for location in location_prices:
            if location.city:
                self.env['update.transportation.prices.line'].create([{'update_trasnportation_price': self.id,
                                                                       'location': location.id,
                                                                       'previous_amount': location.amount,
                                                                       'new_amount': location.amount,
                                                                       }])

    def update_transportation_price(self):
        for rec in self:
            if rec.update_transportation_price_line_ids:
                for location in rec.update_transportation_price_line_ids:
                    location.sudo().location.sudo().amount = location.new_amount
        return self.write({'state': 'done'})

    def set_draft(self):
        return self.write({'state': 'draft'})

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('update.transportation.prices') or ' '

        return super(UpdateTransportationPrices, self).create(vals)

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(UpdateTransportationPrices, self).unlink()


class UpdateTransportationPricesLine(models.Model):
    _name = 'update.transportation.prices.line'

    update_trasnportation_price = fields.Many2one('update.transportation.prices')
    location = fields.Many2one(comodel_name="locations.detail", string="Location")
    previous_amount = fields.Float(required=True, string='Previous Price')
    new_amount = fields.Float(required=True, string='New Price')
    is_colored = fields.Boolean(compute='_compute_is_colored')

    @api.depends('new_amount')
    def _compute_is_colored(self):
        for record in self:
            if record.new_amount != record.previous_amount:
                record.is_colored = True
            else:
                record.is_colored = False
