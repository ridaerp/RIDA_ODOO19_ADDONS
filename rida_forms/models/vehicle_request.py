from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import datetime
import dateutil
from dateutil.relativedelta import relativedelta



_STATES = [
    ('draft', 'Draft'),
    # ('line_approve', 'Waiting Department Manager Approval'),
    # ('Adm_man_approve', 'Admin manager Approval'),
    ('operation_officer_approve', 'Operation Officer Approval'),
    ('movement_manager_approve', 'Movement and Operation Manager Approval'),
    ('reject', 'Rejected'),
    ('cancel', 'Cancelled'),
    # comment by ekhlas ('done', 'Done'),
    ################## change string by ekhlas ##########
    ('done', 'Done'),
    ########################## ekhlas code##################
    # ('purchase', 'Purchase Order'),
    # ('close', 'Closed'),
]



# air_booking_request_amendment


class VehicleEquipmentRegulationForm(models.Model):
    _name = 'vehicle.request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Vehicle Request'
    _rec_name = "name_seq"
    
    name_seq = fields.Char("Number", required=True, index=True, default=lambda self: _('New'), copy=False) 
    date_request = fields.Datetime("Date",default=fields.datetime.now(), required=True)
    equipment_id = fields.Many2one("maintenance.equipment", "Vehicle/Equipments", index=True)
    category_id = fields.Many2one('maintenance.equipment.category', string='Category', store=True, required=True)
    department_id = fields.Many2one('hr.department', string='Dept./Section', related="requested_by.employee_ids.department_id",readonly=True)
    location = fields.Char(string='Work Location')
    started_from = fields.Datetime("Started From", required=True) 
    to = fields.Datetime(string='To', required=True)
    purpose = fields.Text(string='Purpose')
    capacity = fields.Integer(string="Capacity", required=True)
    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')], string='Priority')
    period = fields.Integer(string="Period", required=True)
    requested_by = fields.Many2one("res.users",readonly=True, string="Employee", track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True)
    movement_receiving_request_time = fields.Datetime("Receiving request time")
    operator_driver_name = fields.Many2one("res.users",readonly=True, string="Operator / Driver Name", store=True)
    movement_delivery_time = fields.Datetime("Delivery Time")
    equipment_code = fields.Char(string="EQ./ Vehicle CODE",related="equipment_id.code",readonly=True)
    state = fields.Selection(selection=_STATES, string='Status', index=True, track_visibility='onchange', readonly=True,
                             required=True, copy=False, default='draft')
    reason_reject=fields.Char("Resoan Reject",track_visibility='onchange')
    employee_id = fields.Many2one('hr.employee', string='Employee', related="requested_by.employee_id",readonly=True)

    def button_draft(self):
     self.state = "draft"

    def button_to_officer(self):
        self.state="operation_officer_approve"

    def button_cancel(self):
     self.state="cancel"

    def button_to_operation_officer(self):
        self.state = "movement_manager_approve"


    def button_operation_officer_reject(self):
        self.state = "reject"

    def button_movement_manager_reject(self):
     self.state="reject"   

    def button_to_movement_manager(self):
     self.state="done"

    def get_requested_by(self):
        user = self.env.user.id
        return user

    def _get_default_department(self):
        return self.env.user.department_id.id if self.env.user.department_id else False

    @api.depends('requested_by')
    def _compute_employee_contract(self):
        for contract in self.filtered('requested_by'):
            contract.job_id = contract.requested_by.job_id

    @api.depends('department_id')
    def get_line_manager(self):
        if self.department_id:
            self.line_manager_id = self.department_id.manager_id.user_id

    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('name_seq', 'New') == 'New':
                val['name_seq'] = self.env['ir.sequence'].next_by_code('vehicle.request') or 'New'

        return super(VehicleEquipmentRegulationForm, self).create(vals)

    @api.constrains('to')
    def check_non_zero_end_meeting(self):
        if self.started_from >= self.to:
                raise ValidationError("End time should be after start time!")

    @api.constrains('movement_delivery_time')
    def check_movement_delivery_time(self):
        if self.movement_receiving_request_time >= self.movement_delivery_time:
                raise ValidationError("Delivery time should be after request time!")