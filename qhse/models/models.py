from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class ModificationRequest(models.Model):
    _name = 'modification.request'
    _order = "create_date desc"
    _rec_name = 'code_seq'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _mail_post_access = 'read'
    _order = 'code_seq desc'

    code_seq = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True,
                             readonly=True)
    job_id = fields.Many2one(comodel_name="hr.job", string="Job Title")
    department_id = fields.Many2one('hr.department', string="Department")
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    state = fields.Selection(
        [('draft', 'Draft'), ('line_mng', 'Waiting Line Manager'), ('qhse', 'QHSE Verifiy'),
         ('ccso', 'CCSO Approve'),
         ('od', 'Operation Director Approve'),
         ('fleet', 'Fleet Approve'),
         ('chro', 'CHRO'),
         ('ceo', 'CEO'),
         ('qhse_conf', 'QHSE confirm'),
         ('ict', 'ICT Processing'),
         ('qhse_validated', 'QHSE Reviewing'),
         ('reject', 'reject'), ('close', 'Waiting Acceptance/Close'), ('done', 'Done')],
        string='Status', default='draft', track_visibility='onchange', copy=False)
    type_approval = fields.Selection(selection=[('ccso_approval', 'CCSO Approval'),
                                                ('od', 'Operation Director Approve'),
                                                ('ceo', 'CEO'),
                                                ('chro', 'CHRO'),
                                                ('fleet', 'Fleet Approve'), ], related='pr_cat.type_approval')
    state_ccso = fields.Selection(related='state')
    state_od = fields.Selection(related='state')
    state_fleet = fields.Selection(related='state')
    state_chro = fields.Selection(related='state')
    state_ceo = fields.Selection(related='state')
    date = fields.Datetime(default=fields.Datetime.now(), readonly=True)
    level_of_change = fields.Selection(string="", selection=[('maj', 'Major'), ('min', 'Minor'), ], default='maj')
    type = fields.Selection(string="", selection=[('mod', 'Modified'), ('new_doc', 'New document'), ], default='mod')
    description = fields.Char(string="", )
    note = fields.Char(string="", )
    pr_mo_new = fields.Text(string="Proposed Modification/New issue")
    mo_new = fields.Text(string="Modification/ New issue Cause / s:")
    emp_l_mng = fields.Many2one('res.users', string="Line Manager Approval", readonly=1)
    emp_l_mng_date = fields.Datetime(string='Date Approve', readonly=1)
    qhse_desc = fields.Text(string="QHSE COMMENT ")
    n_o_change = fields.Char(string="No. of Change", )
    rel_doc = fields.Char(string="Related Documents (if any)", )
    employee_type = fields.Selection(selection=[('hq', 'HQ Staff'),
                                                ('site', 'Site Staff'), ('fleet', 'Fleet')], )
    emp_ccso = fields.Many2one('res.users', string="CCSO Approval", readonly=1)
    emp_od = fields.Many2one('res.users', string="Operation Approval", readonly=1)
    emp_fleet = fields.Many2one('res.users', string="Fleet Approval", readonly=1)
    ccso_od_date = fields.Datetime(string='Date Approve', readonly=1)

    user_type = fields.Selection(related="req_id.user_type")

    qhse_manager = fields.Many2one('res.users', string="QHSE Approval", readonly=1)
    pr_cat = fields.Many2one(comodel_name="procedure.category", string="Procedure Category")
    qhse_date = fields.Datetime(string='Date Approve', readonly=1)
    procedure_id = fields.Many2one(comodel_name="qhse.procedure", string="Procedure")
    form_id = fields.Many2one('qhse.forms', string="Form")

    @api.onchange('req_id')
    def onchange_req_id(self):
        if not self.req_id.user_type:
            raise UserError('The Employee Type if NOT Set')
        else:
            emp = self.env['hr.employee'].sudo().search([('user_id', '=', self.req_id.id)], limit=1)
            if emp.sudo().job_id:
                self.job_id = emp.sudo().job_id.id
            if emp.sudo().department_id:
                self.department_id = emp.sudo().department_id.id
            self.employee_type = self.req_id.user_type

    def set_submit(self):
        if not self.req_id.id == self.env.user.id:
            raise UserError('Sorry, Only requester can submit this document!')
        return self.write({'state': 'line_mng'})

    def set_l_mng_confirm(self):
        line_manager = False
        try:
            line_manager = self.req_id.line_manager_id
        except:
            line_manager = False
        if not line_manager or line_manager != self.env.user:
            raise UserError("Sorry. Your are not authorized to approve this document!")

        self.emp_l_mng = self.env.user
        self.emp_l_mng_date = fields.Datetime.now()
        return self.write({'state': 'qhse'})

    def set_qhse_confirm(self):
        self.qhse_manager = self.env.user
        self.qhse_date = fields.Datetime.now()
        if self.type_approval == 'ccso_approval':
            return self.write({'state': 'ccso'})
        if self.type_approval == 'od':
            return self.write({'state': 'od'})
        if self.type_approval == 'fleet':
            return self.write({'state': 'fleet'})
        if self.type_approval == 'ceo':
            return self.write({'state': 'ceo'})
        if self.type_approval == 'chro':
            return self.write({'state': 'chro'})
        self.qhse_manager = self.env.user
        self.qhse_date = fields.Datetime.now()

    def set_ccso_confirm(self):
        self.emp_ccso = self.env.user
        self.ccso_od_date = fields.Datetime.now()
        return self.write({'state': 'qhse_conf'})

    def set_od_confirm(self):
        self.emp_od = self.env.user
        self.ccso_od_date = fields.Datetime.now()
        return self.write({'state': 'qhse_conf'})

    def set_fleet_confirm(self):
        self.emp_fleet = self.env.user
        self.ccso_od_date = fields.Datetime.now()
        return self.write({'state': 'qhse_conf'})

    def set_chro(self):
        self.emp_fleet = self.env.user
        self.ccso_od_date = fields.Datetime.now()
        return self.write({'state': 'qhse_conf'})

    def set_ceo(self):
        self.emp_fleet = self.env.user
        self.ccso_od_date = fields.Datetime.now()
        return self.write({'state': 'qhse_conf'})

    def set_qhse_conf_confirm(self):
        return self.write({'state': 'ict'})

    def set_qhse_validate(self):
        return self.write({'state': 'close'})

    def set_ict_confirm(self):
        return self.write({'state': 'qhse_validated'})

    def done(self):
        if not self.req_id.id == self.env.user.id:
            raise UserError('Sorry, Only requester can Close this document!')
        return self.write({'state': 'done'})

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")

        return super(ModificationRequest, self).unlink()

    @api.model
    def create(self, vals):
        for val in vals:
            vals['code_seq'] = self.env['ir.sequence'].next_by_code('mod.request') or ' '

        return super(ModificationRequest, self).create(vals)


