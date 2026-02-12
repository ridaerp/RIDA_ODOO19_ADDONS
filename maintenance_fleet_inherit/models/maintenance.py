# -*- coding: utf-8 -*-
from email.policy import default

from odoo import models, fields, api, _
from datetime import datetime, date
# import datetime

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class FleetVechicles(models.Model):
    _inherit = 'fleet.vehicle'
    _rec_name = 'display_name'
    equipment_id = fields.Many2one('maintenance.equipment', 'Related Equipment', required=True, ondelete="cascade",
                                   readonly=True)
    display_name = fields.Char(compute='compute_display_name', string="Name", store=False)

    maintenance_count = fields.Integer(string="Maintenance Count", compute='compute_mr_count')

    analytic_account_id = fields.Many2one("account.analytic.account", string="Cost Center")
    start_odometer = fields.Float(compute="_get_odometer", inverse='_set_odometer', string='Start Odometer',
                                  readonly=True,
                                  help='Odometer measure of the vehicle at the moment of this log')
    odometer_unit = fields.Selection([
        ('kilometers', 'km'),
        ('miles', 'mi'),
        ('Hours', 'Hours'),
        ], 'Odometer Unit', default='kilometers', help='Unit of the odometer ', required=True)

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if rec.location:
            loc = self.env['vehicle.location'].search([('name', '=', rec.location)], limit=1)
            if not loc:
                self.env['vehicle.location'].create({'name': rec.location})
        return rec

    def write(self, vals):
        res = super().write(vals)
        for val in vals:
            if val.get('location'):
                loc = self.env['vehicle.location'].search([('name', '=', val['location'])], limit=1)
                if not loc:
                    self.env['vehicle.location'].create({'name': val['location']})
        return res

    def _get_odometer(self):
        FleetVehicalOdometer = self.env['fleet.vehicle.odometer']
        for record in self:
            vehicle_odometer = FleetVehicalOdometer.search([('vehicle_id', '=', record.id)], limit=1, order='create_date desc')
            if vehicle_odometer:
                record.odometer = vehicle_odometer.value
                record.start_odometer = vehicle_odometer.start_value
            else:
                record.odometer = 0
                record.start_odometer = 0


    @api.depends('equipment_id')
    def compute_display_name(self):
        for rec in self:
            display_name = ""
            if rec.equipment_id or rec.equipment_id.code:
                display_name = str(rec.equipment_id.name) + " [ " + str(rec.equipment_id.code) + " ]"
            rec.display_name = display_name

    def compute_mr_count(self):
        self.maintenance_count = self.env['maintenance.request'].search_count(
            [('equipment_id', '=', self.equipment_id.id)])

    def preview_equip_list(self):
        return {
            'name': "Maintenance Equipment",
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.equipment',
            'view_id': False,
            'view_mode': 'list,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('id', '=', self.equipment_id.id)],
        }

    def action_view_mr(self):
        return {
            'name': "Maintenance Request",
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request',
            'view_id': False,
            'view_mode': 'list,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('equipment_id', '=', self.equipment_id.id)],
        }


