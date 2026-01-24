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
                                 string='Travel Details', track_visibility='onchange')
    # employee_no = fields.Integer("Employee No", required=True)
    # employee_no = fields.Integer('hr.department', string='Department - اﻻدارة', related="requested_by.employee_ids.department_id",readonly=True)
    # employee_no = fields.Char(related='requested_by.employee_ids.emp_code',string="Employee No",readonly=True)
    # reason = fields.Text("Reason - اﻻسباب", required=True)  
    travel_date = fields.Date("Travel date")
    travel_amended_date = fields.Date("Travel Amended date")
    travel_for_amended_date = fields.Date("Travel date")
    request_received_date = fields.Date("Request received date")
    itinerary = fields.Char("Itinerary")
    itinerary_date = fields.Date("Date")
    return_date = fields.Date("Return date", required=True)
    # time_of_departure = fields.Integer("Duration - زمن‬ التحرك", track_visibility='onchange', required=True)
    duty_station = fields.Char("Duty station")   
    requested_by = fields.Many2one("res.users",readonly=True, string="Employee", track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True)
    # department_id = fields.Many2one('hr.department', string='Department - اﻻدارة',
    #                                 default=lambda self: self._get_default_department(),readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', related="requested_by.employee_id",readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', related="requested_by.employee_ids.department_id",readonly=True)
    job_id = fields.Many2one('hr.job', related="requested_by.employee_ids.job_id", string='Job Title',readonly=True)
    admin_comment = fields.Text("Admin Comment")
    state = fields.Selection(selection=_STATES, string='Status', index=True, track_visibility='onchange', readonly=True,
                             required=True, copy=False, default='draft')

    approve_by = fields.Many2one('res.users', 'Approve by', track_visibility='onchange'
                                   , store=True, readonly=True)


    reason_reject=fields.Char("Resoan Reject",track_visibility='onchange')
    line_manager_id = fields.Many2one('res.users', string="Line Manager", compute='get_line_manager', store=True)
    
    # service_ids = fields.One2many('ict.services','product_id','Services', copy=True, track_visibility='onchange')
    
    # company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id)
    company_id = fields.Many2one('res.company', related="requested_by.company_id", store=True,readonly=True)


    def button_draft(self):
     self.state = "draft"

    def button_to_department_manger(self):

        # if self.purpose=='business_trip':
            if self.travel_date:
                d = dateutil.parser.parse(str(self.travel_date)).date()
                checked_day=self.date_request+relativedelta(days =+ 14)

                print ("###################",checked_day)

                if d< checked_day:
                    raise UserError("The date of departure must be Fourteen days after date of request")

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

            rec.state = "c-level_approval"




    def button_to_c_level_approval(self):
        # for rec in self:
        #     if self.env.user.has_group('base.group_system'):
        #         pass
        #     else:
        #         self.ensure_one()
        #         line_managers = []
        #         line_manager = False
        #         try:
        #             line_manager = rec.requested_by.line_manager_id
        #         except:
        #             line_manager = False
        #         # comment by ekhlas
        #         if not line_manager or line_manager !=rec.env.user :
        #             raise UserError("Sorry. Your are not authorized to approve this document!")

            # rec.state = "Adm_man_approve"

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
        # self.mapped('line_ids').do_cancel()
        # return self.write({'state': 'reject'})
        

        

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
        if vals.get('name_seq', 'New') == 'New':
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('air.request') or 'New'
        result = super(AirBookingRequestAmendment, self).create(vals)
        # result = super(IctDeviceRequest, self).create(vals)
        # if not result.service_ids:
        # if self.time_of_departure:
        #     raise UserError('Please add Services lines!')
        
        return result




    @api.constrains('travel_details')
    def check_non_travel_details(self):
        if self.travel_details is False:
            raise UserError("Please add Travel Details!")



    # @api.constrains('time_of_departure')
    # def check_non_zero(self):
    #     if self.time_of_departure <= 0:
    #         raise UserError("Please add Duration Time! - !الرجاء إضافة زمن‬ التحرك")











    #  # manager to line
    # def button_to_line_manager(self):
    #     for rec in self:
    #         if self.env.user.has_group('base.group_system'):
    #             rec.write({'approve_by': rec.env.user.id})
    #             pass

    #         else:
    #             rec.write({'approve_by': rec.env.user.id})
    #             self.ensure_one()
    #             line_managers = []
    #             today = fields.Date.today()
    #             line_manager = False
    #             try:
    #                 line_manager = self.requested_by.line_manager_id
    #             except:
    #                 line_manager = False
    #             # comment by ekhlas
    #             if not line_manager or not self.user_has_groups('material_request.group_department_manager'):
    #                 raise UserError("Sorry. Your are not authorized to approve this document!")
    #             if not line_manager or line_manager !=rec.env.user :
    #                 raise UserError("Sorry. Your are not authorized to approve this document!")

    #             rec.write({'state': 'ict_HOD_approve'})
        




# class IctDeviceRequest(models.Model):



# class IctService(models.Model):
#     _name = 'ict.service'
#     name = fields.Char("Service Name", required=True)
#     description = fields.Text("Description")
    
# class DeviceTemplateService(models.Model):
#     _name = 'ict.template.service'
#     name = fields.Char("Service Type", required=True)
#     service_id = fields.Many2one('ict.service',string="ICT Service", required=True)
#     # servicess_id = fields.Many2one('ict.template.service',string="Service")
#     # servicess22_id = fields.Many2one(related='servicess_id.service_id', string='servicess22')
#     # department_id = fields.Many2one(related='employee_id.department_id', string='Department', readonly=True)
    
        
# # IctDeviceRequest





# class IctServices(models.Model):
#     _name = 'ict.services'
#     _description = 'IctServices'
#     _inherit = ['mail.thread']
#     ict_service_id = fields.Many2one('ict.service',string="ICT Service", required=True)
#     product_id = fields.Many2one('ict.device.request')
#     service_type_id = fields.Many2one('ict.template.service',string="Service Type", required=True)
    

    