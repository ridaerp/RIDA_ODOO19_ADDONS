import datetime

from odoo import models, fields, api
from odoo.exceptions import UserError


class LabRequest(models.Model):
    _name = 'lab.request'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char(readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True,
                             readonly=True)
    responsible_id = fields.Many2one("res.users", "Responsible")
    date = fields.Datetime(default=fields.Datetime.now(), string='Request Date')
    type = fields.Selection(string="Type Of Patient",
                            selection=[('employee', 'Employee'), ('contractor', 'Contractor'), ('quest', 'Guest'), ],
                            default='employee', required=1)
    p_contractor = fields.Many2one('patient.contractors', string="Patient")
    p_employee = fields.Many2one('hr.employee', string="Patient")
    p_quest = fields.Many2one('patient.quset', string="Patient")
    patient = fields.Char(string="Patient")
    department_id = fields.Many2one('hr.department', 'Department')
    result = fields.Char(string="Result")
    extra_info = fields.Text(string="Extra Info")
    description = fields.Text('Description')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    doctor_visitor_id = fields.Many2one('doctor.visit', string="Clinic Visit")
    date_of_analysis = fields.Datetime(string="Date Of Analysis")
    routine = fields.Boolean(string="Routine", default=False)
    serology = fields.Boolean(string="Serology", default=False)
    chemistry = fields.Boolean(string="Chemistry", default=False)
    invoice_prices_ids = fields.One2many('invoice.prices', 'lab_request', string="Invoice")
    lab_result_routine_ids = fields.One2many('lab.result', 'routine_invest_attributes_ids', string="Routine Lab Result")
    lab_result_serology_ids = fields.One2many('lab.result', 'serology_invest_attributes_ids',
                                              string="Serology Lab Result")
    lab_result_chemistry_ids = fields.One2many('lab.result', 'chemistry_invest_attributes_ids',
                                               string="ChemistryLab Result")
    routine_list_ids = fields.Many2many('investigations.list', 'lab_investigations_routine_rel', 'lab_request',
                                        'routine_investigation', string="Lab Investigation")
    serology_list_ids = fields.Many2many('investigations.list', 'lab_investigations_serology_rel', 'lab_request',
                                         'serology_investigation', string="Lab Investigation")
    chemistry_list_ids = fields.Many2many('investigations.list', 'lab_investigations_chemistry_rel', 'lab_request',
                                          'chemistry_investigation', string="Lab Investigation")
    state = fields.Selection(
        [('draft', 'Draft'), ('sample_collected', 'Sample Collected'), ('test_in_progress', 'Test In progress'),
         ('doctor_accept', 'physician decision'), ('close', 'Closed'),
         ('reject', 'Rejected')],
        string='Status', default='draft', tracking=True, copy=False)
    emp_approval = fields.Many2one('res.users', string="Employee Approval", readonly=1)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    is_today = fields.Boolean(default=False, compute='_is_today', store='True')
    duration_mintus = fields.Float("Mintus", compute="compute_duration")
    duration_day = fields.Float("Day", compute="compute_duration")
    duration_second = fields.Float("Seconds", compute="compute_duration")
    account_analytic_id = fields.Many2one('account.analytic.account', string='Cost Center')
    last_issuance_request_id = fields.Many2one('medicare.issuance.request', 'Lab Consumable Request')
    lab_consumble_count = fields.Integer(string="Lab Consumable", compute='_compute_lab_consumble_count')

    def _update_invoice_prices(self):
        """ دالة داخلية لتحديث جدول الأسعار تلقائياً """
        for rec in self:
            # 1. مسح الأسعار القديمة
            rec.invoice_prices_ids = [(5, 0, 0)]
            
            # 2. جمع كل المعرفات المختارة من القوائم الثلاث
            all_investigation_ids = (
                rec.routine_list_ids.ids + 
                rec.serology_list_ids.ids + 
                rec.chemistry_list_ids.ids
            )
            
            if all_investigation_ids:
                # جلب بيانات الفحوصات وأسعارها
                investigations = self.env['investigations.list'].browse(all_investigation_ids)
                
                invoice_data = []
                for inv in investigations:
                    invoice_data.append((0, 0, {
                        'investigation_name': inv.id,
                        'price': inv.price,
                        'lab_request': rec.id
                    }))
                
                # تحديث الحقل
                rec.invoice_prices_ids = invoice_data

    def _compute_lab_consumble_count(self):
        self.lab_consumble_count = self.env['medicare.issuance.request'].search_count(
            [('lab_id.id', '=', self.id)])

    @api.onchange("p_employee")
    def _onchange_employee(self):
        for rec in self:
            if rec.p_employee:
                if rec.p_employee.company_id:
                    rec.company_id = rec.p_employee.company_id.id
                if rec.p_employee.sudo():
                    rec.account_analytic_id = rec.sudo().p_employee.sudo().analytic_account_id
                else:
                    rec.account_analytic_id = False

    @api.onchange("p_contractor")
    def _onchange_p_contractor(self):
        for rec in self:
            if rec.p_contractor:
                if rec.p_contractor.department_id.sudo().analytic_account_id:
                    rec.account_analytic_id = rec.p_contractor.department_id.sudo().analytic_account_id
                else:
                    rec.account_analytic_id = False

    @api.depends('date', 'date_of_analysis')
    def compute_duration(self):
        if self.date and self.date_of_analysis:
            d1 = self.date
            d2 = self.date_of_analysis
            dd = d2 - d1
            self.duration_day = float(dd.days)
            self.duration_mintus = float(dd.seconds // 60)
            self.duration_second = float(dd.seconds % 60)
        else:
            self.duration_day = 0.0
            self.duration_second = 0.0
            self.duration_mintus = 0.0

    def action_lab_consumable(self):
        self.ensure_one()
        env = self.env(user=1)
        res = env['medicare.issuance.request'].create(
            {'type': self.type, 'company_id': self.company_id.id, 'p_employee': self.p_employee.id,
             'p_contractor': self.p_contractor.id,
             'p_quest': self.p_quest.id, 'lab_id': self.id, 'patient': self.patient,
             'type_product': 'lab', 'account_analytic_id': self.account_analytic_id.id
             })
        self.last_issuance_request_id = res.id
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'medicare.issuance.request',
            'res_id': res.id,
            'context': {'form_view_initial_mode': 'edit'},
        }

    def set_lab_consumable(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lab Consumable',
            'view_mode': 'list,form',
            'res_model': 'medicare.issuance.request',
            'domain': [('lab_id.id', '=', self.id)],
            'context': "{'create': False}"
        }

    @api.depends('date')
    def _is_today(self):
        current_date = datetime.date.today()
        for rec in self:
            if rec.date and (rec.date.date() == current_date):
                rec.is_today = True
            else:
                rec.is_today = False

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(LabRequest, self).unlink()

    def sample_close(self):
        return self.write({'state': 'close'})

    def complete_sample(self):
        for rec in self:
            if rec.env.user == rec.responsible_id:
                pass
            elif self.env.user.has_group('base.group_system'):
                pass
            else:
                raise UserError("Sorry. Your are not authorized to approve this document!")
        self.emp_approval = self.env.user
        self.date_of_analysis = fields.Datetime.now()
        if self.doctor_visitor_id:
            self.sudo().doctor_visitor_id.sudo().state = 'lab_result'
        return self.write({'state': 'doctor_accept'})

    def test_samples(self):
        return self.write({'state': 'test_in_progress'})

    def sample_collected(self):
        return self.write({'state': 'sample_collected'})

    def action_draft(self):
        self.result = False
        self.extra_info = False
        for rec in self.lab_result_routine_ids:
            rec.result = False
            rec.selected_result = False
        for rec in self.lab_result_serology_ids:
            rec.result = False
            rec.selected_result = False
        for rec in self.lab_result_chemistry_ids:
            rec.result = False
            rec.selected_result = False
        return self.write({'state': 'draft'})

    @api.onchange('routine')
    def _onchange_routine(self):
        for rec in self:
            if not rec.routine:
                rec.routine_list_ids = False
                rec.lab_result_routine_ids = False

    @api.onchange('serology')
    def _onchange_serology(self):
        for rec in self:
            if not rec.serology:
                rec.serology_list_ids = False
                rec.lab_result_serology_ids = False

    @api.onchange('chemistry')
    def _onchange_chemistry(self):
        for rec in self:
            if not rec.serology:
                rec.chemistry_list_ids = False
                rec.lab_result_chemistry_ids = False

    @api.onchange('routine_list_ids')
    def _onchange_routine_list_ids(self):
        for rec in self:
            # Clear existing lab results
            rec.lab_result_routine_ids = [(5, 0, 0)]

            if rec.routine:
                # Search for investigation attributes
                routine_ids = self.env['investigations.attributes'].search([
                    ('investigations_list_id.lab_invest_id.name', 'ilike', 'Routine'),
                    ('investigations_list_id.id', 'in', rec.routine_list_ids.ids)
                ])

                # Prepare data to dynamically add records to the Many2many field
                lab_result_data = [(0, 0, {'lab_attribute_id': record.id}) for record in routine_ids]

                # Assign the data to the Many2many field
                rec.lab_result_routine_ids = lab_result_data
            rec._update_invoice_prices()

    @api.onchange('serology_list_ids')
    def _onchange_serology_list_ids(self):
        for rec in self:
            # Clear existing lab results
            rec.lab_result_serology_ids = [(5, 0, 0)]

            if rec.serology:
                # Search for investigation attributes
                serology_ids = self.env['investigations.attributes'].search([
                    ('investigations_list_id.lab_invest_id.name', 'ilike', 'Serology'),
                    ('investigations_list_id.id', 'in', rec.serology_list_ids.ids)
                ])

                # Dynamically add virtual records to the Many2many field
                lab_result_data = [(0, 0, {'lab_attribute_id': record.id}) for record in serology_ids]

                # Assign the virtual records to lab_result_serology_ids
                rec.lab_result_serology_ids = lab_result_data
            rec._update_invoice_prices()

    @api.onchange('chemistry_list_ids')
    def _onchange_chemistry_list_ids(self):
        for rec in self:
            # Clear existing lab result records
            rec.lab_result_chemistry_ids = [(5, 0, 0)]

            if rec.chemistry:
                # Search for chemistry investigation attributes
                chemistry_ids = self.env['investigations.attributes'].search([
                    ('investigations_list_id.lab_invest_id.name', 'ilike', 'Chemistry'),
                    ('investigations_list_id.id', 'in', rec.chemistry_list_ids.ids)
                ])

                # Dynamically prepare virtual records for the Many2many field
                lab_result_data = [(0, 0, {'lab_attribute_id': record.id}) for record in chemistry_ids]

                # Assign the virtual records to lab_result_chemistry_ids
                rec.lab_result_chemistry_ids = lab_result_data
            rec._update_invoice_prices()

    def update_all_previous_prices(self):
        x=self.env['lab.request'].search([])
        for rec in x:
            rec.invoice_prices_ids = False
            if rec.serology_list_ids:
                serology_invoice_ids = self.env['investigations.list'].search(
                    [('id', 'in', rec.serology_list_ids.ids)])
                for record in serology_invoice_ids:
                    serologyInvoicePrices = self.env['invoice.prices'].create([{'investigation_name': record.id,
                                                                                'price': record.price,
                                                                                'lab_request': rec.id}])
            if rec.chemistry_list_ids.ids:
                chemistry_invoice_ids = self.env['investigations.list'].search(
                    [('id', 'in', rec.chemistry_list_ids.ids)])
                for record in chemistry_invoice_ids:
                    chemistryInvoicePrices = self.env['invoice.prices'].create([{'investigation_name': record.id,
                                                                                 'price': record.price,
                                                                                 'lab_request': rec.id}])
            if rec.routine_list_ids.ids:
                routine_invoice_ids = self.env['investigations.list'].search(
                    [('id', 'in', rec.routine_list_ids.ids)])
                for record in routine_invoice_ids:
                    RoutineInvoicePrices = self.env['invoice.prices'].create([{'investigation_name': record.id,
                                                                               'price': record.price,
                                                                               'lab_request': rec.id}])

    def prepare_invoice(self):
        for rec in self:
            rec.invoice_prices_ids = False
            if rec.serology_list_ids:
                serology_invoice_ids = self.env['investigations.list'].search(
                    [('id', 'in', rec.serology_list_ids.ids)])
                for record in serology_invoice_ids:
                    serologyInvoicePrices = self.env['invoice.prices'].create([{'investigation_name': record.id,
                                                                                'price': record.price,
                                                                                'lab_request': self.id}])
            if rec.chemistry_list_ids.ids:
                chemistry_invoice_ids = self.env['investigations.list'].search(
                    [('id', 'in', rec.chemistry_list_ids.ids)])
                for record in chemistry_invoice_ids:
                    chemistryInvoicePrices = self.env['invoice.prices'].create([{'investigation_name': record.id,
                                                                                 'price': record.price,
                                                                                 'lab_request': self.id}])
            if rec.routine_list_ids.ids:
                routine_invoice_ids = self.env['investigations.list'].search(
                    [('id', 'in', rec.routine_list_ids.ids)])
                for record in routine_invoice_ids:
                    RoutineInvoicePrices = self.env['invoice.prices'].create([{'investigation_name': record.id,
                                                                               'price': record.price,
                                                                               'lab_request': self.id}])

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('lab.code') or ' '

        return super(LabRequest, self).create(vals)

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
            self.department_id = self.p_employee.department_id
            self.patient = self.p_employee.name
        if self.p_contractor:
            self.patient = self.p_contractor.name
        if self.p_quest:
            self.patient = self.p_quest.name


