# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo import models, fields, api
# import datetime
from datetime import datetime, date, timedelta


class DoctorVisit(models.Model):
    _name = 'doctor.visit'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char(readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True,
                             readonly=True)
    type = fields.Selection(string="Type Of Patient",
                            selection=[('employee', 'Employee'), ('contractor', 'Contractor'), ('quest', 'Guest'), ],
                            default='employee', required=1)
    p_contractor = fields.Many2one('patient.contractors', string="Patient")
    p_employee = fields.Many2one('hr.employee', string="Patient")
    p_quest = fields.Many2one('patient.quset', string="Patient")
    account_analytic_id = fields.Many2one('account.analytic.account', string='Cost Center')
    patient = fields.Char(string="Patient", compute='_compute_fields')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', 'Department', compute='_compute_fields')
    job_id = fields.Many2one(comodel_name="hr.job", string="Job Title", compute='_compute_fields')
    line_manager_id = fields.Many2one(comodel_name="res.users", string="Manager", compute='_compute_fields')
    age = fields.Integer(string="Age", compute='_compute_fields')
    state = fields.Selection(
        [('draft', 'Draft'), ('diagnosing', 'Diagnosing'), ('referring', 'Referring'),
         ('lab', 'Lab testing'),
         ('lab_result', 'Lab Result'),
         ('minor_room', 'Minor room'),
         ('pharmacy', 'Pharmacy'),
         ('close', 'Close'),
         ('reject', 'Rejected')],
        string='Status', default='draft', track_visibility='onchange', copy=False)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], default='male', compute='_compute_fields')
    blood_group = fields.Selection([
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ], string='Blood Group', compute='_compute_fields')
    urgency_level = fields.Selection([
        ('acute', 'Acute'),
        ('emergency', 'Emergency'),
        ('urgency', 'Urgency'),
    ], default='acute', string='Urgency Level')
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    work_related = fields.Boolean(string="Work Related", default=False)
    spot_diagnostic = fields.Text(string="Spot Diagnostic")
    pre_notes = fields.Text(string="Prescription Notes")
    appointment_date = fields.Datetime(string="Appointment Date", default=fields.Datetime.now)
    description = fields.Text("Symptoms")
    diagnostic_result = fields.Text("Diagnostics Results")
    show_referring = fields.Boolean(default=False)
    partner_id = fields.Many2one('res.partner', 'Converted To')
    sick_leaves = fields.Char("Sick Leaves")
    last_lab_test_id = fields.Many2one('lab.request', 'Last Lab Test')
    lab_test_count = fields.Integer(string="Lab Tests", compute='_compute_lab_test_count')
    lab_total_invoice = fields.Float(compute='_compute_lab_total_invoice', string='Lab Invoice')
    minor_room_count = fields.Integer(string="Minor Room", compute='_compute_minor_room_count')
    last_minor_room_id = fields.Many2one('minor.room', 'Last Minor Room Request')
    issuance_request_count = fields.Integer(string="Issuance Request", compute='_compute_issuance_request_count')
    pharmacy_total_invoice = fields.Float(compute='_compute_pharmacy_invoice', string='Pharmacy Invoice')
    last_issuance_request_id = fields.Many2one('medicare.issuance.request', 'Last Issuance Request')
    dieases_ids = fields.Many2many(comodel_name="dieases", string="Dieases")
    doctor_visit_count = fields.Integer(string="Doctor Visits", compute='compute_doctor_visit_count')
    total_invoice = fields.Float(compute='_compute_total_invoice', string='Total Invoice')

    def compute_doctor_visit_count(self):
        if self.p_employee:
            self.doctor_visit_count = self.env['doctor.visit'].search_count(
                [('p_employee.id', '=', self.p_employee.id), ('id', '!=', self.id)])
        elif self.p_contractor:
            self.doctor_visit_count = self.env['doctor.visit'].search_count(
                [('p_contractor.id', '=', self.p_contractor.id), ('id', '!=', self.id)])
        elif self.p_quest:
            self.doctor_visit_count = self.env['doctor.visit'].search_count(
                [('p_quest.id', '=', self.p_quest.id), ('id', '!=', self.id)])
        else:
            self.doctor_visit_count = 0

    def set_doctor_visit(self):
        if self.p_employee:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Doctor Visits',
                'view_mode': 'tree,form',
                'res_model': 'doctor.visit',
                'domain': [('p_employee.id', '=', self.p_employee.id), ('id', '!=', self.id)],
                'context': "{'create': False}"
            }

        elif self.p_contractor:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Doctor Visits',
                'view_mode': 'tree,form',
                'res_model': 'doctor.visit',
                'domain': [('p_contractor.id', '=', self.p_contractor.id), ('id', '!=', self.id)],
                'context': "{'create': False}"
            }

        elif self.p_quest:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Doctor Visits',
                'view_mode': 'tree,form',
                'res_model': 'doctor.visit',
                'domain': [('p_quest.id', '=', self.p_quest.id), ('id', '!=', self.id)],
                'context': "{'create': False}"
            }

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(DoctorVisit, self).unlink()

    def _compute_issuance_request_count(self):
        self.issuance_request_count = self.env['medicare.issuance.request'].search_count(
            [('doctor_visitor_id.id', '=', self.id)])

    def _compute_lab_test_count(self):
        self.lab_test_count = self.env['lab.request'].search_count(
            [('doctor_visitor_id.id', '=', self.id)])

    def _compute_lab_total_invoice(self):
        for rec in self:
            lab_total_invoice = 0
            lab_test_ids = self.env['lab.request'].search(
                [('doctor_visitor_id.id', '=', rec.id), ('state', 'not in', ['draft', 'reject'])])
            if lab_test_ids:
                lab_total_invoice = self.env['invoice.prices'].search(
                    [('lab_request.id', 'in', lab_test_ids.ids)])
            if lab_total_invoice:
                rec.lab_total_invoice = sum([i.price for i in lab_total_invoice])
            else:
                rec.lab_total_invoice = 0

    def _compute_pharmacy_invoice(self):
        for rec in self:
            issuance_request = self.env['medicare.issuance.request'].search(
                [('doctor_visitor_id.id', '=', rec.id), ('state', 'not in', ['draft', 'reject'])])
            if issuance_request:
                issuance_request_line = self.env['medicare.issuance.request.line'].search(
                    [('request_id.id', 'in', issuance_request.ids)])
                if issuance_request_line:
                    rec.pharmacy_total_invoice = sum([i.price * i.qty for i in issuance_request_line])
                else:
                    rec.pharmacy_total_invoice = 0
            else:
                rec.pharmacy_total_invoice = 0

    def _compute_total_invoice(self):
        for rec in self:
            if rec.lab_total_invoice or rec.pharmacy_total_invoice:
                rec.total_invoice = rec.lab_total_invoice + rec.pharmacy_total_invoice
            else:
                rec.total_invoice = 0

    def _compute_minor_room_count(self):
        self.minor_room_count = self.env['minor.room'].search_count(
            [('doctor_visitor_id.id', '=', self.id)])

    def action_pharmacy(self):
        self.ensure_one()
        env = self.env(user=1)
        res = env['medicare.issuance.request'].create(
            {'type': self.type, 'company_id': self.company_id.id, 'p_employee': self.p_employee.id,
             'p_contractor': self.p_contractor.id,
             'p_quest': self.p_quest.id, 'doctor_visitor_id': self.id, 'patient': self.patient,
             'type_product': 'pharmacy', 'account_analytic_id': self.account_analytic_id.id
             })
        self.last_issuance_request_id = res.id
        self.write({'state': 'pharmacy'})
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'medicare.issuance.request',
            'res_id': res.id,
            'context': {'form_view_initial_mode': 'edit'},
        }

    def action_minor_room(self):
        self.ensure_one()
        env = self.env(user=1)
        res = env['minor.room'].create(
            {'type': self.type, 'account_analytic_id': self.account_analytic_id.id, 'company_id': self.company_id.id,
             'p_employee': self.p_employee.id,
             'p_contractor': self.p_contractor.id,
             'p_quest': self.p_quest.id, 'doctor_visitor_id': self.id, 'patient': self.patient,
             })
        self.last_minor_room_id = res.id
        self.write({'state': 'minor_room'})
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'minor.room',
            'res_id': res.id,
            'context': {'form_view_initial_mode': 'edit'},
        }

    def action_lab_test(self):
        self.ensure_one()
        env = self.env(user=1)
        res = env['lab.request'].create(
            {'type': self.type, 'account_analytic_id': self.account_analytic_id.id, 'company_id': self.company_id.id,
             'p_employee': self.p_employee.id,
             'p_contractor': self.p_contractor.id, 'department_id': self.department_id.id,
             'p_quest': self.p_quest.id, 'doctor_visitor_id': self.id, 'patient': self.patient,
             })
        self.last_lab_test_id = res.id
        self.write({'state': 'lab'})
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'lab.request',
            'res_id': res.id,
            'context': {'form_view_initial_mode': 'edit'},
        }

    def set_pharmacy(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Issuance Request',
            'view_mode': 'tree,form',
            'res_model': 'medicare.issuance.request',
            'domain': [('doctor_visitor_id.id', '=', self.id)],
            'context': "{'create': False}"
        }

    def set_minor_room(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Minor Room Requests',
            'view_mode': 'tree,form',
            'res_model': 'minor.room',
            'domain': [('doctor_visitor_id.id', '=', self.id)],
            'context': "{'create': False}"
        }

    def set_lab_test(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lab Tests',
            'view_mode': 'tree,form',
            'res_model': 'lab.request',
            'domain': [('doctor_visitor_id.id', '=', self.id)],
            'context': "{'create': False}"
        }

    def action_referring(self):
        self.show_referring = True
        return self.write({'state': 'referring'})

    def action_diagnosing(self):
        return self.write({'state': 'diagnosing'})

    def action_close(self):
        return self.write({'state': 'close'})

    def action_draft(self):
        return self.write({'state': 'draft'})

    @api.depends("p_employee", "p_contractor", "p_quest")
    def _compute_fields(self):
        for rec in self:
            if rec.p_employee:
                if rec.p_employee.company_id:
                    rec.company_id = rec.p_employee.company_id.id
                if rec.p_employee.sudo().contract_id:
                    rec.account_analytic_id = rec.p_employee.sudo().contract_id.analytic_account_id
                else:
                    rec.account_analytic_id = False
                rec.age = rec.p_employee.age
                rec.department_id = rec.p_employee.department_id
                rec.job_id = rec.p_employee.job_id
                rec.line_manager_id = rec.p_employee.user_id.line_manager_id
                rec.gender = rec.sudo().p_employee.gender
                rec.blood_group = rec.p_employee.blood_group
                rec.patient = rec.p_employee.name
            elif rec.p_contractor:
                rec.blood_group = rec.p_contractor.blood_group
                rec.gender = rec.p_contractor.gender
                rec.patient = rec.p_contractor.name
                rec.age = rec.p_contractor.age
                rec.department_id = False
                rec.job_id = False
                rec.line_manager_id = False
            elif rec.p_quest:
                rec.age = rec.p_quest.age
                rec.blood_group = rec.p_quest.blood_group
                rec.gender = rec.p_quest.gender
                rec.patient = rec.p_quest.name
                rec.department_id = False
                rec.job_id = False
                rec.line_manager_id = False
            else:
                rec.age = 0
                rec.gender = False
                rec.blood_group = False
                rec.patient = False
                rec.department_id = False
                rec.job_id = False
                rec.line_manager_id = False

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('doctor.visit') or ' '
        res = super(DoctorVisit, self).create(vals)
        return res

    @api.onchange('type')
    def _onchange_type(self):
        self.age = 0
        self.gender = False
        self.blood_group = False
        self.p_contractor = False
        self.p_employee = False
        self.p_quest = False
        self.patient = False
        self.account_analytic_id = False

    @api.onchange('p_employee', 'p_contractor', 'p_quest')
    def _onchange_employee(self):
        for rec in self:
            if rec.sudo().p_employee.sudo().contract_id:
                rec.account_analytic_id = rec.p_employee.sudo().contract_id.sudo().analytic_account_id
            else:
                rec.account_analytic_id = False
            if rec.p_contractor:
                if rec.p_contractor.department_id.sudo().analytic_account_id:
                    rec.account_analytic_id = rec.p_contractor.department_id.sudo().analytic_account_id
                else:
                    rec.account_analytic_id = False