class MaintenanceEquiement(models.Model):
    _inherit = 'maintenance.equipment'

    # works_24_hours = fields.Boolean(
    #     string='24 Hours Operation',
    #     help='Equipment works in two shifts (24 hours)'
    # )
    def _default_equipment_status(self):
        return self.env['maintenance.equipment.status'].search([('sequence', '=', 1)], limit=1).id

    code = fields.Char("Equipment Code", required=True)
    custom_sequence = fields.Integer("sequence")
    vechicle_model = fields.Many2one("fleet.vehicle.model", "Vechicle Model")
    equipment_type = fields.Selection(related="category_id.equipment_type", string="Machines/Vechicles", required=True)
    vechicle_id = fields.Many2one('fleet.vehicle', compute="get_fleet", string='Related Vechicle', ondelete="cascade",
                                  readonly=True)
    analytic_account_id = fields.Many2one("account.analytic.account", string="Analytic Account")

    brand = fields.Char('Brand')
    fleet_category = fields.Selection(string='Fleet Category', selection=[('light', 'Light'), ('vehicles', 'Vehicles'),
                                                                          ('heavy_equipment', 'Heavy Equipment'),
                                                                          ('trucks', 'Trucks')],default="vehicles")
    year = fields.Integer('Year')
    plate = fields.Char('Plate')
    vin = fields.Char('VIN.#')
    engine = fields.Char('Engine model')
    engine_serial = fields.Char('Engine serial No')
    c_b_type = fields.Char(string="C.B.Type")
    c_b_rating = fields.Char(string="C.B.Rating")
    rated_power_kva = fields.Char(string="Rated Power KVA")
    voltage_transfer = fields.Char(string="Voltage Transfer")
    B_DIM = fields.Char("B-DIM")
    TYPE = fields.Char("TYPE")
    UNIT_NAME = fields.Char("UNIT NAME")
    U_DIM = fields.Char("U-DIM")
    AC = fields.Char("AC")
    time_period = fields.Selection([('24', '24 Hours'), ('12', '12 Hours')], "Time Period")
    equipment_fleet_type = fields.Many2one("fleet.equipment.type", "Equipment Type")
    type_of_equipment = fields.Char(string='Type', help="Type of equipment ex. ")
    stander_fuel = fields.Float(string="Stander Fuel Consumption Rate")

    status_id = fields.Many2one(readonly=True, default=_default_equipment_status)
    team_color = fields.Char(string="Team Color")
    zone_id = fields.Many2one(comodel_name="zone", string="Zone")
    block_id = fields.Many2one(comodel_name="block", string="Block")
    office_room_id = fields.Many2one(comodel_name="office.room", string="Offices & Rooms")
    odometer = fields.Float(compute="_get_odometer", inverse='_set_odometer', string='Last Odometer',readonly=True,
                            help='Odometer measure of the vehicle at the moment of this log')
    start_odometer = fields.Float(compute="_get_odometer", inverse='_set_odometer', string='Start Odometer',readonly=True,
                            help='Odometer measure of the vehicle at the moment of this log')
    odometer_id = fields.Many2one('fleet.vehicle.odometer', 'Odometer',
                                  help='Odometer measure of the vehicle at the moment of this log')
    odometer_count = fields.Integer(compute="_compute_count_all", string='Odometer')
    odometer_unit = fields.Selection([
        ('kilometers', 'km'),
        ('miles', 'mi'),
        ('Hours', 'Hours'),
        ], 'Odometer Unit', default='kilometers', help='Unit of the odometer ', required=True)


    asset_id=fields.Many2one("account.asset","Asset")
    
    def _compute_count_all(self):
        Odometer = self.env['fleet.vehicle.odometer']
        for record in self:
            record.odometer_count = Odometer.search_count([('vehicle_id', '=', record.vechicle_id.id)])

    ####################function to add code in search filed
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, ('[' + record.code + ']') + "" + record.name if record.code else ''))
        return result

    def _get_odometer(self):
        FleetVehicalOdometer = self.env['fleet.vehicle.odometer']
        for record in self:
            vehicle_odometer = FleetVehicalOdometer.search(['|',('vehicle_id', '=', record.vechicle_id.id),('equipment_id','=',record.id)], limit=1, order='create_date desc')
            if vehicle_odometer:
                record.odometer = vehicle_odometer.value
                record.start_odometer = vehicle_odometer.start_value
            else:
                record.odometer = 0
                record.start_odometer = 0

    def set_odometer(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:

            res = self.env['ir.actions.act_window']._for_xml_id('fleet.%s' % xml_id)
            res.update(
                context=dict(self.env.context, default_vehicle_id=self.vechicle_id.id,default_equipment_id=self.id, group_by=False),
                domain=[('vehicle_id', '=', self.vechicle_id.id)]
            )
            return res
        return False

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        pos = self.search(domain + args, limit=limit)
        return pos.name_get()


    def get_fleet(self):
        for record in self:
            search_ids = self.env['fleet.vehicle'].search([('equipment_id', '=', record.id)])
            if search_ids:
                record.vechicle_id = search_ids[0]
            else:
                record.vechicle_id = False

    @api.model
    def create(self, vals):
        result = super(MaintenanceEquiement, self).create(vals)

        fleet_vals = {'name': result.name,
                      'model_id': result.vechicle_model.id,
                      'next_assignation_date': result.assign_date,
                      'company_id': result.company_id.id,
                      'equipment_id': result.id,
                      'net_car_value': result.cost,
                      'license_plate': result.serial_no,
                      'analytic_account_id': result.analytic_account_id.id,
                      'vin_sn': result.vin,
                      }
        search_ids = self.env['fleet.vehicle'].search([('equipment_id', '=', self._context.get('active_id'))])

        # if not search_ids:
        if result.equipment_type == 'vechicles':
            equipment_id = self.env['fleet.vehicle'].create(fleet_vals)
        return result

    def preview_fleet_list(self):
        return {
            'name': "Maintenance Equipment",
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.vehicle',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('id', '=', self.vechicle_id.id)],
        }

    def preview_location_list(self):
        return {
            'name': "Equipment Relocation",
            'type': 'ir.actions.act_window',
            'res_model': 'vehicle.equipment.request',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('equipment_id', '=', self.id), ('state', '=', 'release')],
        }

    def preview_issuance_list(self):
        self.ensure_one()
        tree_view_id = self.env.ref('studio_customization.odoo_studio_default__1274eaeb-3d89-4f4b-93c3-728d624825fa').id
        return {
            'name': "Issuance Request",
            'type': 'ir.actions.act_window',
            'res_model': 'issuance.request.line',
            'view_id': tree_view_id,
            'view_mode': 'list',
            'domain': ['|', ('product_id.categ_id', 'like', 'General Material / Gasoline'),
                       ('equipment_id', '=', self.id), ('analytic_account_id.code', 'ilike', self.code)],
            'context': "{'create': False}"
        }

class MaintenanceEquitmentCategory(models.Model):
    _inherit = 'maintenance.equipment.category'

    equipment_type = fields.Selection(
        [('machines', 'Machines'), ('vechicles', 'Vechicles'), ('utilities', 'Utilities')],
        string="Machines/Vechicles", required=True,default="machines")


class FleetVechiclesType(models.Model):
    _name = "fleet.equipment.type"
    name = fields.Char("Name")


