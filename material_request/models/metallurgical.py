from odoo import models, fields, api, _
from odoo import models, fields, api, exceptions, _
from odoo.tools import format_datetime
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.exceptions import UserError, ValidationError
import dateutil
from dateutil.relativedelta import relativedelta

_STATES = [
    ('draft', 'Draft'),
    ('metallurgist', 'Metallurgist'),
    ('met_lab_Manager', 'Met Lab Manager'),
    ('operation_director', 'Oper-Director Approval'),
    ('reject', 'Rejected'),
    ('close', 'Closed'),
]


class MetallurgicalRequest(models.Model):
    _name = "metallurgical.request"

    _description = 'Metallurgical Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _rec_name = 'name'
    _order = 'date_request desc'

    name = fields.Char('META-LAB No.', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))

    date_request = fields.Datetime("Request Date", default=fields.Datetime.now, required=True)

    state = fields.Selection(selection=_STATES, string='Status', index=True, tracking=True, readonly=True,
                             required=True, copy=False, default='draft')

    sample_category = fields.Selection([('internal', 'Internal'), ('external', 'External')], default="internal",
                                       srting="Internal/External", required=True)
    sample_no = fields.Float("Number of samples ", required="True")
    sample_wight = fields.Float("Approximate total sample weight ", required="True")

    sample_type = fields.Selection([('core', 'Core'),
                                    ('drill', 'Drill cuttings'),
                                    ('tailing', 'Tailing'),
                                    ('fine', 'Fine'),
                                    ('rocks', 'Rocks'),
                                    ('carbon', 'Active Carbon'),
                                    ('cyanide', 'Cyanide'),
                                    ('other', 'Other')], string="Sample Type")

    other = fields.Char("Other")
    core_type = fields.Selection(
        [('hq', 'HQ'), ('Pq', 'PQ'), ('nq', 'NQ'), ('full', 'Full'), ('1/2', '1/2'), ('1/4', '1/4')],
        string="Core Types")
    Sample_contained = fields.Char("Samples will be contained within")

    hazardous = fields.Selection([('cyanide', 'Cyanide-PPM'), ('lead', 'Lead-PPM'), ('silica', 'Free Silica-PPM'),
                                  ('radioactive', 'Radioactive Material-PPM'),
                                  ('fibrous', 'Fibrous Material/Asbestos-PPM'), ('other', 'Other')],
                                 string="hazardous materials")

    hazardous_other = fields.Char("Other")

    test_type = fields.Many2one("meta.test.type", string="Type of test")

    requested_by = fields.Many2one('res.users', 'Courier Name', tracking=True,
                                   default=lambda self: self.get_requested_by(), store=True, readonly=True)

    email = fields.Char("Email")

    phone = fields.Char("Phone")

    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id)

    department_id = fields.Many2one('hr.department', string='Department',
                                    default=lambda self: self._get_default_department())

    reason_reject = fields.Text("Rejection Reason", track_visibility="onchange")

    metallurgist_date = fields.Datetime("Recevied Date")

    metallurgist = fields.Many2one('res.users', 'Metallurgist', tracking=True,
                                   store=True, readonly=True)

    meta_manager = fields.Many2one('res.users', 'Met Lab Manager', tracking=True,
                                   store=True, readonly=True)

    approved_date = fields.Datetime("Approval-Date")

    production_id = fields.Many2one('mrp.production', string="Production Order")
    workorder_id = fields.Many2one('mrp.workorder', string="Work Order")
    
    def _get_default_department(self):
        return self.env.user.department_id.id if self.env.user.department_id else False

##########email notification###########################
    def activity_update(self):
        for rec in self:
            users = []
            message = ""
            if rec.state == 'draft':
                users = self.env.ref('base_rida.rida_group_site_manager').user_ids
                message = "Please approval the request"
                for user in users:
                    self.activity_schedule('master_data.mail_act_master_data_approval', user_id=user.id, note=message)
            else:
                continue

    def button_submit(self):
        for rec in self:
            if not self.requested_by.id == self.env.user.id:
                raise UserError('Sorry, Only requester can submit this document!')

        if rec.sample_category == 'internal':
            rec.state = 'metallurgist'
        else:
            self.activity_update()
            rec.state = 'operation_director'

    def get_requested_by(self):
        user = self.env.user.id
        self.email = self.env.user.email
        return user

    def button_draft(self):
        return self.write({'state': 'draft'})

    def button_cancel(self):
        self.write({'state': 'cancel'})

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('metallurgical.sequence') or "/"

        return super(MetallurgicalRequest, self).create(vals)

    def button_receive(self):
        for rec in self:
            rec.metallurgist = rec.env.user.id
            rec.metallurgist_date = datetime.today()

        return self.write({'state': 'met_lab_Manager'})

    def button_approve(self):
        for rec in self:
            rec.meta_manager = rec.env.user.id
            rec.approved_date = datetime.today()

        return self.write({'state': 'close'})

    def operation_director_approve(self):
        return self.write({'state': 'metallurgist'})


class MetallurgicalTestType(models.Model):
    _name = "meta.test.type"

    _description = 'Test Type'
    _rec_name = 'name'

    name = fields.Char('Name')