class LabInvestigationsList(models.Model):
    _name = 'lab.investigations.list'

    name = fields.Many2one('investigations.list', string='investigations list', ondelete='cascade')


class LabResult(models.Model):
    _name = 'lab.result'

    lab_attribute_id = fields.Many2one('investigations.attributes', string='Lab TEST', ondelete='cascade')
    routine_invest_attributes_ids = fields.Many2one('lab.request', string='Investigations Attributes')
    serology_invest_attributes_ids = fields.Many2one('lab.request', string='Investigations Attributes')
    chemistry_invest_attributes_ids = fields.Many2one('lab.request', string='Investigations Attributes')
    result = fields.Char(string="", required=False, )
    selected_result = fields.Selection([
        ('positive', 'Positive'),
        ('negative', 'Negative')], string='Positive/Negative')
    is_selected = fields.Boolean('Is Selected', related='lab_attribute_id.is_selected')
    normal_range = fields.Char(related='lab_attribute_id.normal_range')
    investigation_name = fields.Many2one('investigations.list', related='lab_attribute_id.investigations_list_id')

    @api.onchange('selected_result')
    def _onchange_selected_result(self):
        if self.selected_result == 'positive':
            self.result = 'Positive'
        elif self.selected_result == 'negative':
            self.result = 'Negative'


class InvoicePrices(models.Model):
    _name = 'invoice.prices'

    investigation_name = fields.Many2one('investigations.list',string='Lab Investigation')
    investigation_invest_id = fields.Many2one('lab.investigations', related='investigation_name.lab_invest_id',
                                              )
    lab_request = fields.Many2one('lab.request')
    price = fields.Float()
