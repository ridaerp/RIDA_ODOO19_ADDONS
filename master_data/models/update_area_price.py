from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class UpdateAreaPrices(models.Model):
    _name = 'update.area.price'
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
        [('draft', 'Draft'),
         ('wlm_approve', 'Waiting Line Manager'),
         ('coo', 'COO Approval'),
         ('md', 'Waiting Master Admin'),
         ('reject', 'reject'), ('done', 'Done')],
        string='Status', default='draft', track_visibility='onchange')
    update_area_price_line_ids = fields.One2many(comodel_name="update.area.price.line", inverse_name="update_price",
                                                 string="", required=False, )

    @api.onchange('req_id')
    def onchange_categ_id(self):
        if self.req_id:
            self.department_id = self.env['hr.employee'].search([('user_id', '=', self.req_id.id)],
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

    def ccso_approve(self):
        return self.write({'state': 'md'})

    def update_area_price(self):
        for rec in self:
            if rec.update_area_price_line_ids:
                for area in rec.update_area_price_line_ids:
                    area.sudo().area.sudo().x_studio_unit_price = area.unit_price
                    area.sudo().area.sudo().x_studio_discount_on_ore_price = area.discount_on_ore_price
                    area.sudo().area.sudo().x_studio_discount_on_transportation = area.discount_on_transportation
        return self.write({'state': 'done'})

    def get_area(self):
        area_prices = self.env['x_area'].sudo().search([])
        self.update_area_price_line_ids = False
        for area in area_prices:
            self.env['update.area.price.line'].create([{'update_price': self.id,
                                                        'area': area.id,
                                                        'previous_unit_price': area.x_studio_unit_price,
                                                        'previous_discount_on_ore_price': area.x_studio_discount_on_ore_price,
                                                        'previous_discount_on_transportation': area.x_studio_discount_on_transportation,
                                                        'unit_price': area.x_studio_unit_price,
                                                        'discount_on_ore_price': area.x_studio_discount_on_ore_price,
                                                        'discount_on_transportation': area.x_studio_discount_on_transportation,
                                                        }])

    def get_area_with_price(self):
        self.ensure_one()
        tree_view_id = self.env.ref('master_data.update_area_price_line_tree_view').id
        if self.state == 'draft':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Area',
                'view_id': tree_view_id,
                'view_mode': 'tree',
                'res_model': 'update.area.price.line',
                'domain': [('update_price', '=', self.id)],
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Area',
                'view_id': tree_view_id,
                'view_mode': 'tree',
                'res_model': 'update.area.price.line',
                'domain': [('update_price', '=', self.id)],
                'context': "{'create': False}"
            }

    @api.model
    def create(self, vals):
        for val in vals:
            vals['name'] = self.env['ir.sequence'].next_code_by('update.area.prices') or ' '
        return super(UpdateAreaPrices, self).create(vals)

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(UpdateAreaPrices, self).unlink()


class UpdateAreaPriceLine(models.Model):
    _name = 'update.area.price.line'

    update_price = fields.Many2one('update.area.price')
    area = fields.Many2one(comodel_name="x_area", string="Area")
    previous_unit_price = fields.Float(string="Previous Unit Price",readonly=1)
    previous_discount_on_ore_price = fields.Float(string="Previous Discount on Ore Price",readonly=1)
    previous_discount_on_transportation = fields.Float(string="Previous Discount on Transportation(O based on grade)",readonly=1)
    unit_price = fields.Float(string="Unit Price")
    discount_on_ore_price = fields.Float(string="Discount on Ore Price")
    discount_on_transportation = fields.Float(string="Discount on Transportation(O based on grade)")
    is_colored = fields.Boolean(compute='_compute_is_colored')

    @api.depends('unit_price','discount_on_ore_price','discount_on_transportation')
    def _compute_is_colored(self):
        for record in self:
            if record.unit_price != record.previous_unit_price or record.discount_on_ore_price != record.previous_discount_on_ore_price or record.discount_on_transportation != record.previous_discount_on_transportation:
                record.is_colored = True
            else:
                record.is_colored = False
