from odoo import fields , api , models , _
import datetime
from dateutil.relativedelta import relativedelta

class employee_rotation(models.Model):
    _name = 'employee.rotation'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Employee Movement'
    _rec_name = 'employee_id'

    date = fields.Date("Date", default=datetime.datetime.now().date(), readonly=True)
    employee_id = fields.Many2one("hr.employee", "Employee", required=True)
    department_id = fields.Many2one("hr.department","Department",)
    job_id = fields.Many2one("hr.job", "Job Title",)
    n_department_id = fields.Many2one("hr.department", "New Department")
    n_job_id = fields.Many2one("hr.job", "New Job Title")
    state = fields.Selection([
        ('draft','Draft'),
        ('hr_manager','HR Manager Approval'),
        ('approve', 'Approved'),
        ('reject', 'Rejected')
    ], default='draft',track_visibility='onchange')
    company_id = fields.Many2one("res.company", string="Company")
    new_company = fields.Many2one("res.company", string="New Company")
    note = fields.Text("Note")
    movement_type = fields.Selection(string='Movement Type', selection=[('rotation', 'Rotation'), ('transfare', 'Transfer'),('temp_transfare', 'Temporary Transfer'), ('secondment', 'Secondment'),('to_project', 'Assign to Project')])

    
    @api.depends('employee_id.department_id','employee_id.job_id')
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            rec.department_id = rec.employee_id.department_id
            rec.job_id = rec.employee_id.job_id
            rec.company_id = rec.employee_id.company_id

    def update_activities(self):
        for rec in self:
            users = []
            rec.activity_unlink(['hr_employee_rotation.mail_act_approval'])
            if rec.state not in ['draft','hr_manager','approve','reject']:
                continue
            message = ""
            if rec.state == 'hr_manager':
                users = self.env.ref('base_rida.rida_hr_manager_notify').user_ids
                message = "Approve"

            elif rec.state == 'reject':
                users = [self.create_uid]
                message = "Cancelled"
            for user in users:
                self.activity_schedule('hr_employee_rotation.mail_act_approval', user_id=user.id, note=message)

    def action_submit(self):
        for rec in self:
            rec.state = 'hr_manager'
            rec.update_activities()
    
    def hr_manager_approve(self):
        for rec in self:
            rec.sudo().employee_id.company_id = rec.new_company if rec.new_company else rec.company_id
            rec.sudo().employee_id.department_id = rec.n_department_id if rec.n_department_id else rec.department_id
            rec.sudo().employee_id.job_id = rec.n_job_id if rec.n_job_id else rec.job_id
            if rec.sudo().employee_id:
                rec.sudo().employee_id.department_id = rec.n_department_id if rec.n_department_id else rec.department_id
                rec.sudo().employee_id.company_id = rec.new_company if rec.new_company else rec.company_id
                rec.sudo().employee_id.job_id = rec.n_job_id if rec.n_job_id else rec.job_id
            rec.state = 'approve'
        self.activity_unlink(['hr_employee_rotation.mail_act_approval'])
    
    def action_reject(self):
        for rec in self:
            rec.state = 'reject'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Only draft records can be deleted!")
        
class hrEmployee(models.Model):
    _inherit = 'hr.employee'

    def compute_rotation_count(self):
        for record in self:
            record.rotation_count = self.env['employee.rotation'].search_count(
                [('employee_id', '=', self.id)])

    rotation_count = fields.Integer(compute='compute_rotation_count')

    def get_rotation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rotation',
            'view_mode': 'list',
            'res_model': 'employee.rotation',
            'domain': [('employee_id', '=', self.id)],
            'context': "{'create': False}"
        }