class QhseProcedure(models.Model):
    _name = 'qhse.procedure'
    _order = "create_date desc"

    name = fields.Char()
    pr_cat = fields.Many2one(comodel_name="procedure.category", string="Procedure Category")
    page = fields.Char()
    issue_rev = fields.Char(string='Issue/Rev')
    date = fields.Date()
    code = fields.Char(string="Code")
    type_approval = fields.Selection(selection=[ ('ccso_approval', 'CCSO Approval'),
                                                ('od', 'Operation Director Approve'),
                                                ('ceo', 'CEO'),
                                                ('chro', 'CHRO'),
                                                ('fleet', 'Fleet Approve'), ], related='pr_cat.type_approval')
    mod_req_count = fields.Integer(string="Count", compute='compute_md_req_count')
    pdf_file = fields.Binary(string='PDF Attachment')
    pdf_filename = fields.Char(string='PDF Filename')

    def compute_md_req_count(self):
        self.mod_req_count = self.env['modification.request'].search_count([('procedure_id', '=', self.id)])

    def get_mod_change(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Modification Changes',
            'view_mode': 'list',
            'res_model': 'modification.request',
            'domain': [('procedure_id', '=', self.id)],
            'context': "{'create': False}"
        }


class QhsePolicy(models.Model):
    _name = 'qhse.policy'
    _order = "create_date desc"

    name = fields.Char()
    pr_cat = fields.Many2one(comodel_name="procedure.category", string="Procedure Category")
    page = fields.Char()
    issue_rev = fields.Char(string='Issue/Rev')
    date = fields.Date()
    code = fields.Char(string="Code")
    type_approval = fields.Selection(selection=[ ('ccso_approval', 'CCSO Approval'),
                                                ('od', 'Operation Director Approve'),
                                                ('ceo', 'CEO'),
                                                ('chro', 'CHRO'),
                                                ('fleet', 'Fleet Approve'), ], related='pr_cat.type_approval')
    pdf_file = fields.Binary(string='PDF Attachment')
    pdf_filename = fields.Char(string='PDF Filename')


class ProcedureCategory(models.Model):
    _name = 'procedure.category'
    _order = "create_date desc"

    name = fields.Char(required=True, )
    type_approval = fields.Selection(string="", selection=[ ('ccso_approval', 'CCSO Approval'),
                                                           ('od', 'Operation Director Approve'),
                                                           ('ceo', 'CEO'),
                                                           ('chro', 'CHRO'),
                                                           ('fleet', 'Fleet Approve'), ], required=False, )


class QhseForms(models.Model):
    _name = 'qhse.forms'
    _order = "create_date desc"

    name = fields.Char()
    pr_cat = fields.Many2one(comodel_name="procedure.category", string="Procedure Category")
    page = fields.Char()
    issue_rev = fields.Char(string='Issue/Rev')
    date = fields.Date()
    code = fields.Char(string="Code")
    procedure_id = fields.Many2one(comodel_name="qhse.procedure", string="Procedure")
    mod_req_count = fields.Integer(string="Count", compute='compute_md_req_count')
    pdf_file = fields.Binary(string='PDF Attachment')
    pdf_filename = fields.Char(string='PDF Filename')

    def compute_md_req_count(self):
        self.mod_req_count = self.env['modification.request'].search_count([('procedure_id', '=', self.id)])

    def get_mod_change(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Modification Changes',
            'view_mode': 'list',
            'res_model': 'modification.request',
            'domain': [('form_id', '=', self.id)],
            'context': "{'create': False}"
        }
