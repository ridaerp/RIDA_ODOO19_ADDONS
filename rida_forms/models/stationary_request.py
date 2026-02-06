from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_STATES = [
    ('draft', 'Draft'),
    ('adm_man_approve', 'Admin Affirm'),
    ('reject', 'Rejected'),
    ('cancel', 'Cancelled'),
    ('close', 'Closed'),
]

class StationaryRequest(models.Model):
    _name = 'stationary.request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Stationary Request'
    _rec_name = 'name_seq'
    _order = 'name_seq desc'

    name_seq = fields.Char("Number", required=True, index=True, default=lambda self: _('New'), copy=False)
    date_request = fields.Date("Request Date", default=fields.Date.context_today, required=True)
    requested_by = fields.Many2one(
        "res.users",
        readonly=True,
        string="Requested By",
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
    stationary_line_ids = fields.One2many('stationary.request.line', 'stationary_id', string='Stationary Lines')


    @api.onchange('employee_id')
    def _onchange_employee_id_update_company(self):
        for rec in self:
            rec.company_id = rec.employee_id.company_id if rec.employee_id else False

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Only Draft Records Can Be Deleted!")

        return super(StationaryRequest, self).unlink()

    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('name_seq', 'New') == 'New':
                val['name_seq'] = self.env['ir.sequence'].next_by_code('stationary.request') or 'New'

        return super(StationaryRequest, self).create(vals)

    def action_submit(self):
        for rec in self:
            rec.state = 'adm_man_approve'


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
                message = "Admin affirmation required."
            else:
                continue

            for user in users:
                rec.activity_schedule(
                    'master_data.mail_act_master_data_approval',
                    user_id=user.id,
                    note=message,
                )

class StationaryRequestLine(models.Model):
    _name = 'stationary.request.line'

    stationary_id = fields.Many2one('stationary.request', string='Stationary Request', ondelete='cascade')
    state = fields.Selection(related='stationary_id.state', store=False)
    product_id = fields.Many2one('product.product', string='Item / الصنف',domain="[('categ_id', '=', 411)]")
    qty_req = fields.Float('Quantity Requested / الكمية المطلوبة')
    qty_rec = fields.Float('Quantity Received / الكمية المستلمة')
    remark = fields.Char(string='الملاحظات/ Remarks')