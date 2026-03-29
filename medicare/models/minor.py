from odoo import fields, models, api
from odoo.exceptions import UserError
import datetime


class MinorRoom(models.Model):
    _name = 'minor.room'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char(readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True,
                             readonly=True)
    date = fields.Datetime(string="Request Date", default=datetime.datetime.now())
    confirmed_by = fields.Many2one('res.users', string='Confirmed By', default=lambda self: self.env.user,
                                   tracking=True,
                                   readonly=True)
    doctor_visitor = fields.Many2one('doctor.visit', string="Clinic Visit")
    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed'),
         ('reject', 'Rejected')],
        string='Status', default='draft', track_tracking=True, copy=False)
    minor_procedure = fields.Selection(
        [('nuring_procedures', 'Nuring procedures'), ('operations', 'Operations'),
         ('services', 'Services'), ('follow_up', 'Follow Up')],
        string='Minor Prodcedure')
    type = fields.Selection(string="Type Of Patient",
                            selection=[('employee', 'Employee'), ('contractor', 'Contractor'), ('quest', 'Guest'), ],
                            default='employee', required=1)
    p_contractor = fields.Many2one('patient.contractors', string="Patient")
    p_employee = fields.Many2one('hr.employee', string="Patient")
    p_quest = fields.Many2one('patient.quset', string="Patient")
    patient = fields.Char(string="Patient")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    minor_items = fields.Many2many('minor.items', string='Minor Items')
    doctor_visitor_id = fields.Many2one('doctor.visit', string="Doctor Visitor")
    description = fields.Text('Description')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Cost Center')
    last_issuance_request_id = fields.Many2one('medicare.issuance.request', 'Last Issuance Request')
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    last_minor_id = fields.Many2one('medicare.issuance.request', 'Last Minor Consumable Request')
    minor_consumble_count = fields.Integer(string="Minor Consumable", compute='_compute_minor_consumble_count')

    def _compute_minor_consumble_count(self):
        self.minor_consumble_count = self.env['medicare.issuance.request'].search_count(
            [('minor_id.id', '=', self.id)])

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(MinorRoom, self).unlink()

    def set_minor_consumable(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Minor Consumable',
            'view_mode': 'list,form',
            'res_model': 'medicare.issuance.request',
            'domain': [('minor_id.id', '=', self.id)],
            'context': "{'create': False}"
        }

    @api.onchange('type')
    def _onchange_type(self):
        self.p_contractor = False
        self.p_employee = False
        self.p_quest = False
        self.patient = False
        self.account_analytic_id = False

    @api.onchange('p_contractor', 'p_employee', 'p_quest')
    def _onchange_type_of(self):
        if self.p_employee:
            if self.p_employee.company_id:
                self.company_id = self.p_employee.company_id.id
            self.patient = self.p_employee.name
            if self.p_employee.sudo():
                self.account_analytic_id = self.sudo().p_employee.sudo().analytic_account_id
            else:
                self.account_analytic_id = False
        if self.p_contractor:
            self.patient = self.p_contractor.name
            if self.p_contractor.department_id.sudo().analytic_account_id:
                self.account_analytic_id = self.p_contractor.department_id.sudo().analytic_account_id
            else:
                self.account_analytic_id = False

        if self.p_quest:
            self.patient = self.p_quest.name

    def action_minor_consumable(self):
        self.ensure_one()
        env = self.env(user=1)
        res = env['medicare.issuance.request'].create(
            {'type': self.type, 'company_id': self.company_id.id, 'p_employee': self.p_employee.id,
             'p_contractor': self.p_contractor.id,
             'p_quest': self.p_quest.id, 'minor_id': self.id, 'patient': self.patient,
             'type_product': 'minor_room', 'account_analytic_id': self.account_analytic_id.id
             })
        self.last_minor_id = res.id
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'medicare.issuance.request',
            'res_id': res.id,
            'context': {'form_view_initial_mode': 'edit'},
        }


    def action_confirm(self):
        return self.write({'state': 'confirmed'})

    def action_draft(self):
        return self.write({'state': 'draft'})

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('room.code') or ' '

        return super(MinorRoom, self).create(vals)


class MinorItems(models.Model):
    _name = 'minor.items'

    name = fields.Char(string='Name')
    minor_procedure = fields.Selection(
        [('nuring_procedures', 'Nuring procedures'), ('operations', 'Operations'),
         ('services', 'Services'), ('follow_up', 'Follow Up')],
        string='Minor Prodcedure', store=True)
    description = fields.Text('')
    price = fields.Float(
        'Price', digits='Product Price')
    sequence = fields.Integer(string="NO", compute='_compute_step_number')


    @api.depends('name')
    def _compute_step_number(self):
        for index, record in enumerate(self, start=1):
            record.sequence = str(index)