class MaintenanceEquitmentStatus(models.Model):
    _inherit = "maintenance.equipment.status"
    sequence = fields.Integer("Sequence")


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    def _default_analytic_account_id(self):
        return self.office_room_id.analytic_account_id.id or self.equipment_id.analytic_account_id.id

    @api.onchange('equipment_id','office_room_id')
    def onchange_equipment_id(self):
        if self.office_room_id:
            self.analytic_account_id = self.office_room_id.analytic_account_id


        if self.equipment_id:
            self.user_id = self.equipment_id.technician_user_id if self.equipment_id.technician_user_id else self.equipment_id.category_id.technician_user_id
            self.category_id = self.equipment_id.category_id

            self.analytic_account_id = self.equipment_id.analytic_account_id
            if self.equipment_id.maintenance_team_id:
                self.maintenance_team_id = self.equipment_id.maintenance_team_id.id

            if self.equipment_id.company_id:
                self.company_id = self.equipment_id.company_id

    # location_id = fields.Many2one('vehicle.location', string='Location')
    wo_number = fields.Char('WO Number', copy=False, readonly=True, index=True, default=lambda self: _('New'))
    location = fields.Char("Location")
    custom_sequence = fields.Integer("sequence",related='equipment_id.custom_sequence')

    request_date_time = fields.Datetime('Request Date /Time', tracking=True,
                                        help="Date requested for the maintenance to happen")

    request_time = fields.Char(
        string='Request Time',
        compute='_compute_request_time',
        store=True
    )

    department_id = fields.Many2one('hr.department', string='Department',
                                    default=lambda self: self._get_default_department())
    # analytic_account_id=fields.Many2one("account.analytic.account",related="equipment_id.analytic_account_id",string="Cost Center")
    analytic_account_id = fields.Many2one("account.analytic.account", default=_default_analytic_account_id,
                                          string="Cost Center")

    defect_type = fields.Selection(
        [('electrical', 'Electrical'), ('mechanical', 'Mechanical'), ('hydraulic', 'Hydraulic'),
         ('transmission', 'Transmission'), ('main', 'Main')], "Defect Category")

    defect_type_id = fields.Many2one("defect.category", "Defect Category")



    maintenance_defect = fields.Many2one("maintenance.defect", string="Defect Type")
    maintenance_note = fields.Text(string="Maintenance feedback")
    inspect_note = fields.Text(string="Inspection feedback")
    wo_receive_datetime = fields.Datetime('W.O Received Date / Time',
                                          tracking=True, readonly=True)

    assigned_datetime = fields.Datetime('DateTime of Assigned ',
                                        tracking=True, readonly=True)


    assigned_date = fields.Char(
        string='Date of Assigned',
        compute='_compute_assigned_date',
        store=True
    )

    assigned_time = fields.Char(
        string='Time of Assigned ',
        compute='_compute_assigned_time',
        store=True
    )





    insepect_datetime = fields.Datetime('Started  Inspect date / time',
                                        tracking=True)
    m_s_datetime = fields.Datetime('Maintenance Started date / time',
                                   tracking=True)
    m_e_datetime = fields.Datetime('Closing date / time',
                                   tracking=True)

    m_e_time = fields.Char(
        string='Closing  time',
        compute='_compute_end_time',
        store=True
    )
    x_studio_equipment_code = fields.Char()


    complete_datetime = fields.Datetime('Complete date / time',
                                        tracking=True)
    complete_date = fields.Char(
        string='Complete Date',
        compute='_compute_complete_date',
        store=True
    )

    complete_time = fields.Char(
        string='Complete Time',
        compute='_compute_complete_time',
        store=True
    )



    actual_duration = fields.Char(
        string='Actual Duration',
        compute='get_actual_duration',
        store=True
    )
    maintenance_time = fields.Char(
        string='Maintenance Time',
        compute='ge_maintenance_time',
        store=True
    )
    duration_minutes = fields.Float(
        string='Duration (Minutes)',
        compute='_compute_duration_minutes',
        store=True
    )



    odometer_id = fields.Many2one('fleet.vehicle.odometer', 'Odometer',
                                  help='Odometer measure of the vehicle at the moment of this log')
    odometer = fields.Float(string='Odometer Value',
                            help='Odometer measure of the vehicle at the moment of this log')
    # odometer_unit = fields.Selection(related='vehicle_id.odometer_unit', string="Unit", readonly=True)
    equipment_type = fields.Selection(related="equipment_id.equipment_type", string="Machines/Vechicles", required=True)

    requested_by = fields.Many2one('res.users', 'Requested by', track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True, readonly=True)
    sequence = fields.Integer(related="stage_id.sequence", default=1, string='Sequence', )

    need_spare = fields.Selection([('yes', 'Yes'), ('no', 'No')], "Need SparePart", default="")
    maintenance_type_id = fields.Selection([('internal', 'Internal'), ('external', 'External')], "Maintenance Type",
                                           default="")
    cat_type = fields.Char(related='category_id.name')
    stage_id = fields.Many2one(readonly=True)

    technican_user = fields.Many2one('res.users', 'Maintenance Technican', track_visibility='onchange')
    technican_users = fields.Many2many('res.users', string='Maintenance Technicans')
    

    technican_users_name = fields.Char(
        string='Maintenance Technicans Names',
        compute='_compute_techincan_names',
        store=True
    )

    team_users = fields.Many2many('res.users', "Team Members", compute="get_m_team")

    vechicle_id = fields.Many2one(related="equipment_id.vechicle_id", string="Vehicle")
    duration_from_in_out = fields.Float("DownTime/Mins", compute=
    "get_duration")
    duration_from_in_out_hour = fields.Float("DownTime/Hours", compute=
    "get_duration")

    reponse_time = fields.Float("Respone Time", compute=
    "get_response")

    mr_members_ids = fields.Many2many(related="maintenance_team_id.members_ids", string="Members")
    period = fields.Selection([('24', '24 Hours'), ('12', '12 Hours')], string="Time Period(24/12)")
    total_available_time = fields.Float("TOTAL AVAILABLE TIME min.", compute="get_available")
    net_available_time = fields.Float("NET AVAILABLE TIME min.", compute="get_available")
    equipment_available_time = fields.Float("EQUIPMENT AVAILABLE", compute="get_available")
    name_state = fields.Char(string="", related='stage_id.name')
    zone_id = fields.Many2one(comodel_name="zone", string="Zone",related="block_id.zone_id")
    block_id = fields.Many2one(comodel_name="block", string="Block")
    office_room_id = fields.Many2one(comodel_name="office.room", string="Offices & Rooms")

    maintenance_for=fields.Selection([('equipment','Equipment'),('workcenter','Workcenter'),('other','Other')],"For")

    std_durattion = fields.Float("Std Duration")
    equipment_leadtime = fields.Float("Equipment Waiting Time", compute=
    "get_equipment_leadtime")

    equipment_recevied_date_time = fields.Datetime('Equipment Received Date Time',
                                        )


    equipment_recevied_date = fields.Char(
        string='Equipment Received Date',
        compute='_compute_equipment_rec_date',
        store=True
    )

    equipment_recevied_time = fields.Char(
        string='Equipment Received Time',
        compute='_compute_equipment_rec_time',
        store=True
    )

    equipment_request_datetime = fields.Datetime('Equipment Request Date Time',
                                       )

    equipment_request_date = fields.Char(
        string='Equipment Request Date',
        compute='_compute_equipment_date',
        store=True
    )

    equipment_request_time = fields.Char(
        string='Equipment Request Time',
        compute='_compute_equipment_time',
        store=True
    )



    ################material AS MR
    mr_request_datetime = fields.Datetime('MR Request Date Time',
                                       )


    mr_request_date = fields.Char(
        string='MR Request Date ',
        compute='_compute_mr_date',
        store=True
    )

    mr_request_time = fields.Char(
        string='MR Request  Time',
        compute='_compute_mr_time',
        store=True
    )


    mr_recevied_date_time = fields.Datetime('MR/SR Received Date Time',
                                     )


    mr_recevied_date = fields.Char(
        string='MR/SR  Received Date',
        compute='_compute_mr_rec_date',
        store=True
    )

    mr_recevied_time = fields.Char(
        string='MR/SR Received  Time',
        compute='_compute_mr_rec_time',
        store=True
    )


    
    mr_leadtime = fields.Float("MR/SR Waiting Time", compute=
    "get_mr_leadtime")


    issuance_request_datetime = fields.Datetime('Iss Request DateTime',
                                      )

    issuance_request_date = fields.Char(
        string='Iss Request Date',
        compute='_compute_iss_date',
        store=True
    )

    issuance_request_time = fields.Char(
        string='Iss Request Time',
        compute='_compute_iss_time',
        store=True
    )

    issuance_recevied_datetime = fields.Datetime('Iss Received Date Time',
                                       )


    issuance_recevied_date = fields.Char(
        string='Iss  Received Date',
        compute='_compute_iss_rec_date',
        store=True
    )

    issuance_recevied_time = fields.Char(
        string='Iss Received  Time',
        compute='_compute_iss_rec_time',
        store=True
    )



    issuance_leadtime = fields.Float("Iss Request Waiting Time", compute=
    "get_issuance_leadtime")


    waiting_material = fields.Boolean(default=False,string=" MR/SR Request Pending")
    waiting_issuance = fields.Boolean(default=False,string="Equipment Request Pending")
    waiting_equipment = fields.Boolean(default=False,string="Equipment Request Waiting")

    previous_stage_id = fields.Many2one(
        'maintenance.stage',
        string="Previous Stage"
    )

    ####################################Request Date ##################################
    @api.depends('request_date_time')
    def _compute_request_time(self):
        for record in self:
            if record.request_date_time:
                local_dt = fields.Datetime.context_timestamp(record,record.request_date_time
                 )
                record.request_time = local_dt.strftime('%H:%M:%S')
            else:
                record.request_time = False


    #################################### Complete Date Time ##################################


    @api.depends('complete_datetime')
    def _compute_complete_date(self):
        for record in self:
            if record.complete_datetime:
                # Convert to user's timezone
                user_dt = fields.Datetime.context_timestamp(
                    record,
                    record.complete_datetime
                )
                record.complete_date = user_dt.date().strftime('%Y-%m-%d')
            else:
                record.complete_date = False



    @api.depends('complete_datetime')
    def _compute_complete_time(self):
        for record in self:
            if record.complete_datetime:
                local_dt = fields.Datetime.context_timestamp(record,record.complete_datetime
                 )
                record.complete_time = local_dt.strftime('%H:%M:%S')
            else:
                record.complete_time = False

    #################################### Assigned Date ##################################

    @api.depends('assigned_datetime')
    def _compute_assigned_date(self):
        for record in self:
            if record.assigned_datetime:
                # Convert to user's timezone
                user_dt = fields.Datetime.context_timestamp(
                    record,
                    record.assigned_datetime
                )
                record.assigned_date = user_dt.date().strftime('%Y-%m-%d')
            else:
                record.assigned_date = False
    

    @api.depends('assigned_datetime')
    def _compute_assigned_time(self):
        for record in self:
            if record.assigned_datetime:
                local_dt = fields.Datetime.context_timestamp(record,record.assigned_datetime
                 )
                record.assigned_time = local_dt.strftime('%H:%M:%S')
            else:
                record.assigned_time = False


 
    ###########################################################################


    @api.depends('technican_users')
    def _compute_techincan_names(self):
        for record in self:
            record.technican_users_name = ', '.join(
                record.technican_users.mapped('name')
            ) if record.technican_users else False






    @api.depends('m_e_datetime')
    def _compute_end_time(self):
        for record in self:
            if record.m_e_datetime:
                local_dt = fields.Datetime.context_timestamp(record,record.m_e_datetime
                 )
                record.m_e_time = local_dt.strftime('%H:%M:%S')
            else:
                record.m_e_time = False




  #################################### Equipment Received  Date ##################################

    @api.depends('equipment_recevied_date_time')
    def _compute_equipment_rec_date(self):
        for record in self:
            if record.equipment_recevied_date_time:
                # Convert to user's timezone
                user_dt = fields.Datetime.context_timestamp(
                    record,
                    record.equipment_recevied_date_time
                )
                record.equipment_recevied_date = user_dt.date().strftime('%Y-%m-%d')
            else:
                record.equipment_recevied_date = False
    

    @api.depends('equipment_recevied_date_time')
    def _compute_equipment_rec_time(self):
        for record in self:
            if record.equipment_recevied_date_time:
                local_dt = fields.Datetime.context_timestamp(record,record.equipment_recevied_date_time
                 )
                record.equipment_recevied_time = local_dt.strftime('%H:%M:%S')
            else:
                record.equipment_recevied_time = False

  #################################### Equipment Request  Date ##################################

    @api.depends('equipment_request_datetime')
    def _compute_equipment_date(self):
        for record in self:
            if record.equipment_request_datetime:
                # Convert to user's timezone
                user_dt = fields.Datetime.context_timestamp(
                    record,
                    record.equipment_request_datetime
                )
                record.equipment_request_date = user_dt.date().strftime('%Y-%m-%d')
            else:
                record.equipment_request_date = False
    

    @api.depends('equipment_request_datetime')
    def _compute_equipment_time(self):
        for record in self:
            if record.equipment_request_datetime:
                local_dt = fields.Datetime.context_timestamp(record,record.equipment_request_datetime
                 )
                record.equipment_request_time = local_dt.strftime('%H:%M:%S')
            else:
                record.equipment_request_time = False


 #################################### MR Request  Date ##################################

    @api.depends('mr_request_datetime')
    def _compute_mr_date(self):
        for record in self:
            if record.mr_request_datetime:
                # Convert to user's timezone
                user_dt = fields.Datetime.context_timestamp(
                    record,
                    record.mr_request_datetime
                )
                record.mr_request_date = user_dt.date().strftime('%Y-%m-%d')
            else:
                record.mr_request_date = False
    

    @api.depends('mr_request_datetime')
    def _compute_mr_time(self):
        for record in self:
            if record.mr_request_datetime:
                local_dt = fields.Datetime.context_timestamp(record,record.mr_request_datetime
                 )
                record.mr_request_time = local_dt.strftime('%H:%M:%S')
            else:
                record.mr_request_time = False



 #################################### MR Recevied  Date ##################################

    @api.depends('mr_recevied_date_time')
    def _compute_mr_rec_date(self):
        for record in self:
            if record.mr_recevied_date_time:
                # Convert to user's timezone
                user_dt = fields.Datetime.context_timestamp(
                    record,
                    record.mr_recevied_date_time
                )
                record.mr_recevied_date = user_dt.date().strftime('%Y-%m-%d')
            else:
                record.mr_recevied_date = False
    

    @api.depends('mr_recevied_date_time')
    def _compute_mr_rec_time(self):
        for record in self:
            if record.mr_recevied_date_time:
                local_dt = fields.Datetime.context_timestamp(record,record.mr_recevied_date_time
                 )
                record.mr_recevied_time = local_dt.strftime('%H:%M:%S')
            else:
                record.mr_recevied_time = False



 #################################### Issuance  Date ##################################

    @api.depends('issuance_request_datetime')
    def _compute_iss_date(self):
        for record in self:
            if record.issuance_request_datetime:
                # Convert to user's timezone
                user_dt = fields.Datetime.context_timestamp(
                    record,
                    record.issuance_request_datetime
                )
                record.issuance_request_date = user_dt.date().strftime('%Y-%m-%d')
            else:
                record.issuance_request_date = False
    

    @api.depends('issuance_request_datetime')
    def _compute_iss_time(self):
        for record in self:
            if record.issuance_request_datetime:
                local_dt = fields.Datetime.context_timestamp(record,record.issuance_request_datetime
                 )
                record.issuance_request_time = local_dt.strftime('%H:%M:%S')
            else:
                record.issuance_request_time = False




 #################################### Issuance  Date ##################################

    @api.depends('issuance_recevied_datetime')
    def _compute_iss_rec_date(self):
        for record in self:
            if record.issuance_recevied_datetime:
                # Convert to user's timezone
                user_dt = fields.Datetime.context_timestamp(
                    record,
                    record.issuance_recevied_datetime
                )
                record.issuance_recevied_date = user_dt.date().strftime('%Y-%m-%d')
            else:
                record.issuance_recevied_date = False
    

    @api.depends('issuance_recevied_datetime')
    def _compute_iss_rec_time(self):
        for record in self:
            if record.issuance_recevied_datetime:
                local_dt = fields.Datetime.context_timestamp(record,record.issuance_recevied_datetime
                 )
                record.issuance_recevied_time = local_dt.strftime('%H:%M:%S')
            else:
                record.issuance_recevied_time = False







    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if rec.location:
            loc = self.env['vehicle.location'].search([('name', '=', rec.location)], limit=1)
            if not loc:
                self.env['vehicle.location'].create({'name': rec.location})
        return rec

    def write(self, vals):
        res = super().write(vals)
        for val in vals:
            if val.get('location'):
                loc = self.env['vehicle.location'].search([('name', '=', val['location'])], limit=1)
                if not loc:
                    self.env['vehicle.location'].create({'name': val['location']})
        return res

    @api.constrains('std_durattion', 'stage_id', 'team_id')
    def _check_std_duration_required(self):
        for rec in self:
            if rec.stage_id and rec.stage_id.sequence == 3:
                if rec.maintenance_team_id and rec.maintenance_team_id.name == "Construction Team":
                    if not rec.std_durattion or rec.std_durattion == 0.0:
                        raise ValidationError("Duration is required in this stage for the Construction team.")

    def create_vehicle_request(self):
        self.ensure_one()
        under_maintenance_stage = self.env['maintenance.stage'].search([('sequence', '=', 5)])
        inspection_stage = self.env['maintenance.stage'].search([('sequence', '=', 3)])
        self.waiting_equipment = True
        self.equipment_request_datetime=datetime.now()

        # ✅ Save previous stage ONLY if current stage sequence = 3
        if self.stage_id and self.stage_id.sequence == 3:
            self.previous_stage_id = self.stage_id.id


        self.stage_id = under_maintenance_stage.id

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'vehicle.equipment.request',
            # 'res_id': self.id,
            'context': {'form_view_initial_mode': 'edit','default_mainteance_request_id': self.id},
        }





    def _get_default_department(self):
        return self.env.user.department_id.id if self.env.user.department_id else False

    @api.depends("maintenance_team_id")
    def get_m_team(self):
        for rec in self:
            rec.team_users = rec.maintenance_team_id.members_ids.ids

    @api.onchange("equipment_id.status_id")
    def get_available(self):
        for rec in self:
            if rec.complete_datetime:
                if rec.equipment_id.status_id.sequence == 1 and rec.period == '24':
                    rec.total_available_time = 1440
                    rec.net_available_time = rec.total_available_time - rec.duration_from_in_out
                    rec.equipment_available_time = rec.net_available_time / rec.total_available_time


                elif rec.equipment_id.status_id.sequence == 1 and rec.period == '12':
                    rec.total_available_time = 720
                    rec.net_available_time = rec.total_available_time - rec.duration_from_in_out
                    rec.equipment_available_time = (rec.net_available_time / rec.total_available_time)


                else:
                    rec.total_available_time = 0.0
                    rec.net_available_time = 0.0
                    rec.equipment_available_time = 0.0

            else:
                rec.total_available_time = 0.0
                rec.net_available_time = 0.0
                rec.equipment_available_time = 0.0

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, ('[' + record.wo_number + ']') + "" + record.name if record.wo_number else ''))

        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = [('name', operator, name)]
        pos = self.search(domain + args, limit=limit)
        return pos.name_get()


    @api.depends('assigned_datetime', 'request_date_time')
    def get_response(self):
        for rec in self:
            if rec.request_date_time and rec.assigned_datetime:

                requested_date = datetime.strptime(rec.request_date_time.strftime('%Y-%m-%d %H:%M:%S'),
                                                   DEFAULT_SERVER_DATETIME_FORMAT)
                complete_date = datetime.strptime(rec.assigned_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                                                  DEFAULT_SERVER_DATETIME_FORMAT)

                diff = complete_date - requested_date
                diff_s = diff.total_seconds()
                rec.reponse_time = diff_s / 60

            else:
                rec.reponse_time = 0.0



    @api.depends('duration')
    def _compute_duration_minutes(self):
        for record in self:
            record.duration_minutes = record.duration * 60 if record.duration else 0.0





    @api.depends('equipment_recevied_date_time', 'equipment_request_datetime')
    def get_equipment_leadtime(self):
        for rec in self:
            if rec.equipment_recevied_date_time and rec.equipment_request_datetime:

                requested_date = datetime.strptime(rec.equipment_request_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                                                   DEFAULT_SERVER_DATETIME_FORMAT)
                complete_date = datetime.strptime(rec.equipment_recevied_date_time.strftime('%Y-%m-%d %H:%M:%S'),
                                                  DEFAULT_SERVER_DATETIME_FORMAT)

                diff = complete_date - requested_date
                diff_s = diff.total_seconds()
                rec.equipment_leadtime = diff_s / 60

            else:
                rec.equipment_leadtime = 0.0



    @api.depends('mr_recevied_date_time', 'mr_request_datetime')
    def get_mr_leadtime(self):
        for rec in self:
            if rec.mr_recevied_date_time and rec.mr_request_datetime:

                requested_date = datetime.strptime(rec.mr_request_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                                                   DEFAULT_SERVER_DATETIME_FORMAT)
                complete_date = datetime.strptime(rec.mr_recevied_date_time.strftime('%Y-%m-%d %H:%M:%S'),
                                                  DEFAULT_SERVER_DATETIME_FORMAT)

                diff = complete_date - requested_date
                diff_s = diff.total_seconds()
                rec.mr_leadtime = diff_s / 60

            else:
                rec.mr_leadtime = 0.0




    @api.depends('issuance_recevied_datetime', 'issuance_request_datetime')
    def get_issuance_leadtime(self):
        for rec in self:
            if rec.issuance_recevied_datetime and rec.issuance_request_datetime:

                requested_date = datetime.strptime(rec.issuance_request_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                                                   DEFAULT_SERVER_DATETIME_FORMAT)
                complete_date = datetime.strptime(rec.issuance_recevied_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                                                  DEFAULT_SERVER_DATETIME_FORMAT)

                diff = complete_date - requested_date
                diff_s = diff.total_seconds()
                rec.issuance_leadtime = diff_s / 60

            else:
                rec.issuance_leadtime = 0.0



    @api.depends('complete_datetime', 'm_s_datetime')
    def ge_maintenance_time(self):
        for rec in self:
            if rec.m_s_datetime and rec.complete_datetime:

                requested_date = datetime.strptime(rec.m_s_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                                                   DEFAULT_SERVER_DATETIME_FORMAT)
                complete_date = datetime.strptime(rec.complete_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                                                  DEFAULT_SERVER_DATETIME_FORMAT)

                diff = complete_date - requested_date
                diff_s = diff.total_seconds()
                rec.maintenance_time = round(diff_s / 60, 2)  # rounded to 2 decimals

            else:
                rec.maintenance_time = 0.0



    @api.depends('complete_datetime', 'assigned_datetime')
    def get_actual_duration(self):
        for rec in self:
            if rec.wo_receive_datetime and rec.complete_datetime:

                requested_date = datetime.strptime(rec.assigned_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                                                   DEFAULT_SERVER_DATETIME_FORMAT)
                complete_date = datetime.strptime(rec.complete_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                                                  DEFAULT_SERVER_DATETIME_FORMAT)

                diff = complete_date - requested_date
                diff_s = diff.total_seconds()
                rec.actual_duration = round(diff_s / 60, 2)  # rounded to 2 decimals

            else:
                rec.actual_duration = 0.0





    @api.depends('complete_datetime', 'request_date_time')
    def get_duration(self):
        for rec in self:
            if rec.request_date_time and rec.complete_datetime:

                requested_date = datetime.strptime(rec.request_date_time.strftime('%Y-%m-%d %H:%M:%S'),
                                                   DEFAULT_SERVER_DATETIME_FORMAT)
                complete_date = datetime.strptime(rec.complete_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                                                  DEFAULT_SERVER_DATETIME_FORMAT)

                diff = complete_date - requested_date
                diff_s = diff.total_seconds()
                rec.duration_from_in_out = diff_s / 60
                rec.duration_from_in_out_hour = diff_s / 60 / 60

            else:
                rec.duration_from_in_out = 0.0
                rec.duration_from_in_out_hour = 0.0




    def get_requested_by(self):
        user = self.env.user.id
        return user

    def _get_odometer(self):
        self.odometer = 0
        for record in self:
            if record.odometer_id:
                record.odometer = record.odometer_id.value

    def _set_odometer(self):
        pass

    @api.model_create_multi
    def create(self, vals_list):

        for data in vals_list:

            seq = self.env['ir.sequence'].next_by_code('maintenance_request.sequence') or "/"
            data['wo_number'] = seq

            if 'odometer' in data and not data['odometer']:
                # if received value for odometer is 0, then remove it from the
                # data as it would result to the creation of a
                # odometer log with 0, which is to be avoided
                del data['odometer']
        return super(MaintenanceRequest, self).create(vals_list)

        # if request.requested_by.id != self.env.user.id:
        #     raise UserError("Sorry you cannot create a request with different user.")
        # # if not request.line_ids:
        #     raise UserError('Please add Issuance lines!')
        return request

    # def button_cancel(self):
    #     self.state = "cancel"

    def button_submit(self):
        for rec in self:

            # team_ids=self.env['maintenance.team'].search([('id','=',rec.maintenance_team_id.id)])

            # team_user_ids=self.env['res.users'].search([('id','in',team_ids.members_ids.ids)])
            # rec.technican_users=team_user_ids

            if not self.requested_by.id == self.env.user.id:
                raise UserError('Sorry, Only requester can submit this document!')

            if self.analytic_account_id.company_id and self.analytic_account_id.company_id != self.company_id:
                raise UserError('The  Cost Center Incompatible for the Company')

            rec.write({
                'request_date_time': datetime.now(),
                # 'wo_number':seq
            })
            if self.equipment_type == 'utilities' or  self.office_room_id:
                if self.zone_id.admin_approval==True:
                    stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 15)])
                else:
                    stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 14)])

            else:
                stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 2)])
            # ##################old code###########
            # stage_fleet_obj = self.env['maintenance.stage'].search([('sequence', '=', 22)])
            # if rec.equipment_type == 'vechicles':
            #     rec.write({'stage_id': stage_fleet_obj.id,
            #                })
            # else:
            #     rec.write({'stage_id': stage_obj.id,
            #                })
            if self.cat_type == 'GENERATORS' or self.equipment_type == 'vechicles':
                if self.odometer <= 0:
                    raise UserError("Odometer Value Must be grather than 0")
                odometer = self.env['fleet.vehicle.odometer'].create({
                    'value': self.odometer,
                    'date': fields.Date.context_today(self),
                    'equipment_id': self.equipment_id.id,
                    'vehicle_id': self.equipment_id.vechicle_id.id or False
                })
            rec.write({'stage_id': stage_obj.id,
                       })

    def admin_submit(self):
        stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 2)])
        for rec in self:
            rec.write({'stage_id': stage_obj.id,
                       'wo_receive_datetime': datetime.now(),
                       })
            

    def manager_submit(self):
        stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 2)])


        for rec in self:
            if self.env.user.has_group('base.group_system'):
                pass

            else:
                self.ensure_one()
                line_managers = []
                # today = fields.Date.now()
                line_manager = False
                try:
                    line_manager = rec.employee_id.user_id.line_manager_id
                except:
                    line_manager = False
                # comment by ekhlas
                if not line_manager or line_manager != rec.env.user:
                    raise UserError("Sorry. Your are not authorized to approve this document!")

        for rec in self:
            rec.write({'stage_id': stage_obj.id,
                       })

    # def oper_mov_approval(self):
    #     for rec in self:
    #         stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 2)])
    #         rec.write({'stage_id': stage_obj.id,
    #                    'wo_receive_datetime': datetime.now(),
    #                    })

    # @api.onchange('technican_user')
    # def set_receive_wo(self):
    #     for rec in self:
    #         rec.write({
    #             'wo_receive_datetime':datetime.datetime.now(),
    #             })

    def button_receive_wo(self):
        for rec in self:
            if not rec.technican_users:
                raise UserError("Please Assign Technican !")

            # seq = self.env['ir.sequence'].next_by_code('maintenance_request.sequence') or "/"
            # data['number'] = seq

            stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 3)])
            equipment_obj = self.env['maintenance.equipment'].search([('id', '=', rec.equipment_id.id)])
            equipment_status_obj = self.env['maintenance.equipment.status'].search([('sequence', '=', 2)])

            if rec.wo_receive_datetime:
                rec.write({'stage_id': stage_obj.id,
                           'assigned_datetime': datetime.now(),
                           # 'wo_number':seq
                           })

            else:
                rec.write({'stage_id': stage_obj.id,
                           'wo_receive_datetime': datetime.now(),
                           'assigned_datetime': datetime.now(),
                           # 'wo_number':seq
                           })
            equipment_obj.write({'status_id': equipment_status_obj.id})

    # def button_inspect(self):
    #     for rec in self:
    #         stage_obj=self.env['maintenance.stage'].search([('sequence','=',4)])
    #         rec.write({'stage_id':stage_obj.id,

    #             # 'insepect_datetime':datetime.datetime.now(),
    #             'm_s_datetime':datetime.datetime.now(),

    #             })

    def button_inspect(self):
        for rec in self:
            if not rec.maintenance_type_id:
                raise UserError("Check Maintenance internal/external")

            if not rec.need_spare and rec.maintenance_type_id == 'internal':
                raise UserError("Must Define Need SparePart YES/NO !")
            if rec.need_spare == 'yes':
                stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 5)])
                rec.write({'stage_id': stage_obj.id,
                           'm_s_datetime': datetime.now(),
                           })
            else:
                stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 6)])
                rec.write({'stage_id': stage_obj.id,
                           'm_s_datetime': datetime.now(),
                           })





    def button_execute(self):

        for rec in self:
            stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 6)])
            if self.previous_stage_id.sequence==3 and rec.waiting_equipment:
                rec.write({
                'stage_id': self.previous_stage_id.id,
                'equipment_recevied_date_time':datetime.now(),
                'previous_stage_id':False,

                })

            elif rec.waiting_material:
                rec.write({
                    'stage_id': stage_obj.id,
                    'mr_recevied_date_time':datetime.now(),

                    })
            elif rec.waiting_issuance:
                rec.write({
                'stage_id': stage_obj.id,
                'issuance_recevied_datetime':datetime.now(),

                })
            elif rec.waiting_equipment:
                rec.write({
                'stage_id': stage_obj.id,
                'equipment_recevied_date_time':datetime.now(),

                })

            else:
                rec.write({
                'stage_id': stage_obj.id,
                'm_s_datetime':datetime.now(),
                })




    def complete(self):
        for rec in self:
            if rec.duration <= 0:
                raise UserError("Enter Maintance Duration")
            stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 7)])
            rec.sudo().write({'stage_id': stage_obj.id,
                       'complete_datetime': datetime.now(),
                       })

    def close(self,odoo_bot=False):
        requested_by = self.sudo().employee_id.sudo().user_id
        for rec in self:
            stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 8)],limit=1)

            equipment_obj = self.env['maintenance.equipment'].search([('id', '=', rec.equipment_id.id)])
            equipment_status_obj = self.env['maintenance.equipment.status'].search([('sequence', '=', 1)])

            if not odoo_bot:
                x = self.env.user.has_group('mrp.group_mrp_user') and rec.maintenance_team_id.id == 3
                if x:
                    rec.write({'stage_id': stage_obj.id,
                               'm_e_datetime': datetime.now(),
                               # 'request_done':True,
                               'close_date': datetime.now(),
                               })

                    equipment_obj.sudo().write({'status_id': equipment_status_obj.id})
                else :
                    if requested_by != self.env.user:
                        raise UserError("Sorry. Your are not the  close the job just the Requester!")
                rec.write({'stage_id': stage_obj.id,
                           'm_e_datetime': datetime.now(),
                           # 'request_done':True,
                           'close_date': datetime.now(),
                           })

                equipment_obj.sudo().write({'status_id': equipment_status_obj.id})
            else:
                rec.write({'stage_id': stage_obj.id,
                           'm_e_datetime': datetime.now(),
                           # 'request_done':True,
                           'close_date': datetime.now(),
                           })

                equipment_obj.sudo().write({'status_id': equipment_status_obj.id})

    @api.model
    def _cron_close(self):
        maintenance = self.search(
            [('stage_id', '=','Completed')])
        if maintenance:
            for rec in maintenance:
                if rec.zone_id:
                    print('>>>>>>>>>>.type of maintence',rec.zone_id)
                    rec.sudo().close(odoo_bot=True)
        return True

    def button_reject(self):
        for rec in self:
            stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 9)])
            rec.write({'stage_id': stage_obj.id})

    def button_return_maintenance(self):
        for rec in self:
            stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 6)])
            rec.write({'stage_id': stage_obj.id})

    def archive_equipment_request(self):
        super(MaintenanceRequest, self).archive_equipment_request()
        for rec in self:
            stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 10)])
            rec.write({'stage_id': stage_obj.id})
            rec.write({'archive': True})



    # Engineer create MR
    def create_mr(self):
        self.waiting_material = True
        self.mr_request_datetime=datetime.now()
        stage_obj = self.env['maintenance.stage'].search([('sequence', '=',5)],limit=1)
        self.write({'stage_id': stage_obj.id})

        view_id = self.env.ref('material_request.view_material_request_form')
        # for rec in self:
        #   rec.write({
        #       'issuanced_date':datetime.now(),
        #           })

        return {
            'name': _('New Material Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'material.request',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_m_request_id': self.id,
                'default_equipment_id': self.equipment_id.id,
                'default_title': self.name,
                # 'default_priority1': self.priority,
                'default_company_id': self.company_id.id,
                'default_analytic_account_id': self.analytic_account_id.id,

            }}

    # Engineer create IS
    def create_issuance(self):
        self.waiting_issuance = True
        self.issuance_request_datetime=datetime.now()
        stage_obj = self.env['maintenance.stage'].search([('sequence', '=',5)],limit=1)
        self.write({'stage_id': stage_obj.id})

        view_id = self.env.ref('material_request.view_issuance_request_form')
        # for rec in self:
        #   rec.write({
        #       'issuanced_date':datetime.now(),
        #           })

        return {
            'name': _('New Issuance Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'issuance.request',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_equipment_id': self.equipment_id.id,
                'default_m_request_id': self.id,
                'default_title': self.name,
                # 'default_priority1': self.priority,
                'default_company_id': self.company_id.id,
                'default_analytic_account_id': self.analytic_account_id.id,

            }}



    def unlink(self):
        for rec in self:
            if not rec.sequence == 1:
                raise UserError("Only draft records can be deleted!")
            stage_obj = self.env['maintenance.stage'].search([('sequence', '=', 1)],  limit=1)
            stage_obj.ensure_one()
            rec.write({'stage_id': stage_obj.id})

        return super(MaintenanceRequest, self).unlink()


