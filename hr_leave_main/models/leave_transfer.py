from odoo import fields , api , models , _
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError


    
class hrLeavetransferLine(models.Model):
    _name = 'hr.leave.transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Leave Transfer'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee',default=lambda  self: self._get_employee())
    leave_type  = fields.Many2one(comodel_name='hr.leave.type',domain=[('leave_type','=','annual')] ,string='Leave')
    days  = fields.Integer(string='# of Days to Transfer')
    company_id = fields.Many2one("res.company", string="Company", related="employee_id.company_id", store=True,readonly=True)
    state  = fields.Selection([
        ('draft', 'Draft'),
        ('dept_manager', 'Department Manager Approve'),
        ('hr_manager', 'HR Manager Approve'),
        ('approve','Approved'),
        ('reject','Rejected'),
    ], string='Status', default = 'draft',track_tracking=True)

    def _get_employee(self):
        if len(self.env.user.employee_ids) > 0:
            employee = self.env.user.employee_ids[0].id
            return employee or False

    def action_submit(self):
        for rec in self:
            rec.state = 'dept_manager'

    def action_dpt_mgr_approve(self):
        for rec in self:
            if rec.employee_id.parent_id.user_id.id == self.env.user.id:
                rec.state = 'hr_manager'
            else:
                raise UserError('Only Direct Manager Can Approve!')

    def action_hr_mgr_approve(self):
        for rec in self:
            rec.state = 'approve'

    def action_reject(self):
        for rec in self:
            rec.state = 'reject'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def unlink(self):
        for rec in self:
            if not rec.state == "draft":
                raise UserError("Only Draft Records Can Be Deleted")
            return super(hrLeavetransferLine, self).unlink()
