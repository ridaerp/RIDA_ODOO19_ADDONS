from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_STATES = [
    ('draft', 'Draft'),
    ('c_level_approval', 'Waiting Site Manager Approval'),
    ('hr_approve', 'Waiting HR/Admin Manager Approval'),
    ('adm_man_approve', 'Admin Affirm'),
    ('reject', 'Rejected'),
    ('cancel', 'Cancelled'),
    ('close', 'Closed'),
]

class CheckinCampRequest(models.Model):
    _name = 'checkin_camp.request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Check-in Camp Request'
    _rec_name = 'name_seq'
    _order = 'name_seq desc'

    name_seq = fields.Char("Number", required=True, index=True, default=lambda self: _('New'), copy=False)
    date_request = fields.Date("Request Date", default=fields.Date.context_today, required=True)
    requested_by = fields.Many2one(
        "res.users",
        readonly=True,
        string="Requested Employee",
        tracking=True,
        default=lambda self: self.env.user,
    )
    employee_id = fields.Many2one("hr.employee", string="Employee")
    department_id = fields.Many2one('hr.department', string='Department',
                                    related="employee_id.department_id", readonly=True,track_visibility='onchange')
    job_id = fields.Many2one('hr.job', related="employee_id.job_id", string='Job Title', readonly=True,track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Company')
    state = fields.Selection(selection=_STATES, string='Status', index=True, track_visibility='onchange', readonly=True,
                             required=True, copy=False, default='draft')
    checkin_camp_line_ids = fields.One2many('checkin_camp.request.line', 'checkin_camp_id', string='Check-in Camp Lines')


    @api.onchange('employee_id')
    def _onchange_employee_id_update_company(self):
        for rec in self:
            rec.company_id = rec.employee_id.company_id if rec.employee_id else False

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Only Draft Records Can Be Deleted!")

        return super(CheckinCampRequest, self).unlink()



    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('name_seq', 'New') == 'New':
                val['name_seq'] = self.env['ir.sequence'].next_by_code('checkin_camp.request') or 'New'

        return super(CheckinCampRequest, self).create(vals)

    def action_submit(self):
        for rec in self:
            rec.state = 'c_level_approval'

    def action_site_manager_approve(self):
        c_level_id = False
        try:
            c_level_id = self.employee_id.department_id.c_level_id
        except:
            c_level_id = False
        if not c_level_id or c_level_id != self.env.user:
            raise UserError("Sorry. Your are not authorized to approve this document!")
        return self.write({'state': 'hr_approve'})

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

            if rec.state == 'adm_man_approve':
                # users = self.env.ref('base_rida.rida_group_admin_affirm', raise_if_not_found=False).users
                message = "Admin affirmation required."
            elif rec.state == 'hr_approve':
                users = self.env.ref('base_rida.rida_hr_manager_notify', raise_if_not_found=False).users
                message = "Request waiting for HR/Admin Manager approval."

            elif rec.state == 'c_level_approval':
                users = self.env.ref('base_rida.rida_group_site_manager', raise_if_not_found=False).users
                message = "Request waiting for Site Manager approval."

            else:
                continue

            for user in users:
                rec.activity_schedule(
                    'master_data.mail_act_master_data_approval',
                    user_id=user.id,
                    note=message,
                )
class StationaryRequestLine(models.Model):
    _name = 'checkin_camp.request.line'

    checkin_camp_id = fields.Many2one('checkin_camp.request', string='Check-in Camp Request', ondelete='cascade')
    visit_name = fields.Char('Name / الاسم',track_visibility='onchange')
    department_id = fields.Many2one('hr.department', string='Department / الجهة الطالبة', track_visibility='onchange')
    degree = fields.Char('Degree / الدرجة الوظيفيه')
    date_arrival = fields.Date(string='Date Of Arrival / تاريخ الوصول',track_visibility='onchange')
    duration = fields.Integer(string='Residence time / مدة الاسكان',track_visibility='onchange')
    remark = fields.Char(string='الملاحظات/ Remarks')
    zone_id = fields.Many2one('zone', string='Zone')
    block_id = fields.Many2one('block', string='Block No/ المجمع',track_visibility='onchange')
    room_id = fields.Many2one('office.room', string='Unit /الغرفة',track_visibility='onchange')


    @api.onchange('zone_id')
    def _onchange_zone_id(self):
        for rec in self:
            return {
                'domain': {
                    'block_id': [('zone_id', '=', 19)]
                }
            }

    @api.onchange('block_id')
    def _onchange_block_id(self):
        for rec in self:
            return {
                'domain': {
                    'room_id': [('block_id', '=', rec.block_id.id)]
                }
            }