class MaterialRequest(models.Model):
    _inherit = 'material.request'
    m_request_id = fields.Many2one('maintenance.request', "Maintenance Request", copy=False)

    @api.onchange('equipment_id')
    def onchage_equi(self):
        if self.equipment_id.analytic_account_id.id:
            self.analytic_account_id = self.equipment_id.analytic_account_id.id


class IssuanceRequest(models.Model):
    _inherit = 'issuance.request'
    m_request_id = fields.Many2one('maintenance.request', "Maintenance Request", copy=False)




class MaintenanceStage(models.Model):
    _inherit = 'maintenance.stage'
    stage_visible = fields.Boolean(string="Show in Workflow")


class MaintenanceTeam(models.Model):
    _inherit = 'maintenance.team'

    members_ids = fields.Many2many(
        'res.users', string="Team Members")
    calendar_id = fields.Many2one(
        'resource.calendar',
        string='Work Schedule',
        help='Select a work schedule (resource calendar)'
    )
    start_shift = fields.Float()
    end_shift = fields.Float()
    shift_type = fields.Selection([
        ('same_day', 'Same Day'),
        ('cross_day', 'Start Today - End Tomorrow'),
    ], default='same_day', string="Shift Type")

    # user_id = fields.Many2one(comodel_name="res.users", string="Team Leader")