class PatientContractors(models.Model):
    _name = 'patient.contractors'

    name = fields.Char(string='Contractor Name', required=1)
    emp_code = fields.Char(string="Contractor Code")
    department_id = fields.Many2one('hr.department', 'Department')
    partner_id = fields.Many2one('res.partner', 'Partner')
    info = fields.Text(string="Other Info")
    birthday = fields.Date('Date of Birth')
    age = fields.Integer(string="Age", compute="_compute_age", store=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], default='male')
    mobile_phone = fields.Char('Work Mobile')
    work_email = fields.Char('Work Email')
    marital = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('cohabitant', 'Legal Cohabitant'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')
    ], string='Marital Status', default='single')
    blood_group = fields.Selection([
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ], string='Blood Group')

    @api.depends("birthday")
    def _compute_age(self):
        for record in self:
            age = 0
            if record.birthday:
                age = relativedelta(fields.Date.today(), record.birthday).years
            record.age = age


class PatientQuest(models.Model):
    _name = 'patient.quset'

    name = fields.Char(string='Guest Name', required=1)
    emp_code = fields.Char(string="Guest Code")
    organization = fields.Char(string="Organization")
    info = fields.Text(string="Other Info")
    birthday = fields.Date('Date of Birth')
    age = fields.Integer(string="Age", compute="_compute_age", store=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], default='male')
    mobile_phone = fields.Char('Work Mobile')
    work_email = fields.Char('Work Email')
    marital = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('cohabitant', 'Legal Cohabitant'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')
    ], string='Marital Status', default='single')
    blood_group = fields.Selection([
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ], string='Blood Group')

    @api.depends("birthday")
    def _compute_age(self):
        for record in self:
            age = 0
            if record.birthday:
                age = relativedelta(fields.Date.today(), record.birthday).years
            record.age = age


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    blood_group = fields.Selection([
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ], string='Blood Group')
    doctor_visit_count = fields.Integer(string="Doctor Visits", compute='compute_doctor_visit_count')
    birthday = fields.Date('Date of Birth', groups="hr.group_hr_user,medicare.group_medicare_medicare,base.group_user",
                           tracking=True)

    def compute_doctor_visit_count(self):
        self.doctor_visit_count = self.env['doctor.visit'].search_count(
            [('p_employee.id', '=', self.id), ('state', '=', 'close')])

    def set_doctor_visit(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Doctor Visits',
            'view_mode': 'tree,form',
            'res_model': 'doctor.visit',
            'domain': [('p_employee.id', '=', self.id), ('state', '=', 'close')],
            'context': "{'create': False}"
        }
