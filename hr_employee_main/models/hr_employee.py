# -*- coding: utf-8 -*-

from odoo import fields , api , models , _
import datetime
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _order = 'emp_code'

    display_name = fields.Char("Display Name", compute='compute_display_name', store=True)
    location_id = fields.Many2one("locations.detail")
    residence_area = fields.Many2one("locations.detail",string='Location')
    arabic_name = fields.Char("Arabic Name")
    emp_code = fields.Char(string='Employee Code')
    id_expiry_date = fields.Date(string='ID Expiry Date', help='Expiry date of Identification ID')
    passport_expiry_date = fields.Date(string='Passport Expiry Date', help='Expiry date of Passport ID')
    age = fields.Integer(string="Age", readonly=True, compute="_compute_age")
    custody_id = fields.One2many('hr.custody', 'employee_id', groups="hr.group_hr_user")
    relative_ids = fields.One2many(string='Relatives',comodel_name='hr.employee.relative',inverse_name='employee_id', groups="hr.group_hr_user")
    training_ids = fields.One2many('hr.training', 'employee_id', groups="hr.group_hr_user")
    allow_pasi = fields.Boolean(string='Allow PASI')
    is_susupend = fields.Boolean(string='Salary Suspend')
    employee_partner_id=fields.Many2one("res.partner",string= "Employee-Partner")

    parent_id = fields.Many2one('hr.employee', 'Manager', compute="_compute_parent_id", store=True, readonly=False,domain="[]")


    birthday = fields.Date('Date of Birth', groups="hr.group_hr_user,base.group_user",
                           tracking=True)
    # employee_attendance_ids = fields.One2many(comodel_name='hr.attendance', inverse_name='employee_id', domain=lambda self:self._get_employee_id_domain())
    # total_w_hours = fields.Float(string='Total Worked Hours', compute = 'total_worked_hours')

    # def _get_employee_id_domain(self):
    #     return [('employee_id', '=', self.id)]

    def correct(self):
        record=self.env['hr.employee'].search([])
        for rec in record:
            if rec.location_id:
                rec.residence_area=rec.location_id


    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None, order=None):
        args = list(args or [])
        if name:
            args += ['|',('name', operator, name), ('emp_code', operator, name)]
        return self._search(args, limit=limit)


    @api.depends('department_id')
    def _compute_parent_id(self):
        for employee in self.filtered('department_id.manager_id'):
            employee.parent_id = employee.department_id.manager_id

    @api.depends('emp_code', 'name')
    def compute_display_name(self):
        for record in self:
            display_name = record.name
            if record.emp_code:
                display_name = "[%s] %s" % (record.emp_code, display_name)
            record.display_name = display_name

    @api.depends("birthday")
    def _compute_age(self):
        for record in self:
            age = 0
            if record.birthday:
                age = relativedelta(fields.Date.today(), record.birthday).years
            record.age = age



    def mail_reminder(self):
        """Sending expiry date notification for ID and Passport to HR Manager and Cc TO employee"""
        now = datetime.now() + timedelta(days=1)
        date_now = now.date()
        match = self.search([])
        employees = self.env.ref('hr.group_hr_user').users.mapped('employee_ids')
        emails = [employee.work_email for employee in employees]
        for i in match:
            if i.id_expiry_date:
                exp_date = fields.Date.from_string(i.id_expiry_date) - timedelta(days=14)
                if date_now >= exp_date:
                    mail_content = "  Hello  "  ",<br> ID of " + str(i.name) + " # "  + str(i.identification_id) +" " + "is going to expire on " + \
                                   str(i.id_expiry_date) + ". Please renew it before expiry date"
                    main_content = {
                        'subject': _('ID-%s Expired On %s') % (i.identification_id, i.id_expiry_date),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': emails,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()
        match1 = self.search([])
        for i in match1:
            if i.passport_expiry_date:
                exp_date1 = fields.Date.from_string(i.passport_expiry_date) - timedelta(days=180)
                if date_now >= exp_date1:
                    mail_content = "  Hello  "  ",<br> Passport of " + str(i.name) + " # " + str(i.passport_id) + " " + "is going to expire on " + \
                                   str(i.passport_expiry_date) + ". Please renew it before expiry date"
                    main_content = {
                        'subject': _('Passport-%s Expired On %s') % (i.passport_id, i.passport_expiry_date),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': emails,
                        'email_cc': i.work_email,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()

        match2 = self.search([])
        for i in match2:
            if i.visa_expire:
                exp_date2 = fields.Date.from_string(i.visa_expire) - timedelta(days=14)
                if date_now >= exp_date2:
                    mail_content = "  Hello  "  ",<br> Visa of  " + i.name + " # " + i.visa_no +" " +"is going to expire on " + \
                                   str(i.visa_expire) + ". Please renew it before expiry date"
                    main_content = {
                        'subject': _('Visa-%s Expired On %s') % (i.visa_no, i.visa_expire),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': emails,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()




    dep = fields.Selection(selection=[
            ('division', 'Division'),
            ('department', 'Department'),
            ('section', 'Section'),
            ('unit', 'Unit'),
        ])

    @api.onchange('employee_type')
    def dep_domain(self):
        for rec in self:
            return {
                'domain': {'department_id': ['|',('field_hq', '=', rec.employee_type),('field_hq', '=', '')]}
            }


     

    @api.onchange('dep')
    def onchange_dep(self):
        if self.dep == 'division':
            return {
            'domain':{
            'department_id':[('dep_type','=', 'division')]}}
        elif self.dep == 'department':
            return {
            'domain':{
            'department_id':[('dep_type','=', 'department')]}}
        elif self.dep == 'section':
            return {
            'domain':{
            'department_id':[('dep_type','=', 'section')]}}
        else:
            return {
            'domain':{
            'department_id':[('dep_type','=', 'unit')]}}






# class hrEmployeePublic(models.Model):
#     _inherit = 'hr.employee.public'

#     emp_code = fields.Char(string='Employee Code')
#     allow_pasi = fields.Boolean(string='Allow PASI')

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    line_manager_id = fields.Many2one(
        related='employee_id.line_manager_id',
    )

    line_line_manager_id = fields.Many2one(
        related='employee_id.line_line_manager_id',
    )

    rida_employee_type = fields.Selection(
        related='employee_id.rida_employee_type',
    )


    dep = fields.Selection(selection=[
            ('division', 'Division'),
            ('department', 'Department'),
            ('section', 'Section'),
            ('unit', 'Unit'),
        ])
    location_id = fields.Many2one("locations.detail")
    residence_area = fields.Many2one("locations.detail",string='Location')
    arabic_name = fields.Char("Arabic Name")
    emp_code = fields.Char(string='Employee Code')
    # id_expiry_date = fields.Date(string='ID Expiry Date', help='Expiry date of Identification ID')
    # age = fields.Integer(string="Age", readonly=True, compute="_compute_age")
    # custody_id = fields.One2many('hr.custody', 'employee_id', groups="hr.group_hr_user")
    # relative_ids = fields.One2many(string='Relatives',comodel_name='hr.employee.relative',inverse_name='employee_id', groups="hr.group_hr_user")
    # training_ids = fields.One2many('hr.training', 'employee_id', groups="hr.group_hr_user")
    allow_pasi = fields.Boolean(string='Allow PASI')
    is_susupend = fields.Boolean(string='Salary Suspend')
    employee_partner_id=fields.Many2one("res.partner",string= "Employee-Partner")
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



    is_worker = fields.Boolean(string='Is Worker')
    is_section_head = fields.Boolean(string='Is Section head')

    project_analytic_account_id = fields.Many2one(comodel_name='account.analytic.account', string='Project Analytic Account')
    # contract_start_date = fields.Date(string='Contract Start Date', related='employee_id.contract_id.date_start',readonly=True,store=True)
    # contract_end_date = fields.Date(string='Contract end Date', related='employee_id.contract_id.date_end',readonly=True,store=True)


    cross_employee = fields.Many2one(comodel_name='hr.employee', string='Cross Employee')

    passport_expiry_date = fields.Date(readonly=True)


    birthday = fields.Date('Date of Birth', groups="hr.group_hr_user,base.group_user",
                           tracking=True)



class EmployeesRotationLine(models.Model):
    _inherit = 'employees.rotation.line'


    partner_id = fields.Many2one(comodel_name="res.partner", string="Partner", related='employee_id.employee_partner_id',
                                 readonly=True)
    account_payable = fields.Many2one(comodel_name="account.account", string="Payable",
                                      related='employee_id.employee_partner_id.property_account_payable_id', readonly=True)

