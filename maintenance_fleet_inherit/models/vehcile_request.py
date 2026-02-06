from email.policy import default

from odoo import models, fields, api, _
from odoo import models, fields, api, exceptions, _
from odoo.tools import format_datetime

from odoo.exceptions import UserError, ValidationError
import dateutil
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta

# import datetime

_STATES = [
    ('draft', 'Draft'),
    ('line_approve', 'Waiting Manager Approval'),
    ('operation_movement_approve', 'Waiting Fleet Operation Approval'),
    ('reject', 'Rejected'),
    ('cancel', 'Cancelled'),
    ('approve', 'Fleet Processing'),
    ('done', 'Delivered'),
    ('received', 'Received '),
    ('sr_created', 'SR Created'),
    ('release', 'Released'),
]


class VehicleRequest(models.Model):
    _name = 'vehicle.request'
    _description = 'Vehicle/Equipment Request'

    name = fields.Char("Name")


class VehicleRequestType(models.Model):
    _name = 'equipment.request.type'
    _description = 'Equipment Request Type'

    name = fields.Char("Name")


class VehicleEquipmentRequest(models.Model):
    _name = 'vehicle.equipment.request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Vehicle/Equipment Request'
    _rec_name = "name_seq"
    _order ="name_seq desc"

    def _get_default_department(self):
        return self.env.user.department_id.id if self.env.user.department_id else False

    def _get_default_company(self):
        return self.analytic_account_id.company_id.id if self.analytic_account_id.company_id else False

    name_seq = fields.Char("Number", required=True, index=True, default=lambda self: _('New'), copy=False)
    date_request = fields.Datetime("Request Date/Time ", default=fields.Datetime.now, required=True)

    equipment_id = fields.Many2one("maintenance.equipment", "Vehicle/Equipment", index=True)
    category_id = fields.Many2one('maintenance.equipment.category', string='Category', store=True)
    department_id = fields.Many2one('hr.department', string='Dept./Section',
                                    default=lambda self: self._get_default_department())
    location = fields.Char(string='Work Location', required=True)
    started_from = fields.Datetime("Started From", default=fields.Datetime.now, )
    to = fields.Datetime(string='To')
    purpose = fields.Text(string='Purpose')
    capacity = fields.Char(string="Capacity", required=False)
    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'Emergency')], string='Priority' , default='2')
    period = fields.Selection([('24', '24 Hours'), ('12', '12 Hours')], string="Time Period(24/12)", required=True,default="12")
    requested_by = fields.Many2one("res.users", readonly=True, string="Employee", track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True)
    movement_receiving_request_time = fields.Datetime("Receiving request time")
    operator_driver_name = fields.Many2one("res.users", string="Operator / Driver Name")
    movement_delivery_time = fields.Datetime("Delivery Time", readonly=True)
    movement_received_time = fields.Datetime("Received Time", readonly=True)
    duration_mintus = fields.Float("Mintus", compute="compute_duration")
    duration_day = fields.Float("Day", compute="compute_duration")
    duration_second = fields.Float("Seconds", compute="compute_duration")
    driver_evaluation_ids = fields.One2many(comodel_name="trip.evaliation.result", inverse_name="driver_evaluation_id",
                                            copy=0)
    trip_evaluation_ids = fields.One2many(comodel_name="trip.evaliation.result", inverse_name="trip_evaluation_id",
                                          copy=0)
    movement_release_time = fields.Datetime("Release Time", readonly=True)
    equipment_code = fields.Char(string="EQ./ Vehicle CODE", related="equipment_id.code", readonly=True)
    equipment_name = fields.Many2one("equipment.request.type", string="Equipment")

    state = fields.Selection(selection=_STATES, string='Status', index=True, track_visibility='onchange', readonly=True,
                             required=True, copy=False, default='draft')
    comments = fields.Text(string="Comments / تعليقات")
    reason_reject = fields.Char("Resoan Reject", track_visibility='onchange')
    analytic_account_id = fields.Many2one("account.analytic.account", string="Cost Center")
    mr_count = fields.Integer(string="Count", compute='compute_mr_count')
    service_outsource = fields.Boolean("Service Outsourcing", default=False)
    external_equipment_name = fields.Char(string="Vehicle/Equipment")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self._get_default_company())
    mainteance_request_id = fields.Many2one(comodel_name="maintenance.request", string="Maintenance Request", required=False, )

    @api.constrains('started_from', 'date_request', 'priority')
    def _check_started_date_delay(self):
        for rec in self:
            if rec.priority not in ['0', '3']:
                if rec.started_from and rec.date_request:
                    min_date = rec.date_request + timedelta(hours=24)
                    if rec.started_from < min_date:
                        raise ValidationError(
                            "The 'Needed Date' must be at least 24 hours after the request date for normal priority requests.")


    def compute_mr_count(self):
        self.mr_count = self.env['material.request'].search_count([('euipr_request_id', '=', self.id)])


    @api.onchange('equipment_id')
    def onchange_equipment_id(self):
        if self.equipment_id.company_id:
            self.company_id = self.equipment_id.company_id
        else:
            return False

    #  create MR
    def create_sr(self):
        view_id = self.env.ref('material_request.view_material_request_form')
        # for rec in self:
        #   rec.write({
        #       'issuanced_date':datetime.now(),
        #           })
        self.state='sr_created'
        return {
            'name': _('New Service Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'material.request',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_euipr_request_id': self.id,
                'default_title': self.name_seq,
                'default_company_id': self.company_id.id,
                'default_department_id': self.department_id.id,
                'default_analytic_account_id': self.analytic_account_id.id,
                'default_item_type': 'service',

            }}

    def button_draft(self):
        self.state = "draft"

    def button_cancel(self):
        self.state = "cancel"

    def button_to_operation_movement(self):
        self.state = "approve"
        self.movement_receiving_request_time = datetime.now()

    def button_lm_reject(self):
        self.state = "reject"

    def submit(self):
        self.state = "line_approve"

    def button_lm_approve(self):
        ######################add below  by ekhlas code
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                pass

            else:
                self.ensure_one()
                line_managers = []
                # today = fields.Date.now()
                line_manager = False
                try:
                    line_manager = rec.requested_by.line_manager_id
                except:
                    line_manager = False
                # comment by ekhlas
                if not line_manager or line_manager != rec.env.user:
                    raise UserError("Sorry. Your are not authorized to approve this document!")

            rec.state = "operation_movement_approve"

    # def button_to_delivery(self):
    #     message = "Please Close the Request"
    #     self.activity_schedule('maintenance_fleet_inherit.mail_act_user_equipement_request_approval', user_id=self.env.user.id, note=message)
    #     self.activity_schedule('maintenance_fleet_inherit.mail_act_user_equipement_request_approval', user_id=self.requested_by.line_manager_id.id, note=message)
    #     self.state = "done"
    #     self.movement_delivery_time = datetime.now()



    def button_to_delivery(self):
        for record in self:
            message = "Please Close the Request"

            record.activity_schedule(
                'maintenance_fleet_inherit.mail_act_user_equipement_request_approval',
                user_id=record.env.user.id,
                note=message
            )
            record.activity_schedule(
                'maintenance_fleet_inherit.mail_act_user_equipement_request_approval',
                user_id=record.requested_by.line_manager_id.id,
                note=message
            )

            # ✅ Set delivery info
            record.state = "done"
            record.movement_delivery_time = fields.Datetime.now()

            # # ✅ Update Maintenance Request lead time
            # maintenance = record.mainteance_request_id
            # if maintenance and maintenance.equipment_request_datetime:
            #     start_dt = fields.Datetime.context_timestamp(
            #         record, maintenance.equipment_request_datetime
            #     )
            #     end_dt = fields.Datetime.context_timestamp(
            #         record, record.movement_delivery_time
            #     )

            #     duration_hours = (end_dt - start_dt).total_seconds() / 3600

            #     # ✅ Update maintenance duration (HOURS)
            #     maintenance.Material_leadtime = duration_hours


    @api.depends('movement_delivery_time', 'started_from')
    def compute_duration(self):
        if self.movement_delivery_time and self.started_from:
            d1 = self.started_from
            d2 = self.movement_delivery_time
            dd = d2 - d1
            self.duration_day = float(dd.days)
            self.duration_mintus = float(dd.seconds // 60)
            self.duration_second = float(dd.seconds % 60)
        else:
            self.duration_day = 0.0
            self.duration_second = 0.0
            self.duration_mintus = 0.0

    def button_to_received(self):
        if self.requested_by == self.env.user or self.requested_by.line_manager_id == self.env.user:
            self.state = "received"
            self.movement_received_time = datetime.now()
        else:
            raise UserError("Sorry. Your are not authorized to approve this document!")
        self.driver_evaluation_ids=False
        self.trip_evaluation_ids=False
        for rec in self:
            if rec.equipment_name:
                if 'small' in str(rec.equipment_name.name).lower() or 'bus' in str(rec.equipment_name.name).lower() or 'hiace' in str(rec.equipment_name.name).lower() :
                    driver_evaluation_id = self.env['trip.evaliation'].search(
                        [('type_of_vechile', '=', 'small_vehicle'),
                         ('type_of_evaluation', '=', 'drivers')])
                    for record in driver_evaluation_id:
                        driver_evaluation_ids = self.env['trip.evaliation.result'].create(
                            [{'name': record.id, 'driver_evaluation_id': self.id}])
                    trip_evaluation_id = self.env['trip.evaliation'].search(
                        [('type_of_vechile', '=', 'small_vehicle'),
                         ('type_of_evaluation', '=', 'trips')])
                    for record in trip_evaluation_id:
                        trip_evaluation_ids = self.env['trip.evaliation.result'].create(
                            [{'name': record.id, 'trip_evaluation_id': self.id}])
                else:
                    driver_evaluation_id = self.env['trip.evaliation'].search(
                        [('type_of_vechile', '=', 'vehicle'),
                         ('type_of_evaluation', '=', 'drivers')])
                    for record in driver_evaluation_id:
                        driver_evaluation_ids = self.env['trip.evaliation.result'].create(
                            [{'name': record.id, 'driver_evaluation_id': self.id}])
                    trip_evaluation_id = self.env['trip.evaliation'].search(
                        [('type_of_vechile', '=', 'vehicle'),
                         ('type_of_evaluation', '=', 'trips')])
                    for record in trip_evaluation_id:
                        trip_evaluation_ids = self.env['trip.evaliation.result'].create(
                            [{'name': record.id, 'trip_evaluation_id': self.id}])

    def button_to_not_received(self):
        if self.requested_by == self.env.user or self.requested_by.line_manager_id == self.env.user:
            self.state = "approve"
        else:
            raise UserError("Sorry. Your are not authorized to approve this document!")

    def button_to_release(self):
        for rec in self.driver_evaluation_ids:
            if not rec.priority:
                raise UserError("Fill out the Trip Evaluation at the bottom of the screen / املأ تقييم الرحلة في أسفل الشاشة")
        for rec in self.trip_evaluation_ids:
            if not rec.priority:
                 raise UserError("Fill out the Trip Evaluation at the bottom of the screen / املأ تقييم الرحلة في أسفل الشاشة")
        if self.requested_by == self.env.user or self.requested_by.line_manager_id == self.env.user:
            self.state = "release"
            self.movement_release_time = datetime.now()
        else:
            raise UserError("Sorry. Your are not authorized to approve this document!")

    def button_reject(self):
        self.state = "reject"

    def get_requested_by(self):
        user = self.env.user.id
        return user

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError("Only draft records can be deleted!")
        return super(VehicleEquipmentRequest, self).unlink()

    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('name_seq', 'New') == 'New':
                val['name_seq'] = self.env['ir.sequence'].next_by_code('vehicle.equipment.request') or 'New'

        return super(VehicleEquipmentRequest, self).create(vals)

    @api.constrains('to')
    def check_non_zero_end(self):
        if self.to:
            if self.started_from > self.to:
                raise ValidationError("End time should be after start time!")


class MaterialRequest(models.Model):
    _inherit = 'material.request'
    euipr_request_id = fields.Many2one('vehicle.equipment.request', "Equipment Request", copy=False)
    equipment_id = fields.Many2one('maintenance.equipment', 'Equipment', ondelete="cascade", readonly=True)


class TripEvaluation(models.Model):
    _name = 'trip.evaliation'

    name = fields.Text(string="Evaluative questions / الأسئلة التقيمية",required=1)
    type_of_vechile = fields.Selection([
        ('small_vehicle', 'Small Vehicles'),
        ('vehicle', 'Vehicles'),
    ], string='Type of Vechile / نوع الألية',required=1)
    type_of_evaluation = fields.Selection([
        ('drivers', 'Drivers / السائقين'),
        ('trips', 'Trips / الرحلة'),
    ], string='Type of Trip Evaluation / نوع التقييم',required=1)


class TripEvaluationResult(models.Model):
    _name = 'trip.evaliation.result'

    name = fields.Many2one('trip.evaliation', string='Evaluative questions / الأسئلة التقيمية')
    driver_evaluation_id = fields.Many2one("vehicle.equipment.request", string="Driver evaluation ")
    trip_evaluation_id = fields.Many2one("vehicle.equipment.request", string="Trip evaluation")
    priority = fields.Selection([
        ('very low', 'very Low'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string='Priority / التقييم')