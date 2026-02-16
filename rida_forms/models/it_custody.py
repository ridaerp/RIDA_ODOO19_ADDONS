from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ItCustody(models.Model):
    _name = 'it.custody'
    _order = "create_date desc"
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    employee_id = fields.Many2one('hr.employee', string="Employee Name", required=True, )
    department_id = fields.Many2one('hr.department', string="Department", related='employee_id.department_id',
                                    readonly=True, store=True)
    job_id = fields.Many2one('hr.job', string="Position:", related='employee_id.job_id', readonly=True)
    cust_id = fields.Many2one(comodel_name="it.custody.type", string="Device Type", required=True)
    device_name = fields.Char(string="")
    date = fields.Date(required=True, default=fields.Date.today())
    device_model = fields.Char(string="")
    device_ser = fields.Char(string="Device Serial No")
    prov_id = fields.Many2one('res.users', string='Provided By', tracking=True)
    prov_date_approval = fields.Datetime(string='Date Approve')
    description = fields.Text('')
    device_status = fields.Selection([('accept', 'Accepted'), ('unaccept', 'UnAccepted')], string='Status')
    description_clear = fields.Text('Action Required')
    rece_id = fields.Many2one('res.users', string='Received By',
                              tracking=True)
    received_date = fields.Datetime()
    state = fields.Selection(
        [('draft', 'Draft'), ('employee_approve', 'Employee Approval'), ('confirm', 'Confirmed'),
         ('clearance', 'cleared'),
         ('reject', 'reject'), ],
        string='Status', default='draft', tracking=True)
    emp_approval = fields.Many2one('res.users', string="Employee Approval", tracking=True)
    date_approval = fields.Datetime(string='Date Approve')
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('it.custody.code') or ' '

        return super(ItCustody, self).create(vals)

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(ItCustody, self).unlink()

    def set_to_draft(self):
        self.emp_approval = False
        self.date_approval = False
        self.prov_id = False
        self.prov_date_approval = False
        return self.write({'state': 'draft'})

    def set_confirm(self):
        self.prov_id = self.env.user
        self.prov_date_approval = fields.Datetime.now()
        return self.write({'state': 'employee_approve'})

    def set_approve(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                pass
            else:
                if rec.employee_id.user_id:
                    employee_user = rec.employee_id.user_id
                    if employee_user != rec.env.user:
                        raise UserError("Sorry. Your are not authorized to approve this document!")
        self.emp_approval = self.env.user
        self.date_approval = fields.Datetime.now()
        return self.write({'state': 'confirm'})

    def set_to_clearance(self):
        if (self.device_status and self.description_clear):
            self.rece_id = self.env.user
            self.received_date = fields.Datetime.now()
            return self.write({'state': 'clearance'})
        else:
            raise UserError(
                _('Please insert all Clearance information'))


class RemoteAccessRequest(models.Model):
    _name = 'remote.access.request'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string="Employee Name", required=True, )
    department_id = fields.Many2one('hr.department', string="Department", related='employee_id.department_id',
                                    readonly=True, store=True)
    job_id = fields.Many2one('hr.job', string="Position:", related='employee_id.job_id', readonly=True)
    date = fields.Date(required=True, default=fields.Date.today())
    emp_approval = fields.Many2one('res.users', string="Employee Approval", tracking=True)
    date_approval = fields.Datetime(string='Date Approve')
    emp_l_mng = fields.Many2one('res.users', string="Line Manager Approval", readonly=1)
    emp_l_mng_date = fields.Datetime(string='Date Approve', readonly=1)
    ict_approval = fields.Many2one('res.users', string="ICT Director Approval", tracking=True)
    ict_date_approval = fields.Datetime(string='Date Approve')
    prov_id = fields.Many2one('res.users', string='Provided By', tracking=True)
    prov_date_approval = fields.Datetime(string='Date Approve')
    phone = fields.Char(string="Phone", related='employee_id.mobile_phone')
    email = fields.Char(string="Email", related='employee_id.work_email')
    description = fields.Text(string="Describe Purpose of Remote Access", required=True)
    date_from = fields.Date(default=fields.Date.today(), string="From")
    date_to = fields.Date(string="To")
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    state = fields.Selection(
        [('draft', 'Draft'), ('lmn_approve', 'Waiting Line Manager Approval'),
         ('ict_director_approval', 'ICT Director Approval'), ('ict_approved', 'Waiting Technical Team'), ('confirm', 'Confirmed'),
         ('reject', 'reject'), ],
        string='Status', default='draft', tracking=True)
    authorization = fields.Selection(string="", selection=[('approve', 'Approved'), ('denied', 'Denied'), ],
                                     required=False, )
    policy = fields.Boolean(default=False)

    @api.constrains('policy')
    def _policy_validation(self):
        if self.policy == False:
            raise UserError("Check The Policy !!")

    def set_to_draft(self):
        self.emp_l_mng = False
        self.emp_l_mng_date = False
        self.ict_approval = self.env.user
        self.ict_date_approval = fields.Datetime.now()
        self.prov_id = False
        self.prov_date_approval = False
        return self.write({'state': 'draft'})

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(RemoteAccessRequest, self).unlink()

    def set_submit(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                pass
            else:
                if rec.employee_id.user_id:
                    employee_user = rec.employee_id.user_id
                    if employee_user != rec.env.user:
                        raise UserError("Sorry. Your are not authorized to approve this document!")
        self.emp_approval = self.env.user
        self.date_approval = fields.Datetime.now()
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
        return self.write({'state': 'ict_director_approval'})

    def set_ict_director_confirm(self):
        self.ict_approval = self.env.user
        self.ict_date_approval = fields.Datetime.now()
        return self.write({'state': 'ict_approved'})

    def set_approve(self):
        self.prov_id = self.env.user
        self.prov_date_approval = fields.Datetime.now()
        return self.write({'state': 'confirm'})


class ItCustodyType(models.Model):
    _name = 'it.custody.type'
    _description = ''

    name = fields.Char(string="Type", required=True, )
