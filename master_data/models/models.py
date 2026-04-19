from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import itertools
from odoo.exceptions import UserError


class EditProduct(models.Model):
    _name = 'edit.product'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    product_name = fields.Char(required=True)
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True, )
    user_type = fields.Selection(related="req_id.user_type")
    department_id = fields.Many2one('hr.department', string="Department", readonly=True, store=True)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    description = fields.Text('')
    date = fields.Date(default=fields.Date.today(), readonly=True)
    company_id = fields.Many2one('res.company', string='Company')
    prod_id = fields.Many2one(comodel_name="product.product", string="Product")
    part_number = fields.Char('Part Number')
    default_code = fields.Char('Item Code', index=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('scm', 'Waiting Warehouse Manager'), ('md', 'Waiting Warehouse Manager'),
         ('reject', 'reject'),
         ('done', 'Done')],
        string='Status', default='draft', tracking=True)
    image_1920 = fields.Image()
    categ_id = fields.Many2one(
        'product.category', 'Product Category',
    )

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")

        return super(EditProduct, self).unlink()

    @api.onchange('prod_id')
    def _onchange_prod_id(self):
        for rec in self:
            rec.default_code = rec.prod_id.default_code
            rec.product_name = rec.prod_id.name
            rec.part_number = rec.prod_id.part_number
            rec.description = rec.prod_id.description
            rec.categ_id = rec.prod_id.categ_id
            if rec.prod_id.image_1920:
                rec.image_1920 = rec.prod_id.image_1920

    def set_confirm(self):
        return self.write({'state': 'md'})

    def set_approve(self):
        self.state = 'md'

    # return self.write({'state': 'md'})

    def set_to_draft(self):
        return self.write({'state': 'draft'})

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('edit.product') or ' '

        return super(EditProduct, self).create(vals)

    @api.onchange('req_id')
    def onchange_categ_id(self):
        if self.req_id:
            self.department_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.req_id.id)],
                                                                limit=1).department_id

    def create_product(self):
        for rec in self:

            rec.sudo().prod_id.sudo().default_code = rec.default_code
            rec.sudo().prod_id.sudo().name = rec.product_name
            rec.sudo().prod_id.sudo().part_number = rec.part_number
            rec.sudo().prod_id.sudo().description = rec.description
            rec.sudo().prod_id.sudo().categ_id = rec.categ_id

            if rec.image_1920:
                rec.sudo().prod_id.image_1920 = rec.image_1920
            return self.write({'state': 'done'})


class RequestProduct(models.Model):
    _name = 'request.product'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Item Code Request'

    @tools.ormcache()
    def _get_default_category_id(self):
        # Deletion forbidden (at least through unlink)
        return self.env.ref('product.product_category_all')

    @tools.ormcache()
    def _get_default_uom_id(self):
        return self.env.ref('uom.product_uom_unit')

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True, )
    user_type = fields.Selection(related="req_id.user_type")
    department_id = fields.Many2one('hr.department', string="Department", readonly=True, store=True)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        default=_get_default_uom_id, )
    uom_po_id = fields.Many2one(
        'uom.uom', 'Purchase Unit of Measure', )
    description = fields.Text('')
    date = fields.Date(default=fields.Date.today(), readonly=True)
    company_id = fields.Many2one('res.company', string='Company')
    prod_id = fields.Many2one(comodel_name="product.product", string="Product", readonly=True, )
    type = fields.Selection([('product', 'Storable Product'),
        ('consu', 'Consumable'),
        ('service', 'Service'), 
         ], string='Product Type', default='product', required=True)

    state_fleet = fields.Selection(related='state')
    categ_id = fields.Many2one(
        'product.category', 'Product Category',
     )
    part_number = fields.Char('Part Number')
    default_code = fields.Char('Item Code', index=True)
    product_name = fields.Char(required=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('scm', 'Waiting Warehouse Manager'), ('md', 'Waiting Master Admin'),
         ('reject', 'reject'),
         ('done', 'Done')],
        string='Status', default='draft', tracking=True)
    purchase_method = fields.Selection([
        ('purchase', 'On ordered quantities'),
        ('receive', 'On received quantities'),
    ], string="Control Policy", help="On ordered quantities: Control bills based on ordered quantities.\n"
                                     "On received quantities: Control bills based on received quantities.",
        default="receive")
    activity_id = fields.Many2one('mail.activity', 'Linked Activity')
    image_1920 = fields.Image()

    def activity_update(self):
        for rec in self:
            users = []
            message = ""
            if rec.state == 'scm':
                users = self.env.ref('base_rida.rida_group_master_data_manager').user_ids
                message = "Please Create the Supplier "
                for user in users:
                    self.activity_schedule('master_data.mail_act_master_data_approval', user_id=user.id, note=message)
            else:
                continue

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")

        return super(RequestProduct, self).unlink()

    # @api.onchange('uom_id')
    # def _onchange_uom_id(self):
    #     if self.uom_id:
    #         self.uom_po_id = self.uom_id.id

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('item.request') or ' '

        return super(RequestProduct, self).create(vals)

    @api.onchange('req_id')
    def onchange_categ_id(self):
        if self.req_id:
            self.department_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.req_id.id)],
                                                                limit=1).department_id

    def set_confirm(self):
        for rec in self:
            if rec.type == 'product' and rec.purchase_method == 'purchase':
                raise UserError("Sorry! Storable Products must be managed based on received quantities")

            if rec.type == 'service':
                return self.write({'state': 'md'})
        else:
            return self.write({'state': 'scm'})

    def set_approve(self):
        self.activity_update()
        if not self.default_code:
            raise UserError("Please Enter the Product Code")
        self.state = 'md'

    def set_to_draft(self):
        return self.write({'state': 'draft'})

    def create_product(self):
        if self.type == 'service' and self.purchase_method != 'purchase':
            raise UserError("The Control Policy for Service must be on ordered quantities")
        is_storable = False
        type = 'service'
        if self.type == 'service':
            type = 'service'
        elif self.type == 'product':
            type = 'consu'
            is_storable = True
        if self.default_code:
            self.prod_id = self.env["product.product"].create(
                {
                    "name": self.product_name,
                    "image_1920": self.image_1920,
                    "type": type,
                    "default_code": self.default_code,
                    "purchase_method": self.purchase_method,
                    "part_number": self.part_number,
                    "description": self.description,
                    "categ_id": self.categ_id.id,
                    "uom_id": self.uom_id.id,
                }
            )
            self.activity_id.action_done()
            return self.write({'state': 'done'})

        else:
            raise UserError(
                _('Please insert Item Code'))

    def get_product(self):
        self.ensure_one()
        tree_view_id = self.env.ref('master_data.master_product_tree_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Products',
            'view_id': tree_view_id,
            'view_mode': 'list',
            'res_model': 'product.product',
            'domain': [('categ_id', '=', self.categ_id.id)],
            'context': "{'create': False}"
        }
