from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta


class EquipmentPlanLog(models.Model):
    _name = 'equipment.plan.log'
    _description = 'Equipment Plan Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # equipment_type = fields.Selection([
    #     ('excavator', 'Excavator'),
    #     ('wheel_loader', 'Wheel Loader'),
    #     ('backhoe_loader', 'Backhoe Loader'),
    #     ('water_tanker', 'Water Tanker'),
    #     ('dozer', 'Dozer'),
    #     ('motor_grader', 'Motor Grader'),
    #     ('tipper_truck', 'Tipper Truck'),
    #     ('baby_loader', 'Baby Loader'),
    # ], string='Equipment Type')

    equipment_type_id = fields.Many2one("equipment.request.type", string="Equipment Type")

    state = fields.Selection([
        ('under_production', 'Under Production'),
        ('fleet_approved', 'Fleet Approved'),
    ], string='Status', default='under_production', tracking=True)

    equipment_id = fields.Many2one('maintenance.equipment', string="Equipment")

    usage_start = fields.Datetime(string="Start Time", required=True)
    usage_end = fields.Datetime(string="End Time", required=True)
    note = fields.Html(string="Note")


    duration_hours = fields.Float(string="Planned Duration", compute="_compute_duration", store=True)

    odometer_start = fields.Float(string="Odometer Start")
    odometer_end = fields.Float(string="Odometer End")
    odometer_used = fields.Float(string="Actual Usage", compute="_compute_odometer_used", store=True)

    replacement_equipment_id = fields.Many2one(
        'maintenance.equipment',
        string="New Equipment",
        help="Equipment used as replacement if the original failed."
    )

    replacement_reason = fields.Text(string="Reason")
    is_replaced = fields.Boolean(string="Is Replaced?", default=False)
    replacement_time = fields.Datetime(string="Replacement Time")

    replacement_odometer_start = fields.Float(string="New Odometer Start")
    replacement_odometer_end = fields.Float(string="New Odometer End")
    replacement_odometer_used = fields.Float(string="New Odometer Used", compute="_compute_replacement_odometer_used", store=True)

    production_id = fields.Many2one('mrp.production', string="Manufacturing Order" , required=True)

    def action_approve_fleet(self):
        for record in self:
            record.state = 'fleet_approved'

    @api.depends('usage_start', 'usage_end')
    def _compute_duration(self):
        for record in self:
            if record.usage_start and record.usage_end:
                delta = record.usage_end - record.usage_start
                record.duration_hours = delta.total_seconds() / 3600
            else:
                record.duration_hours = 0

    @api.depends('odometer_start', 'odometer_end')
    def _compute_odometer_used(self):
        for record in self:
            if record.odometer_end and record.odometer_start:
                record.odometer_used = record.odometer_end - record.odometer_start
            else:
                record.odometer_used = 0

    @api.constrains('usage_start', 'usage_end')
    def _check_times(self):
        for rec in self:
            if rec.usage_end <= rec.usage_start:
                raise ValidationError("End time must be after start time.")

    @api.depends('replacement_odometer_start', 'replacement_odometer_end')
    def _compute_replacement_odometer_used(self):
        for record in self:
            if record.replacement_odometer_end and record.replacement_odometer_start:
                record.replacement_odometer_used = record.replacement_odometer_end - record.replacement_odometer_start
            else:
                record.replacement_odometer_used = 0

    @api.constrains('odometer_start', 'odometer_end')
    def _check_orignal_odometer(self):
        for rec in self:
            if rec.odometer_end < rec.odometer_start:
                raise ValidationError("odometer end must be greater than start.")

    @api.constrains('replacement_odometer_start', 'replacement_odometer_end')
    def _check_replacement_odometer(self):
        for rec in self:
            if rec.is_replaced and rec.replacement_odometer_end < rec.replacement_odometer_start:
                raise ValidationError("Replacement odometer end must be greater than start.")



   
