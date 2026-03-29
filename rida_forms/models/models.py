from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_STATES = [
    ('draft', 'Draft'),
    ('line_approve', 'Waiting Department Manager Approval'),
    ('ict_HOD_approve', 'Waiting  ICT HOD Approval'),
    ('reject', 'Rejected'),
    ('cancel', 'Cancelled'),
    # comment by ekhlas ('done', 'Done'),
    ################## change string by ekhlas ##########
    ('done', 'Done'),
    ########################## ekhlas code##################
    # ('purchase', 'Purchase Order'),
    ('close', 'Closed'),
]


class resBranch(models.Model):
    _name = 'res.branch'

    name = fields.Char()



class IctDeviceRequest(models.Model):
    _name = 'ict.device.request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'ICT Device Request'
    _rec_name = "name_seq"

    
    name = fields.Char("Full Name")
    name_seq = fields.Char("Number", required=True, index=True, default=lambda self: _('New'), copy=False)
    employee_id = fields.Many2one("res.users", string="Employee", track_tracking=True,
                                   default=lambda self: self.get_requested_by(), store=True)
    requested_by = fields.Many2one("res.users",readonly=True, string="Employee", track_tracking=True,
                                   default=lambda self: self.get_requested_by(), store=True)
    # department_id = fields.Many2one('hr.department', string='Department',
    #                                 default=lambda self: self._get_default_department())
    department_id = fields.Many2one('hr.department', string='Department', related="requested_by.employee_ids.department_id",readonly=True)
    job_id = fields.Many2one('hr.job', related="requested_by.employee_ids.job_id", string='Job Title',readonly=True)
    # job_id = fields.Many2one('hr.job', string="Job Position")
    # job_id = fields.Many2one('hr.job', compute='_compute_employee_contract',
    #     domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", string='Job Position')
    # company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id)
    company_id = fields.Many2one('res.company', related="requested_by.company_id", store=True,readonly=True)
    email = fields.Char("Requested email")
    phone = fields.Integer("Mobile No")
    erp = fields.Boolean("ERP Account")
    requirements = fields.Text("Additional Requirements/Specifications")
    relocation_from = fields.Char("From")
    relocation_to = fields.Char("To")
    date_request = fields.Date("Request Date",default=fields.Date.context_today, required=True)
    state = fields.Selection(selection=_STATES, string='Status', index=True, track_tracking=True, readonly=True,
                             required=True, copy=False, default='draft')

    approve_by = fields.Many2one('res.users', 'Approve by', track_tracking=True
                                   , store=True, readonly=True)


    reason_reject=fields.Char("Resoan Reject",track_tracking=True)
    line_manager_id = fields.Many2one('res.users', string="Line Manager", compute='get_line_manager', store=True)
    # line_manager_id = fields.Many2one('res.users', string="Line Manager", related="requested_by.line_manager_id")
    branch_id = fields.Many2one('res.branch', )
    section = fields.Many2one('hr.department', string='Section')
    service_ids = fields.One2many('ict.services','product_id','Services', copy=True, track_tracking=True)
    

    def button_draft(self):
        self.state = "draft"

    
    def button_to_department_manger(self):  
        self.state="line_approve"

    def button_cancel(self):
        self.state="cancel"


    def get_requested_by(self):
        user = self.env.user.id
        return user


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

            rec.state = "ict_HOD_approve"


    def button_to_ict_HOD(self):
     self.state="done"

    def get_requested_by(self):
        user = self.env.user.id
        return user

    def _get_default_department(self):
        return self.env.user.department_id.id if self.env.user.department_id else False

    def _get_default_Job(self):
        return self.env.user.job.id if self.env.user.job_id else False

    @api.depends('employee_id')
    def _compute_employee_contract(self):
        for contract in self.filtered('employee_id'):
            contract.job_id = contract.employee_id.job_id

    @api.depends('branch_id', 'section', 'department_id')
    def get_line_manager(self):
        if self.branch_id:
            self.line_manager_id = self.branch_id.manager_id.user_id
        elif self.section:
            self.line_manager_id = self.section.manager_id.user_id
        elif self.department_id:
            self.line_manager_id = self.department_id.manager_id.user_id

    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('name_seq', 'New') == 'New':
                val['name_seq'] = self.env['ir.sequence'].next_by_code('device.request') or 'New'
            result = super(IctDeviceRequest, self).create(vals)
            if not result.service_ids:
                raise UserError('Please add Services lines!')
        
        return result


class IctService(models.Model):
    _name = 'ict.service'
    name = fields.Char("Service Name", required=True)
    description = fields.Text("Description")
    
class DeviceTemplateService(models.Model):
    _name = 'ict.template.service'
    name = fields.Char("Service Type", required=True)
    service_id = fields.Many2one('ict.service',string="ICT Service", required=True)

class IctServices(models.Model):
    _name = 'ict.services'
    _description = 'IctServices'
    _inherit = ['mail.thread']
    ict_service_id = fields.Many2one('ict.service',string="ICT Service", required=True)
    product_id = fields.Many2one('ict.device.request')
    service_type_id = fields.Many2one('ict.template.service',string="Service Type", required=True)
    

