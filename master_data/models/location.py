from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class RequestLocation(models.Model):
    _name = 'request.location'
    _order = "create_date desc"
    _parent_name = "location_id"
    _parent_store = True
    _description = 'Stock Location Request '

    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']


    @api.model
    def default_get(self, fields):
        res = super(RequestLocation, self).default_get(fields)
        if 'barcode' in fields and 'barcode' not in res and res.get('complete_name'):
            res['barcode'] = res['complete_name']
        return res



    code_seq = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    name = fields.Char('Location Name', required=True)
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True,
                             readonly=True)
    department_id = fields.Many2one('hr.department', string="Department", readonly=True, store=True)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")

    state = fields.Selection(
        [('draft', 'Draft'), ('md', 'Waiting Master Admin'),
         ('reject', 'reject'), ('done', 'Done')],
        string='Status', default='draft', tracking=True,copy=False)
    date = fields.Date(default=fields.Date.today(), readonly=True)
    complete_name = fields.Char("Full Location Name", compute='_compute_complete_name', store=True)
    active = fields.Boolean('Active', default=True, help="By unchecking the active field, you may hide a location without deleting it.")
    usage = fields.Selection([
        ('supplier', 'Vendor Location'),
        ('view', 'View'),
        ('internal', 'Internal Location'),
        ('customer', 'Customer Location'),
        ('inventory', 'Inventory Loss'),
        ('production', 'Production'),
        ('transit', 'Transit Location')], string='Location Type',
        default='internal', index=True, required=True,
        help="* Vendor Location: Virtual location representing the source location for products coming from your vendors"
             "\n* View: Virtual location used to create a hierarchical structures for your warehouse, aggregating its child locations ; can't directly contain products"
             "\n* Internal Location: Physical locations inside your own warehouses,"
             "\n* Customer Location: Virtual location representing the destination location for products sent to your customers"
             "\n* Inventory Loss: Virtual location serving as counterpart for inventory operations used to correct stock levels (Physical inventories)"
             "\n* Production: Virtual counterpart location for production operations: this location consumes the components and produces finished products"
             "\n* Transit Location: Counterpart location that should be used in inter-company or inter-warehouses operations")
    location_id = fields.Many2one(
        'stock.location', 'Parent Location', index=True, ondelete='cascade', check_company=True,required=True,
        help="The parent location that includes this location. Example : The 'Dispatch Zone' is the 'Gate 1' parent location.")
    # child_ids = fields.One2many('stock.location', 'location_id', 'Contains')
    comment = fields.Text('Additional Information')
    posx = fields.Integer('Corridor (X)', default=0, help="Optional localization details, for information purpose only")
    posy = fields.Integer('Shelves (Y)', default=0, help="Optional localization details, for information purpose only")
    posz = fields.Integer('Height (Z)', default=0, help="Optional localization details, for information purpose only")
    parent_path = fields.Char(index=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company, index=True, required=True)
    scrap_location = fields.Boolean('Is a Scrap Location?', default=False, help='Check this box to allow using this location to put scrapped/damaged goods.')
    return_location = fields.Boolean('Is a Return Location?', help='Check this box to allow using this location as a return location.')
    removal_strategy_id = fields.Many2one('product.removal', 'Removal Strategy', help="Defines the default method used for suggesting the exact location (shelf) where to take the products from, which lot etc. for this location. This method can be enforced at the product category level, and a fallback is made on the parent locations if none is set here.")
    putaway_rule_ids = fields.One2many('stock.putaway.rule', 'location_in_id', 'Putaway Rules')
    barcode = fields.Char('Barcode', copy=False)
    new_location = fields.Many2one("stock.location",string='Location',readonly=1, copy=False)

    _sql_constraints = [('barcode_company_uniq', 'unique (barcode,company_id)', 'The barcode for a location must be unique per company !')]


    def _track_subtype(self, init_values):
        self.ensure_one()
        if self.state=='done':
            return self.env.ref('master_data.request_location_status')
        if self.state=='reject':
            return self.env.ref('master_data.request_location_rej_status')
        return super(RequestLocation, self)._track_subtype(init_values)


    def activity_update(self):
        for rec in self:
            users = []
            message = ""
            if rec.state == 'draft':
                users = self.env.ref('base_rida.rida_group_master_data_manager').user_ids
                message = "Please Create the Stock Location"
                for user in users:
                    self.activity_schedule('master_data.mail_act_master_data_approval', user_id=user.id, note=message)
            else:
                continue

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")

        return super(RequestLocation, self).unlink()


    @api.model
    def create(self, vals):
        for val in vals:
            val['code_seq'] = self.env['ir.sequence'].next_by_code('request.location') or ' '
        return super(RequestLocation, self).create(vals)

    def set_confirm(self):
        self.activity_update()
        return self.write({'state': 'md'})

    def create_location(self):
        self.new_location = self.env["stock.location"].create({
            'name': self.name,
            'usage': self.usage,
            'complete_name': self.complete_name,
            'location_id': self.location_id.id,
            'barcode': self.barcode,
            'putaway_rule_ids':self.putaway_rule_ids,
            'removal_strategy_id': self.removal_strategy_id.id,
            # 'scrap_location': self.scrap_location,
            'company_id': self.company_id.id,
            # 'posx': self.posx,
            'parent_path': self.parent_path,
            # 'return_location': self.return_location,
            # 'posz': self.posz,
            # 'posy': self.posy,
        })
        return self.write({'state': 'done'})




    @api.depends('name', 'location_id.complete_name', 'usage')
    def _compute_complete_name(self):
        for location in self:
            if location.location_id and location.usage != 'view':
                location.complete_name = '%s/%s' % (location.location_id.complete_name, location.name)
            else:
                location.complete_name = location.name

    @api.onchange('usage')
    def _onchange_usage(self):
        if self.usage not in ('internal', 'inventory'):
            self.scrap_location = False



    def _get_putaway_strategy(self, product):
        ''' Returns the location where the product has to be put, if any compliant putaway strategy is found. Otherwise returns None.'''
        current_location = self
        putaway_location = self.env['stock.location']
        while current_location and not putaway_location:
            # Looking for a putaway about the product.
            putaway_rules = current_location.putaway_rule_ids.filtered(lambda x: x.product_id == product)
            if putaway_rules:
                putaway_location = putaway_rules[0].location_out_id
            # If not product putaway found, we're looking with category so.
            else:
                categ = product.categ_id
                while categ:
                    putaway_rules = current_location.putaway_rule_ids.filtered(lambda x: x.category_id == categ)
                    if putaway_rules:
                        putaway_location = putaway_rules[0].location_out_id
                        break
                    categ = categ.parent_id
            current_location = current_location.location_id
        return putaway_location

    def get_warehouse(self):
        """ Returns warehouse id of warehouse that contains location """
        domain = [('view_location_id', 'parent_of', self.ids)]
        return self.env['stock.warehouse'].search(domain, limit=1)

    def should_bypass_reservation(self):
        self.ensure_one()
        return self.usage in ('supplier', 'customer', 'inventory', 'production') or self.scrap_location or (self.usage == 'transit' and not self.company_id)
