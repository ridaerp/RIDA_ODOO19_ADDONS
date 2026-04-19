from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import datetime
import dateutil
from dateutil.relativedelta import relativedelta



_STATES = [
    ('draft', 'Draft'),
    ('line_approve', 'Waiting Department Manager Approval'),
    ('Adm_man_approve', 'Admin manager Approval'),
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


class MeetingRoomReservation(models.Model):
    _name = 'meeting.request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Meeting Room Reservation'
    _rec_name = "name_seq"

    
    
    name_seq = fields.Char("Number", required=True, index=True, default=lambda self: _('New'), copy=False) 
    date_request = fields.Date("Request Date - ‫تاريخ‬ الطلب",default=fields.Date.context_today, readonly=True)
    # destination_from = fields.Char("Destination From", required=True)
    # destination_to = fields.Char("To", required=True)
    type_of_services = fields.Selection([('coffee_break', 'Coffee break - خدمات بوفيه'), ('no_need', 'No need - ﻻشئ'), ('others', 'Others, Specify - ‫‫أخرى‬ , ‫يرجى‬ التحديد‬  ')], 
                                 string='Type of services - نوع الخدمةالمطلوبة', tracking=True)
    specify = fields.Char("Specify")
    # time_request = fields.time("Time",default=fields.time.context_today, required=True)
    # employee_no = fields.Integer("Employee No", required=True)
    # employee_no = fields.Integer('hr.department', string='Department - اﻻدارة', related="requested_by.employee_ids.department_id",readonly=True)
    # employee_no = fields.Char(related='requested_by.employee_ids.emp_code',string="Employee No",readonly=True)
    # reason = fields.Text("Reason - اﻻسباب", required=True)  
    meeting_date = fields.Date("Meeting date - تاريخ الإجتماع", required=True)
    start_meeting = fields.Datetime("Start - وقت البدء", required=True) 
    end_meeting = fields.Datetime(string='End - وقت اﻻنتهاء', required=True) 
    # start_meeting = fields.Float("Start - وقت البدء", required=True) 
    # end_meeting = fields.Float(string='End - وقت اﻻنتهاء', required=True) 
    no_of_attendees = fields.Integer("No. of attendees - عدد الحضور")
    lcd_screen = fields.Boolean(string="LCD screen - شاشة عرض", default=False)
    laptop = fields.Boolean(string="Laptop - حاسوب محمول", default=False)
    others_electronic_device = fields.Boolean(string="Others, Please Specify - أخرى‬ , ‫يرجى‬ التحديد‬", default=False)
    specify_electronic_device = fields.Char("Specify")
    other_requirements = fields.Text("Other requirements - مطلوبات أخرى")
    # travel_amended_date = fields.Date("Travel Amended date")
    # travel_for_amended_date = fields.Date("Travel date")
    # request_received_date = fields.Date("Request received date")
# itinerary = fields.Char("Itinerary")
    admin_date = fields.Date("Date - التاريخ")
    admin_time = fields.Float(string='Time - الزمن') 
    # return_date = fields.Date("Return date", required=True)
    # time_of_departure = fields.Integer("Duration - زمن‬ التحرك", tracking=True, required=True)
    # duty_station = fields.Char("Duty station")  
    time_request = fields.Float(string='Time - ال‬زمن') 
    requested_by = fields.Many2one("res.users",readonly=True, string="Employee - مقدم‬ الطلب", tracking=True,
                                   default=lambda self: self.get_requested_by(), store=True)
    # department_id = fields.Many2one('hr.department', string='Department - اﻻدارة',
    #                                 default=lambda self: self._get_default_department(),readonly=True)
    department_id = fields.Many2one('hr.department', string='Department - الإداره / القسم', related="requested_by.employee_ids.department_id",readonly=True)
    # job_id = fields.Many2one('hr.job', related="requested_by.employee_ids.job_id", string='Job Title',readonly=True)
    admin_comment = fields.Text("Admin Comment - تعليق المسئوول الإدارى")
    state = fields.Selection(selection=_STATES, string='Status', index=True, tracking=True, readonly=True,
                             required=True, copy=False, default='draft')

    approve_by = fields.Many2one('res.users', 'Approve by', tracking=True
                                   , store=True, readonly=True)


    reason_reject=fields.Char("Resoan Reject",tracking=True)
    line_manager_id = fields.Many2one('res.users', string="Line Manager", compute='get_line_manager', store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', related="requested_by.employee_id",readonly=True)
    note=fields.Text("Description")
    # service_ids = fields.One2many('ict.services','product_id','Services', copy=True, tracking=True)
    
    # company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id)
    # company_id = fields.Many2one('res.company', related="requested_by.company_id", store=True,readonly=True)




    meeting_room_id=fields.Selection([('hq','HQ Meeting Room'),('site','HR Site Training Room'),('fleet','Fleet Dept Training room'),('site2','Site Mine Room')],"Meeting Room")

    def button_draft(self):
     self.state = "draft"

    def button_to_department_manger(self):

        # if self.purpose=='business_trip':
            if self.meeting_date:
                d = dateutil.parser.parse(str(self.meeting_date)).date()
                checked_day=self.date_request+relativedelta(days =+ 1)

                print ("###################",checked_day)

                if d< checked_day:
                    raise UserError("The date of Meeting date must be One day after date of request")

            if self.start_meeting:
                    d = dateutil.parser.parse(str(self.start_meeting)).date()
                    checked_day=self.date_request+relativedelta(days =+ 1)

                    print ("###################",checked_day)

                    if d< checked_day:
                        raise UserError("The date of Start Meeting date must be One day after date of request")


            if self.end_meeting:
                    d = dateutil.parser.parse(str(self.end_meeting)).date()
                    checked_day=self.date_request+relativedelta(days =+ 1)

                    print ("###################",checked_day)

                    if d< checked_day:
                        raise UserError("The date of Meeting date must be One day after date of request")

            self.state="line_approve"
        # else:
        #     self.state="line_approve"






    def button_cancel(self):
     self.state="cancel"

    def button_Adm_man_cancel(self):
     self.state="cancel"


    def button_to_line_manager(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                pass
            else:
                self.ensure_one()
                line_managers = []
                line_manager = False
                try:
                    line_manager = rec.requested_by.line_manager_id
                except:
                    line_manager = False
                # comment by ekhlas
                if not line_manager or line_manager !=rec.env.user :
                    raise UserError("Sorry. Your are not authorized to approve this document!")

            rec.state = "Adm_man_approve"




    # def button_to_c_level_approval(self):
    #     # for rec in self:
    #     #     if self.env.user.has_group('base.group_system'):
    #     #         pass
    #     #     else:
    #     #         self.ensure_one()
    #     #         line_managers = []
    #     #         line_manager = False
    #     #         try:
    #     #             line_manager = rec.requested_by.line_manager_id
    #     #         except:
    #     #             line_manager = False
    #     #         # comment by ekhlas
    #     #         if not line_manager or line_manager !=rec.env.user :
    #     #             raise UserError("Sorry. Your are not authorized to approve this document!")

    #         # rec.state = "Adm_man_approve"

    #         self.state = "Adm_man_approve"




    def button_lm_reject(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                pass
            else:
                self.ensure_one()
                line_managers = []
                line_manager = False
                try:
                    line_manager = rec.requested_by.line_manager_id
                except:
                    line_manager = False
                # comment by ekhlas
                if not line_manager or line_manager !=rec.env.user :
                    raise UserError("Sorry. Your are not authorized to approve this document!")

            rec.state = "reject"

    def button_Adm_man_reject(self):
     self.state="reject"   

    def button_to_Adm_man(self):
     self.state="done"


    def get_requested_by(self):
        user = self.env.user.id
        return user


    def _get_default_department(self):
        return self.env.user.department_id.id if self.env.user.department_id else False


    def _get_default_Job(self):
        return self.env.user.job.id if self.env.user.job_id else False



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
                val['name_seq'] = self.env['ir.sequence'].next_by_code('meeting.request') or 'New'

        return super(MeetingRoomReservation, self).create(vals)

    @api.constrains('start_meeting')
    def check_non_zero_start_meeting(self):
        for rec in self:
            domain = [
                    ('start_meeting', '<=', rec.start_meeting),
                    ('end_meeting', '>', rec.start_meeting),
                    ('meeting_date', '=', rec.meeting_date),
                    ('state', 'not in', ['cancel', 'draft', 'reject','line_approve','Adm_man_approve']),
                    ('id', '!=', rec.id),
                    ('meeting_room_id','=',rec.meeting_room_id)
                ]

            ndelegations = rec.search_count(domain)

            if ndelegations:
                raise UserError(
                   _('There cannot be 2  reservations overlapping on the same day at the same start time.'))





    @api.constrains('end_meeting')
    def check_non_zero_end_meeting(self):
        if self.start_meeting >= self.end_meeting:
                raise ValidationError("End time should be after start time!")
    
        for rec in self:
            domain = [
                    ('start_meeting', '<=', rec.end_meeting),
                    ('end_meeting', '>', rec.end_meeting),
                    ('meeting_date', '=', rec.meeting_date),
                    ('state', 'not in', ['cancel', 'draft', 'reject','line_approve','Adm_man_approve']),
                    ('id', '!=', rec.id),
                    ('meeting_room_id','=',rec.meeting_room_id)

                ]

            ndelegations = rec.search_count(domain)

            if ndelegations:
                raise UserError(
                   _('There cannot be 2  reservations overlapping on the same day at the same end time.'))