class MaintenanceDefect(models.Model):
    _name = 'maintenance.defect'

    name = fields.Char("Name" , translate=True, )
    type_id = fields.Selection([('electrical', 'Electrical'), ('mechanical', 'Mechanical'), ('hydraulic', 'Hydraulic'),
                                ('transmission', 'Transmission'), ('main', 'Main')], "Defect Category")
    active = fields.Boolean(default=True)


    category_type_id=fields.Many2one("defect.category")

class MaintenanceDefectCategory(models.Model):
    _name = 'defect.category'

    name = fields.Char("Name" , translate=True, )
    equipment_type = fields.Selection([('machines', 'Machines'), ('vechicles', 'Vechicles'), ('utilities', 'Utilities')],
                                      string="Machines/Vechicles")


class zone(models.Model):
    _name = 'zone'
    _description = 'Zone'

    name = fields.Char(required=True)
    description=fields.Char("Description")
    admin_approval=fields.Boolean("Admin Approval")

    def name_get(self):
        result = []
        for record in self:
            display_name = record.name
            if record.description:
                display_name +=  str(record.description) 
            result.append((record.id, display_name))
        return result



class block(models.Model):
    _name = 'block'

    name = fields.Char(required=True)
    zone_id = fields.Many2one(comodel_name="zone", string="Zone",required=True)
    description=fields.Char("Description")




    def name_get(self):
        result = []
        for record in self:
            display_name = record.name+"-"
            # if record.zone_id:
            #     display_name +=  " [ Zone : " + str(record.zone_id.name) + " ]"
            if record.description:
                display_name += str(record.description ) +" [ Zone : " + str(record.zone_id.name) +" "+ str(record.zone_id.description)+ " ]" 
            result.append((record.id, display_name))
        return result



