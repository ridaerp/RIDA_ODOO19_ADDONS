from odoo import models, fields, api, _
from odoo.exceptions import UserError

class QualityNcr(models.Model):
    _name = 'quality.ncr'
    _description = 'Non-Conformance Report'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _order = 'name desc'


    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Detected By', default=lambda self: self.env.user, tracking=True)
    audit_name = fields.Many2one('res.users', string='Auditor Name', default=lambda self: self.env.user, tracking=True)
    emp_assign_id = fields.Many2one('res.users', string='Assign To',tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('qhse', 'QHSE Manager'),
        ('department_manager', 'Waiting Dept Manager'),
        ('waiting_employee', 'Waiting Auditee Employee'),
        ('waiting_approve_department_manager', 'Waiting Dept Manager Approve'),
        ('audit_verifier', 'Auditor Verifier'),
        ('qhse_manager', 'QHSE Manager'),
        ('w_depr_mng_close', 'Waiting Dept Manager Confirmation'),
        ('auditor_represent_verify', 'Auditor Representative Verifier'),
        ('closed', 'Closed'),
        ('reject', 'rejected')
    ], string='Status', default='draft', track_visibility='onchange')
    source = fields.Selection([
        ('client_internal', 'Client/Internal Complaint'),
        ('audit', 'Internal Audit/Inspection'),
        ('other', 'Other')
    ], string='NC Source')
    date = fields.Datetime(default=fields.Datetime.now(),string='Date recorded')
    department_id = fields.Many2one('hr.department', string='Department')
    procedure_id = fields.Many2one(comodel_name="qhse.procedure", string="Process/Activity")
    description_of_ncr = fields.Text(string='Description of Non-Conformance')
    potential_causes = fields.Text(string='Potential Causes')
    proposed_corrective_action = fields.Text(string='Proposed Corrective Action')
    expected_date_corrective_action = fields.Date(string='Expected Date for Corrective Action')
    qhse_dept_use_only = fields.Text(string="Verification / effectiveness of the corrective action")
    note = fields.Html("Note")
    #### Approval
    qhse_manager = fields.Many2one('res.users', string="QHSE Approval", readonly=1)
    qhse_approval_date = fields.Datetime(string='QHSE Date Approve', readonly=1)
    close_ncr_person = fields.Many2one('res.users', string="Person Who Close NCR", readonly=1)
    ncr_person_approval_date = fields.Datetime(string='NCR Date Close', readonly=1)
    dpt_manager = fields.Many2one('res.users', string="Auditee/Concerned Person", readonly=1)
    dpt_approval_date = fields.Datetime(string='Auditee/Concerned Date Approve', readonly=1)
    dpt_manager_the_complete = fields.Many2one('res.users', string="Employee That Complete NCR", readonly=1)
    dpt_approval_date_complete = fields.Datetime(string='Date Of Complete NCR', readonly=1)



    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('ncr.request') or ' '

        return super(QualityNcr, self).create(vals)


    def set_submit(self):
        if not self.req_id.id == self.env.user.id:
            raise UserError('Sorry, Only requester can submit this document!')
        return self.write({'state': 'qhse'})

    def set_l_mng_confirm(self):
        line_manager = False
        try:
            line_manager = self.req_id.line_manager_id
        except:
            line_manager = False
        if not line_manager or line_manager != self.env.user:
            raise UserError("Sorry. Your are not authorized to approve this document!")

        self.qhse_manager = self.env.user
        self.qhse_approval_date = fields.Datetime.now()
        return self.write({'state': 'department_manager'})

    def set_l_dept_mng_confirm(self):
        return self.write({'state': 'waiting_employee'})

    def set_waiting_employee_audi(self):
        if not self.emp_assign_id.id == self.env.user.id:
            raise UserError('Sorry, Only Auditee Employee can Approve this document!')
        return self.write({'state': 'waiting_approve_department_manager'})

    def set_waiting_dept_approve(self):
        self.dpt_manager = self.env.user
        self.dpt_approval_date = fields.Datetime.now()
        return self.write({'state': 'audit_verifier'})

    def set_l_auditor_verfiy_confirm(self):
        if not self.audit_name.id == self.env.user.id:
            raise UserError('Sorry, Only Auditor Verifier can Approve this document!')
        return self.write({'state': 'qhse_manager'})
    
    def set_l_qhse_mng_confirm(self):
        return self.write({'state': 'w_depr_mng_close'})

    def set_w_dept_mng_confirm(self):
        return self.write({'state': 'w_depr_mng_close'})

    def set_auditor_represent_confirm(self):
        self.dpt_manager_the_complete = self.env.user
        self.dpt_approval_date_complete = fields.Datetime.now()
        return self.write({'state': 'auditor_represent_verify'})



    def done(self):
        if not self.audit_name.id == self.env.user.id:
            raise UserError('Sorry, Only Auditor Verifier can Approve this document!')
        self.close_ncr_person = self.env.user
        self.ncr_person_approval_date = fields.Datetime.now()
        return self.write({'state': 'closed'})


    def set_to_draft(self):
        return self.write({'state': 'draft'})

    def return_to_dept_mng_close(self):
        return self.write({'state': 'w_depr_mng_close'})

    def return_to_dpt_mng(self):
        return self.write({'state': 'department_manager'})

    def return_to_employee_audit(self):
        return self.write({'state': 'waiting_employee'})

    def return_to_audit_verify(self):
        return self.write({'state': 'audit_verifier'})

    def return_to_dept_mng(self):
        return self.write({'state': 'waiting_approve_department_manager'})



    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(ModificationRequest, self).unlink()

