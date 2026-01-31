from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, format_date
from odoo import fields, models, api
from odoo.exceptions import UserError


class RecruitmentRequest(models.Model):
    _name = 'recruitment.request'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    @api.model
    def default_get(self, fields):
        res = super(RecruitmentRequest, self).default_get(fields)
        if res.get('req_id', False):
            emp = self.env['hr.employee'].sudo().search([('user_id', '=', res['req_id'])],
                                                        limit=1)
            if not res.get('department_id', False):
                res.update({
                    'department_id': emp.department_id.id,
                })
        return res


    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    date = fields.Date(default=fields.Date.today())
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True)
    department_id = fields.Many2one('hr.department', string="Department")
    job_req_id = fields.Many2one('hr.job', string='Job Title')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    comments = fields.Text("Additional Comments")
    comments_for_hr = fields.Text("Additional Comments (if any)")
    position_req_other = fields.Text("Specify")
    description = fields.Text("Job Requirements (In terms of qualifications, experience, training, age, etc.)")
    state = fields.Selection(
        [('draft', 'Draft')
        , ('line_mng', 'Waiting Line Manager'),
         ('hr_off', 'HR Officer Verify'),
         ('w_chro', 'HR Manager Approve'),
         ('ccso', 'CCSO Approve'), ('coo', 'COO Approve'),
         ('approved', 'Approved'),
         ('reject', 'reject'),
         ('close', 'Closed')],
        string='Status', default='draft', track_visibility='onchange',tracking=True)
    state_ccso = fields.Selection(related='state')
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    job_location = fields.Many2one('rida.location', string='Job Location')
    number_vacancies = fields.Integer(string="Number Vacancies")
    duration = fields.Float(string='Duration (Days)')
    recr_plan = fields.Selection(
        [('budgeted', 'Budgeted'),
         ('unbudgeted', 'UnBudgeted'),],default='budgeted',
        string='Recruitment Plan')
    recr_type = fields.Selection(
        [('perm', 'Permanent'),
         ('temp', 'Temporary'),],default='perm',
        string='Recruitment Type')
    expected_date = fields.Date(string="Expected employment Start Date")
    reason_recr = fields.Selection(
        [('increasing_wo', 'Increasing workload'),
        ('staff_turn', 'Staff turnover (replacement)'),
        ('need_skill', 'Need for new skill'),
        ('staff_transferred', 'Current staff transferred'),
        ('change_structure', 'Change in structure'),
        ('others', 'Others (specify)')],
        string='Recruitment Plan')
    laptop = fields.Boolean(string="Laptop")
    pc = fields.Boolean(string="PC")
    office_desk = fields.Boolean(string="Office Desk")
    tool_book = fields.Boolean(string="Tool book")
    locker = fields.Boolean(string="Locker")
    ppe = fields.Boolean(string="PPE")
    others = fields.Boolean(string="Others")
    reru_plan_id = fields.Many2one('recruitment.plan',string='RecruitmentPlan')
    # min_grade_id = fields.Many2one('hr.grade.configuration', string="Min Grade")
    # max_grade_id = fields.Many2one('hr.grade.configuration', string="Max Grade")
    min_salary = fields.Float(string='Min Salary')
    max_salary = fields.Float(string='Max Salary')
    user_type = fields.Char(compute='onchange_req')

    @api.depends("req_id")
    def onchange_req(self):
        if self.req_id.user_type:
            self.user_type=self.req_id.user_type
        else:
            raise UserError('The Employee Type if NOT Set')

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('reur.requisition.code') or ' '
            res = super(RecruitmentRequest, self).create(val)
            return res

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(RecruitmentRequest, self).unlink()


    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    def action_close(self):
        return self.write({'state': 'close'})

    def action_submit(self):
        return self.write({'state': 'line_mng'})

    def action_submit_line_mng(self):
        line_manager = False
        try:
            line_manager = self.req_id.line_manager_id
        except:
            line_manager = False
        if not line_manager or line_manager != self.env.user:
            raise UserError("Sorry. Your are not authorized to approve this document!")

        return self.write({'state': 'hr_off'})

    def action_off_approve(self):
        for rec in self:
            rec.state = "w_chro"

    def action_chmo_approve(self):
        if self.user_type == 'site' or self.user_type == 'fleet' or  self.recr_type == 'temp':
            return self.write({'state': 'coo'})
        if self.user_type == 'hq':
            return self.write({'state': 'ccso'})


    def approve_operation_director(self):
        return self.write({'state': 'approved'})

    def approve_ccso(self):
        return self.write({'state': 'approved'})