class OfficeRoom(models.Model):
    _name = 'office.room'

    name = fields.Char(required=True)
    block_id = fields.Many2one(comodel_name="block", string="Block", required=True)
    analytic_account_id = fields.Many2one("account.analytic.account", string="Cost Center")
    description=fields.Char("Description")


    def name_get(self):
        result = []
        for record in self:
            display_name = record.name
            # if record.block_id.zone_id:
            #     display_name += " [ Zone : " + str(record.block_id.zone_id.name) + " ]"
            # if record.block_id:
            #     display_name += " [ Block : " + str(record.block_id.name) + " ]"

            if record.description or record.block_id.zone_id or record.block_id:
                display_name += "-"+str(record.description ) +" [ Block : " + str(record.block_id.name) + " ]"+" [ Zone : " + str(record.block_id.zone_id.name) + " ]"
            result.append((record.id, display_name))

        return result



class FleetVehicleOdometer(models.Model):
    _inherit = 'fleet.vehicle.odometer'

    equipment_id = fields.Many2one('maintenance.equipment', ' Equipment', ondelete="cascade")
    location_id = fields.Many2one('vehicle.location', ' location', ondelete="cascade")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle',required=False)
    start_value = fields.Float(string='Start',group_operator="min")
    start_day = fields.Float('Start Shift day')
    end_day = fields.Float('End Shift day')
    start_night = fields.Float('Start Shift Night')
    end_night = fields.Float('Start Shift Night')

    def create(self, vals):
        rec = super(FleetVehicleOdometer, self).create(vals)
        if vals.get('location_id') and rec.equipment_id:
            rec.equipment_id.location = rec.location_id.name
        return rec


class VehicleLocation(models.Model):
    _name = 'vehicle.location'
    _rec_name = 'name'

    name = fields.Char('Location')

