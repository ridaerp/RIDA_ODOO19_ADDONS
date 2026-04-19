from odoo import fields, models, api
from odoo.exceptions import UserError


class ProductMedicare(models.Model):
    _name = 'product.medicare'
    _description = 'Product Medicare'

    name = fields.Char(string='Name')
    product_id = fields.Many2one('product.product', string='Product')
    default_code = fields.Char('Item Code')
    dosage_instruction = fields.Text(
        'Dosage Instruction')
    description = fields.Text(
        'Description')
    qty_available = fields.Float(
        'Quantity On Hand', related='product_id.qty_available')
    qty = fields.Float(
        'Quantity')
    price = fields.Float(
        'Price', digits='Product Price', realted='product_id.list_price')
    uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure', )
    categ_id = fields.Many2one(
        'product.category', 'Product Category',
    )
    picking_id = fields.Many2one(
        'stock.picking', 'Picking',
    )
    manufacture = fields.Char()
    site_effect = fields.Char()
    expire_date = fields.Date(string='Expire Date')
    type_product = fields.Selection(
        [('pharmacy', 'pharmacy'), ('minor_room', 'minor_room'),
         ('lab', 'lab')],
        string='type of product')

    @api.onchange('product_id')
    def _onchange_product(self):
        for rec in self:
            rec.description = rec.product_id.description or False
            rec.default_code = rec.product_id.default_code or False
            rec.uom_id = rec.product_id.uom_id or False
            rec.categ_id = rec.product_id.categ_id or False


class MedicareProductScrap(models.Model):
    _name = 'medicare.product.scrap'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True,
                             readonly=True)
    date = fields.Date(default=fields.Date.today(), string='Request Date')
    product_id = fields.Many2one('product.medicare', string='Product')
    uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure', related='product_id.uom_id')
    expire_date = fields.Date(string='Expire Date', related='product_id.expire_date')
    qty = fields.Float(
        'Quantity')
    description = fields.Text(
        'Comments')
    type_product = fields.Selection(
        [('pharmacy', 'pharmacy'), ('minor_room', 'minor_room'),
         ('lab', 'lab')],
        string='type of product')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('reject', 'Rejected'), ('done', 'Done')],
        string='Status', default='draft', tracking=True)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(MedicareProductScrap, self).unlink()

    def action_draft(self):
        return self.write({'state': 'draft'})

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('medicare.product.scrap') or ' '

        return super(MedicareProductScrap, self).create(vals)

    def set_approve(self):
        for rec in self:
            if rec.qty:
                rec.product_id.qty -= rec.qty
        self.state = 'done'
