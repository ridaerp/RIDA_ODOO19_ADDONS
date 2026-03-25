from email.policy import default

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class RequestEquipment(models.Model):
    _name = 'request.equipment'
    _order = "create_date desc"
    _rec_name = 'code_seq'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    _description = 'Equipment Request '

    code_seq = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True,
                             readonly=True)
    department_id = fields.Many2one('hr.department', string="Department", readonly=True, store=True)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    description = fields.Text('')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    name = fields.Char('Equipment Name', required=True, translate=True)
    category_id = fields.Many2one('maintenance.equipment.category', string='Equipment Category',
                                  tracking=True, group_expand='_read_group_category_ids')
    partner_id = fields.Many2one('res.partner', string='Vendor', check_company=True)
    partner_ref = fields.Char('Vendor Reference')
    model = fields.Char('Model')
    serial_no = fields.Char('Serial Number', copy=False)
    effective_date = fields.Date('Effective Date', default=fields.Date.context_today, required=True, help="Date at which the equipment became effective. This date will be used to compute the Mean Time Between Failure.")
    warranty_date = fields.Date('Warranty Expiration Date')
    vin = fields.Char('VIN.#')
    employee_id = fields.Many2one('hr.employee', store=True, readonly=False, string='Assigned Employee', tracking=True)
    # compute='_compute_equipment_assign',
    department_id = fields.Many2one('hr.department', store=True, readonly=False, string='Assigned Department', tracking=True)
    # compute='_compute_equipment_assign',
    equipment_assign_to = fields.Selection(
        [('department', 'Department'), ('employee', 'Employee'), ('other', 'Other')],
        string='Used By',
        required=True,
        default='employee')
    maintenance_team_id = fields.Many2one('maintenance.team', string='Maintenance Team', check_company=True)
    tag_ids = fields.Many2many(
        "maintenance.equipment.tag",
        "equipment_tag_req_rel",
        "equipment_id",
        "tag_id",
        string="Tags",
    )
    code=fields.Char("Equipment Code",required=True)
    parent_id = fields.Many2one(
        "maintenance.equipment",
        "Parent Equipment",
        index=True,
        ondelete="cascade",
        tracking=True,
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('md', 'Waiting Master Admin'),
         ('reject', 'reject'), ('done', 'Done')],
        string='Status', default='draft', track_visibility='onchange', copy=False)
    equipment_type=fields.Selection(related="category_id.equipment_type",string="Machines/Vechicles",required=True)
    analytic_account_id=fields.Many2one("account.analytic.account",string="Cost Center")
    location = fields.Char('Location')
    cost = fields.Float('Cost')
    vechicle_model=fields.Many2one("fleet.vehicle.model","Vechicle Model")
    brand = fields.Char('Brand')
    equipment_fleet_type=fields.Many2one("fleet.equipment.type","Equipment Type")
    engine = fields.Char('Engine model')
    engine_serial = fields.Char('Engine serial No')
    year = fields.Integer('Year')
    plate = fields.Char('Plate')
    fleet_category = fields.Selection(string='Fleet Category', selection=[('light', 'Light'), ('vehicles', 'Vehicles'),('heavy_equipment', 'Heavy Equipment'), ('trucks', 'Trucks')],default="vehicles")
    vechicle_id =  fields.Many2one('fleet.vehicle', compute="get_fleet",string='Related Vechicle', ondelete="cascade",readonly=True)
    equipment_id = fields.Many2one('maintenance.equipment', string='Equipment')


    def _track_subtype(self, init_values):
        self.ensure_one()
        if self.state=='done':
            return self.env.ref('master_data.equipment_status')
        if self.state=='reject':
            return self.env.ref('master_data.equipment_rej_status')
        return super(RequestEquipment, self)._track_subtype(init_values)

    def activity_update(self):
        for rec in self:
            users = []
            message = ""
            if rec.state == 'draft':
                users = self.env.ref('base_rida.rida_group_master_data_manager').user_ids
                message = "Please Create the Equipment"
                for user in users:
                    self.activity_schedule('master_data.mail_act_master_data_approval', user_id=user.id, note=message)
            else:
                continue



    @api.model
    def create(self, vals):
        for val in vals:
            val['code_seq'] = self.env['ir.sequence'].next_by_code('equipment.request') or ' '

        return super(RequestEquipment, self).create(vals)

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")

        return super(RequestEquipment, self).unlink()

    def set_submit(self):
        self.activity_update()
        return self.write({'state': 'md'})

    def get_fleet(self):
        for rec in self:
            search_ids = self.env['fleet.vehicle'].search([('equipment_id','=',self.equipment_id.id)])
            rec.vechicle_id=search_ids.id

    def set_approve(self):
        self.equipment_id = self.env['maintenance.equipment'].create({
            'code': self.code,
            'name': self.name,
            'note': self.description,
            'tag_ids': self.tag_ids,
            # 'location': self.location,
            # 'parent_id': self.parent_id.id,
            'category_id': self.category_id.id,
            'fleet_category': self.fleet_category,
            'equipment_type': self.equipment_type,
            'company_id': self.company_id.id,
            'analytic_account_id': self.analytic_account_id.id,
            'equipment_assign_to': self.equipment_assign_to,
            'employee_id': self.employee_id.id,
            'department_id': self.department_id.id,
            'maintenance_team_id': self.maintenance_team_id.id,
            'partner_id': self.partner_id.id,
            'partner_ref': self.partner_ref,
            'model': self.model,
            'serial_no': self.serial_no,
            'vin': self.vin,
            'plate': self.plate,
            'year': self.year,
            'effective_date': self.effective_date,
            'cost': self.cost,
            'vechicle_model': self.vechicle_model.id,
            'brand': self.brand,
            'equipment_fleet_type': self.equipment_fleet_type.id,
            'engine': self.engine,
            'engine_serial': self.engine_serial,
            'warranty_date': self.warranty_date,
        })
        return self.write({'state': 'done'})
