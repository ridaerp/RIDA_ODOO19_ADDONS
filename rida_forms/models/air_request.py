from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import datetime
import dateutil
from dateutil.relativedelta import relativedelta



_STATES = [
    ('draft', 'Draft'),
    ('line_approve', 'Waiting Department Manager Approval'),
    ('c-level_approval', 'Waiting For C-Level Approval'),
    ('Adm_man_approve', 'Admin manager Approval'),
    ('reject', 'Rejected'),
    ('cancel', 'Cancelled'),
    # comment by ekhlas ('done', 'Done'),
    ################## change string by ekhlas ##########
    ('done', 'Done'),
    ########################## ekhlas code##################
    # ('purchase', 'Purchase Order'),
    ('close', 'Closed'),
]



# air_booking_request_amendment


class AirBookingRequestAmendment(models.Model):
    _name = 'air.request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Air Booking Request'
    _rec_name = "name_seq"

    
    
    name_seq = fields.Char("Number", required=True, index=True, default=lambda self: _('New'), copy=False) 
    date_request = fields.Date("Request Date",default=fields.Date.context_today, required=True)
    destination_from = fields.Char("Destination From", required=True)
    destination_to = fields.Char("To", required=True)
    travel_details = fields.Selection([('deployment', 'Deployment'), ('secondment', 'Secondment'), ('site_visit', 'Site visit')], 
                                 string='Travel Details', track_tracking=True)
    travel_date = fields.Date("Travel date")
    travel_amended_date = fields.Date("Travel Amended date")
    travel_for_amended_date = fields.Date("Travel date")
    request_received_date = fields.Date("Request received date")
    itinerary = fields.Char("Itinerary")
    itinerary_date = fields.Date("Date")
    return_date = fields.Date("Return date", required=True)
    duty_station = fields.Char("Duty station")   
    requested_by = fields.Many2one("res.users",readonly=True, string="Employee", track_tracking=True,
                                   default=lambda self: self.get_requested_by(), store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', related="requested_by.employee_id",readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', related="requested_by.employee_ids.department_id",readonly=True)
    job_id = fields.Many2one('hr.job', related="requested_by.employee_ids.job_id", string='Job Title',readonly=True)
    admin_comment = fields.Text("Admin Comment")
    state = fields.Selection(selection=_STATES, string='Status', index=True, track_tracking=True, readonly=True,
                             required=True, copy=False, default='draft')

    approve_by = fields.Many2one('res.users', 'Approve by', track_tracking=True
                                   , store=True, readonly=True)


    reason_reject=fields.Char("Resoan Reject",track_tracking=True)
    line_manager_id = fields.Many2one('res.users', string="Line Manager", compute='get_line_manager', store=True)
    
    company_id = fields.Many2one('res.company', related="requested_by.company_id", store=True,readonly=True)


    def button_draft(self):
     self.state = "draft"

    def button_to_department_manger(self):

        if self.travel_date:
            d = dateutil.parser.parse(str(self.travel_date)).date()
            checked_day=self.date_request+relativedelta(days =+ 14)

            print ("###################",checked_day)

            if d< checked_day:
                raise UserError("The date of departure must be Fourteen days after date of request")

        self.state="line_approve"



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

            rec.state = "c-level_approval"




    def button_to_c_level_approval(self):
            self.state = "Adm_man_approve"




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


    def button_c_level_reject(self):
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
                val['name_seq'] = self.env['ir.sequence'].next_by_code('air.request') or 'New'

        return super(AirBookingRequestAmendment, self).create(vals)




    @api.constrains('travel_details')
    def check_non_travel_details(self):
        if self.travel_details is False:
            raise UserError("Please add Travel Details!")



