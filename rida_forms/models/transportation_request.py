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
    ('close', 'Closed'),
]






class TransportationRequest(models.Model):
    _name = 'transportation.request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Transportation Request'
    _rec_name = "name_seq"

    
    
    name_seq = fields.Char("Number", required=True, index=True, default=lambda self: _('New'), copy=False) 
    date_request = fields.Date("Request Date - تاريخ الطلب",default=fields.Date.context_today, required=True)
    # date = fields.Date(readonly=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'refused': [('readonly', False)]}, default=fields.Date.context_today, string="Expense Date")
    destination_from = fields.Char("From - ‫من‬", required=True)
    destination_to = fields.Char("To - ‫إلى‬", required=True)
    purpose = fields.Selection([('internal_business_task', 'Internal business task - ‫مهمة ‬عمل داخل‬‬ الوﻻية'), ('business_trip', 'Business trip - رحلة‬ ‫عمل'), ('regular_transportation', 'Regular transportation trip - ‫ترحيل‬ منتظم')], 
                                 string='Purpose - ‫الغرض‬', track_visibility='onchange')
    reason = fields.Text("Reason - اﻻسباب", required=True)
    # time_request = fields.time("Time",default=fields.time.context_today, required=True)  
    # time_request = fields.Datetime(string='Time', required=True, compute="_compute_time")
    expected_departure = fields.Datetime("Expected departure date - تاريخ التحرك ‫المقترح", required=True)
    # time_of_departure = fields.Integer("Duration - زمن‬ التحرك", track_visibility='onchange', required=True)
    other_requirements = fields.Text("Other requirements - مطلوبات‬ أخرى‬")   
    requested_by = fields.Many2one("res.users",readonly=True, string="Employee - اﻻسم", track_visibility='onchange',
                                   default=lambda self: self.get_requested_by(), store=True)
    # department_id = fields.Many2one('hr.department', string='Department - اﻻدارة',
    #                                 default=lambda self: self._get_default_department(),readonly=True)
    department_id = fields.Many2one('hr.department', string='Department - اﻻدارة', related="requested_by.employee_ids.department_id",readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', related="requested_by.employee_id",readonly=True)
    job_id = fields.Many2one('hr.job', related="requested_by.employee_ids.job_id", string='Job Title - ‫الوظيفة‬',readonly=True)
    admin_comment = fields.Text("Admin Comment - تعليق ‫الشئون‬ اﻻدارية")
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

        if self.purpose=='business_trip':
            if self.expected_departure:
                d = dateutil.parser.parse(str(self.expected_departure)).date()
                checked_day=self.date_request+relativedelta(days =+ 3)

                print ("###################",checked_day)

                if d< checked_day:
                    raise UserError("The date of departure must be  three days after date of request")

            self.state="line_approve"
        else:
            self.state="line_approve"


    # def _compute_time(self):
    #     for rec in self:
    #      # if rec.time_request:
    #      #  rec.datetime.strftime(self.time_request, "%H:%M:%S")
    #        if rec.date_request:
    #         rec.time_request = datetime.strftime(rec.date_request, "%H:%M:%S")



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
                val['name_seq'] = self.env['ir.sequence'].next_by_code('transportation.request') or 'New'
        
        return super(TransportationRequest, self).create(vals)




    @api.constrains('purpose')
    def check_non_purpose(self):
        if self.purpose is False:
            raise UserError("Please add Purpose! - ‫الغرض من وسيلة‬ ‫نقل‬ ‫")
