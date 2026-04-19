from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_STATES = [
    ('draft', 'Draft'),
    ('hr_approve', 'Waiting HR/Admin Manager Approval'),
    ('adm_man_approve', 'Admin Affirm'),
    ('reject', 'Rejected'),
    ('cancel', 'Cancelled'),
    ('close', 'Closed'),
]

class ResidenceRequest(models.Model):
    _name = 'residence.request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Residence Request'
    _rec_name = 'name_seq'
    _order = 'name_seq desc'

    def _get_employee(self):
        if len(self.env.user.employee_ids) > 0:
            employee = self.env.user.employee_ids[0].id
            return employee or False

    name_seq = fields.Char("Number", required=True, index=True, default=lambda self: _('New'), copy=False)
    date_request = fields.Date("Request Date", default=fields.Date.context_today, required=True)
    requested_by = fields.Many2one("res.users", readonly=True, string="Requested By", tracking=True,
                                   default=lambda self: self.get_requested_by(), store=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", default=lambda self: self._get_employee())
    department_id = fields.Many2one('hr.department', string='Department')
    job_id = fields.Many2one('hr.job', string='Job Title')
    company_id = fields.Many2one('res.company', string='Company')
    grade_id = fields.Many2one('hr.grade.configuration', string='Grade')
    purpose = fields.Selection([('visitor', 'Visitor'),
                                     ('per_cont', 'Permanent Contract'),],
                                    required=True, default='per_cont',tracking=True)
    num_of_days = fields.Integer(string='Number Of Days')
    zone_id = fields.Many2one('zone', string='Zone')
    block_id = fields.Many2one('block', string='Unit/Block No')
    room_id = fields.Many2one('office.room', string='Unit /الغرفة', tracking=True)
    state = fields.Selection(selection=_STATES, string='Status', index=True, tracking=True, readonly=True,
                             required=True, copy=False, default='draft')


    @api.onchange('zone_id')
    def _onchange_zone_id(self):
        domain = {}
        if self.zone_id:
            domain = {
                'block_id': [('zone_id', '=', self.zone_id.id)]
            }
        else:
            domain = {
                'block_id': []
            }

        self.block_id = False
        self.room_id = False

        return {
            'domain': domain
        }

    @api.onchange('block_id')
    def _onchange_block_id(self):
        for rec in self:
            return {
                'domain': {
                    'room_id': [('block_id', '=', rec.block_id.id)]
                }
            }

    def get_requested_by(self):
        user = self.env.user.id
        return user

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Only Draft Records Can be Deleted!")

        return super(ResidenceRequest, self).unlink()



    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('name_seq', 'New') == 'New':
                val['name_seq'] = self.env['ir.sequence'].next_by_code('residence.request') or 'New'

        return super(ResidenceRequest, self).create(vals)

    def action_submit(self):
        for rec in self:
            rec.state = 'hr_approve'

    def action_hr_approve(self):
        for rec in self:
            rec.state = 'adm_man_approve'
        self.activity_update()

    def action_close(self):
        for rec in self:
            rec.state = 'close'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_reject(self):
        for rec in self:
            rec.state = 'reject'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def activity_update(self):
        for rec in self:
            rec.activity_unlink(['master_data.mail_act_master_data_approval'])

            users = []
            message = ""

            if rec.state == 'hr_approve':
                users = self.env.ref('base_rida.rida_hr_manager_notify', raise_if_not_found=False).users
                message = "Request waiting for HR/Admin Manager approval."

            elif rec.state == 'adm_man_approve':
                # users = self.env.ref('base_rida.rida_group_admin_affirm', raise_if_not_found=False).users
                message = "Admin affirmation required."

            else:
                continue

            for user in users:
                rec.activity_schedule(
                    'master_data.mail_act_master_data_approval',
                    user_id=user.id,
                    note=message,
                )