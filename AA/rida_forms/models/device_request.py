from odoo import fields, models, api
from odoo.exceptions import UserError


class DeviceRequest(models.Model):
    _name = 'device.request'
    _order = "create_date desc"
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    state = fields.Selection(
        [('draft', 'Draft'), ('lmn_approve', 'Waiting Line Manager Approval'), ('ict_approved', 'ICT Approval'),
         ('confirm', 'Confirmed'),
         ('reject', 'reject'), ],
        string='Status', default='draft', tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Requester Name:", required=True, )
    company_id = fields.Many2one("res.company", string="Company", related="employee_id.company_id", store=True,
                                 readonly=True)
    phone = fields.Char(string="Phone", related='employee_id.mobile_phone')
    email = fields.Char(string="Email", related='employee_id.work_email')
    department_id = fields.Many2one('hr.department', string="Department/Section:", related='employee_id.department_id',
                                    readonly=True, store=True)
    job_id = fields.Many2one('hr.job', string="Job Title:", related='employee_id.job_id', readonly=True)
    cust_id = fields.Many2one(comodel_name="it.custody.type", string="Device Type", required=True)
    description = fields.Text('Additional Requirements/Specifications:')
    prov_id = fields.Many2one('res.users', string='Provided By', tracking=True)
    prov_date_approval = fields.Datetime(string='Date Approve')
    emp_l_mng = fields.Many2one('res.users', string="Line Manager Approval", readonly=1)
    emp_l_mng_date = fields.Datetime(string='Date Approve', readonly=1)
    date = fields.Date(default=fields.Date.today())
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('device.request.code') or ' '

        return super(DeviceRequest, self).create(vals)

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(DeviceRequest, self).unlink()

    def set_to_draft(self):
        self.emp_l_mng = False
        self.emp_l_mng_date = False
        self.prov_id = False
        self.prov_date_approval = False
        return self.write({'state': 'draft'})

    def set_submit(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                pass
            else:
                if rec.employee_id.user_id:
                    employee_user = rec.employee_id.user_id
                    if employee_user != rec.env.user:
                        raise UserError("Sorry. Your are not authorized to approve this document!")
        return self.write({'state': 'lmn_approve'})

    def set_confirm(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                pass
            else:
                if rec.employee_id.user_id.line_manager_id:
                    line_manager = rec.employee_id.user_id.line_manager_id
                    if not line_manager or line_manager != self.env.user:
                        raise UserError("Sorry. Your are not authorized to approve this document!")
        self.emp_l_mng = self.env.user
        self.emp_l_mng_date = fields.Datetime.now()
        return self.write({'state': 'ict_approved'})

    def set_approve(self):
        self.prov_id = self.env.user
        self.prov_date_approval = fields.Datetime.now()
        return self.write({'state': 'confirm'})


class RealocationDeviceRequest(models.Model):
    _name = 'realocation.device.request'
    _order = "create_date desc"
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    state = fields.Selection(
        [('draft', 'Draft'), ('lmn_approve', 'Waiting Line Manager Approval'), ('ict_approved', 'ICT Approval'),
         ('confirm', 'Confirmed'),
         ('reject', 'reject'), ],
        string='Status', default='draft', tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Requester Name:", required=True, )
    company_id = fields.Many2one("res.company", string="Company", related="employee_id.company_id", store=True,
                                 readonly=True)
    from_where = fields.Char(string="From", required=True, )
    to_where = fields.Char(string="To", required=True, )
    phone = fields.Char(string="Phone", related='employee_id.mobile_phone')
    email = fields.Char(string="Email", related='employee_id.work_email')
    department_id = fields.Many2one('hr.department', string="Department/Section:", related='employee_id.department_id',
                                    readonly=True, store=True)
    job_id = fields.Many2one('hr.job', string="Job Title:", related='employee_id.job_id', readonly=True)
    cust_id = fields.Many2one(comodel_name="it.custody.type", string="Device Type", required=True)
    description = fields.Text('IT comment & Recommendation / Specifications:')
    date = fields.Date(default=fields.Date.today())
    emp_l_mng = fields.Many2one('res.users', string="Line Manager Approval", readonly=1)
    emp_l_mng_date = fields.Datetime(string='Date Approve', readonly=1)
    prov_id = fields.Many2one('res.users', string='Provided By', tracking=True)
    prov_date_approval = fields.Datetime(string='Date Approve')
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('realocation.device.request') or ' '

        return super(RealocationDeviceRequest, self).create(vals)

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(RealocationDeviceRequest, self).unlink()

    def set_to_draft(self):
        self.emp_l_mng = False
        self.emp_l_mng_date = False
        self.prov_id = False
        self.prov_date_approval = False
        return self.write({'state': 'draft'})

    def set_submit(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                pass
            else:
                if rec.employee_id.user_id:
                    employee_user = rec.employee_id.user_id
                    if employee_user != rec.env.user:
                        raise UserError("Sorry. Your are not authorized to approve this document!")
        return self.write({'state': 'lmn_approve'})

    def set_confirm(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                pass
            else:
                if rec.employee_id.user_id.line_manager_id:
                    line_manager = rec.employee_id.user_id.line_manager_id
                    if not line_manager or line_manager != self.env.user:
                        raise UserError("Sorry. Your are not authorized to approve this document!")
        self.emp_l_mng = self.env.user
        self.emp_l_mng_date = fields.Datetime.now()
        return self.write({'state': 'ict_approved'})

    def set_approve(self):
        self.prov_id = self.env.user
        self.prov_date_approval = fields.Datetime.now()
        return self.write({'state': 'confirm'})
