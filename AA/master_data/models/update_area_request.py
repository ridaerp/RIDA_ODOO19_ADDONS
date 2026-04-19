from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class UpdateAreaRequest(models.Model):
    _name = 'update.area.request'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True,
                             readonly=True)
    department_id = fields.Many2one('hr.department', string="Department",store=True)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    description = fields.Text('')
    date = fields.Date(default=fields.Date.today(), readonly=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('waiting_pricing', 'Waiting Pricing'),
         ('coo', 'COO Approval'),
         ('reject', 'reject'), ('done', 'Done')],
        string='Status', default='draft', track_visibility='onchange')
    area_name = fields.Char(string="New Area Name", required=1)
    area = fields.Many2one(comodel_name="x_area", string="Area")
    distance = fields.Integer(string="Distance", required=1)
    unit_price = fields.Float(string="Unit Price")
    discount_on_ore_price = fields.Float(string="Discount on Ore Price")
    discount_on_transportation = fields.Float(string="Discount on Transportation(O based on grade)")
    gasolain = fields.Float(string="Gasolain/Truck", required=True)

    @api.onchange('req_id')
    def onchange_categ_id(self):
        if self.req_id:
            self.department_id = self.env['hr.employee'].search([('user_id', '=', self.req_id.id)],
                                                                limit=1).department_id

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('update.area.request') or ' '

        return super(UpdateAreaRequest, self).create(vals)

    @api.onchange('area')
    def _onchange_area(self):
        for rec in self:
            rec.distance = rec.sudo().area.sudo().x_studio_distance_1
            rec.unit_price = rec.sudo().area.sudo().x_studio_unit_price
            rec.discount_on_ore_price = rec.sudo().area.sudo().x_studio_discount_on_ore_price
            rec.discount_on_transportation = rec.sudo().area.sudo().x_studio_discount_on_transportation
            # rec.gasolain = rec.area.gasolain

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(UpdateAreaRequest, self).unlink()

    def set_submit(self):
        return self.write({'state': 'waiting_pricing'})

    def set_confirm(self):
        return self.write({'state': 'coo'})

    def set_draft(self):
        return self.write({'state': 'draft'})

    def update_area(self):
        for rec in self:
            rec.sudo().area.sudo().x_name = rec.area_name
            rec.sudo().area.sudo().x_studio_distance_1 = rec.distance
            rec.sudo().area.sudo().x_studio_unit_price = rec.unit_price
            rec.sudo().area.sudo().x_studio_discount_on_ore_price = rec.discount_on_ore_price
            rec.sudo().area.sudo().x_studio_discount_on_transportation = rec.discount_on_transportation
            # rec.area.gasolain = rec.gasolain
        return self.write({'state': 'done'})

