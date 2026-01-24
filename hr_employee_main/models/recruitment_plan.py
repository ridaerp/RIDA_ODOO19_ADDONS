from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, format_date
from odoo import fields, models, api
from odoo.exceptions import UserError


class RecruitmentPlan(models.Model):
    _name = 'recruitment.plan'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    @api.model
    def default_get(self, fields):
        res = super(RecruitmentPlan, self).default_get(fields)
        if res.get('req_id', False):
            emp = self.env['hr.employee'].sudo().search([('user_id', '=', res['req_id'])],
                                                        limit=1)
            if not (res.get('department_id', False) or res.get('job_req_id', False)):
                res.update({
                    'department_id': emp.department_id.id,
                    'job_req_id': emp.job_id.id
                })
        return res

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    date = fields.Date(default=fields.Date.today())
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True)
    department_id = fields.Many2one('hr.department', string="Department")
    job_req_id = fields.Many2one('hr.job', string='Job Title')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    description = fields.Text()
    state = fields.Selection(
        [('draft', 'Draft'),
         ('w_hr_m', 'HR Manager Verify'),
         ('ccso', 'CCSO Approve'),
         ('coo', 'COO Approve'),
         ('approved', 'Approved'),
         ('reject', 'reject')],
        string='Status', default='draft', track_visibility='onchange')
    state_ccso = fields.Selection(related='state')
    user_type = fields.Selection(related="req_id.user_type")
    recr_plain_line_ids = fields.One2many(comodel_name="recruitment.plan.line", inverse_name="request_id",
                                          string="Recuitment Plan Line", copy=1)
    recruitment_count = fields.Integer(compute='compute_recruitment_count')

    @api.onchange('req_id')
    def onchange_req_id(self):
        if not self.req_id.user_type:
            raise UserError('The Employee Type if NOT Set')


    def compute_recruitment_count(self):
        self.recruitment_count = self.env['recruitment.request'].search_count([('reru_plan_id', '=', self.id)])

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('reur.plan.code') or ' '
        res = super(RecruitmentPlan, self).create(vals)
        return res

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")

        return super(RecruitmentPlan, self).unlink()

    @api.onchange('recr_plain_line_ids')
    def check_for_doubles(self):
        exist_job_list = []
        for line in self.recr_plain_line_ids:
            if line.job_id.id in exist_job_list:
                raise UserError('The Job Title in Recruitment Plan Line is duplicate')
            exist_job_list.append(line.job_id.id)

    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    def action_submit(self):
        return self.write({'state': 'w_hr_m'})

    def action_hr_manager_approve(self):
        if self.user_type == 'hq':
            return self.write({'state': 'ccso'})
        if self.user_type == 'site' or self.user_type == 'fleet':
            return self.write({'state': 'coo'})

    def approve_operation_director(self):
        return self.write({'state': 'approved'})

    def approve_ccso(self):
        return self.write({'state': 'approved'})


    def create_recr_req(self):
        self.ensure_one()
        res = self.env['recruitment.request'].create({'department_id':self.department_id.id,'reru_plan_id':self.id,})
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'recruitment.request',
            'res_id': res.id,
            'context': {'form_view_initial_mode': 'edit'},
        }

    def set_recruitment_request(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Recruitment Request',
            'view_mode': 'tree,form',
            'res_model': 'recruitment.request',
            'domain': [('reru_plan_id', '=', self.id)],
            'context': "{'create': False}"
        }


class RecruitmentPlanLine(models.Model):
    _name = 'recruitment.plan.line'

    request_id = fields.Many2one("recruitment.plan")
    job_id = fields.Many2one('hr.job', string="Job Title")
    number_required = fields.Integer(string="Number Required")
    hiring_date = fields.Date(string="Date (Period for Hiring)")
    remarks = fields.Text("Remarks")
