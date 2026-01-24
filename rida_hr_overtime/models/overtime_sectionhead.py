from datetime import date, timedelta, datetime
from odoo import fields, models, api, _
from odoo.exceptions import UserError

class OvertimeSectionHead(models.Model):
    _name = 'overtime.sectionhead'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    @api.model
    def default_get(self, fields):
        res = super(OvertimeSectionHead, self).default_get(fields)
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
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    month_selection = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Month')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('w_hr_m', 'HR Manager Approve'),
         ('reject', 'reject'), ('wfm', 'Waiting Finance Manager'), ('internal_aud', 'Internal Audit'),
         ('ccso', 'CCSO Approve'), ('wod', 'Waiting Operation Director'),
         ('wd', 'Waiting Accountant'), ('posted', 'Posted')],
        string='Status', default='draft', track_visibility='onchange')
    state_ccso = fields.Selection(related='state')
    user_type = fields.Selection(related="req_id.user_type")
    employees_line_ids = fields.One2many(comodel_name="overtime.sectionhead.line", inverse_name="request_id",
                                         string="Employees", copy=1)
    total_overtime = fields.Float(string='Total Overtime', store=True, compute="_compute_totals")
    total_tax = fields.Float(string='Total Tax', store=True, compute="_compute_totals")
    total_net_overtime = fields.Float(string='Total Net', store=True, compute="_compute_totals")
    overtime_account_id = fields.Many2one('account.account', string='Overtime Account',
                                          related='company_id.overtime_account_id')
    tax_account_id = fields.Many2one('account.account', string='Tax Account', related='company_id.tax_account_id')
    net_overtime_account_id = fields.Many2one('account.account', string='Net Overtime Account',
                                              related='company_id.net_overtime_account_id')
    journal_id = fields.Many2one('account.move', string='Journal Entry', readonly=1, copy=False)

    @api.model
    def create(self, vals):
        # إنشاء التسلسل أولاً
        vals['name'] = self.env['ir.sequence'].get('overtime.sectionhead') or ' '

        # إنشاء السجل
        res = super(OvertimeSectionHead, self).create(vals)

        # تعبئة الـ One2many تلقائياً بالموظفين
        employees = self.env['hr.employee'].search([
            ('is_section_head', '=', True),
            ('company_id', '=', res.company_id.id)  # إضافة فلتر بالشركة
        ])

        lines = []
        for emp in employees:
            lines.append((0, 0, {
                'employee_id': emp.id,
                'analytic_account_id': emp.contract_id.analytic_account_id.id if emp.contract_id else False,
            }))

        if lines:
            res.write({'employees_line_ids': lines})

        return res

    @api.onchange('date')
    def _onchange_date_set_month(self):
        if self.date:
            self.month_selection = self.date.strftime("%m")


    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(OvertimeSectionHead, self).unlink()

    @api.depends('employees_line_ids.overtime',
                 'employees_line_ids.tax',
                 'employees_line_ids.net_overtime')
    def _compute_totals(self):
        for rec in self:
            rec.total_overtime = sum(rec.employees_line_ids.mapped('overtime'))
            rec.total_tax = sum(rec.employees_line_ids.mapped('tax'))
            rec.total_net_overtime = sum(rec.employees_line_ids.mapped('net_overtime'))

    @api.onchange('employees_line_ids')
    def check_for_doubles(self):
        exist_employee_list = []
        for line in self.employees_line_ids:
            if line.employee_id.id in exist_employee_list:
                raise UserError('The Employee in Overtime Line is duplicate')
            exist_employee_list.append(line.employee_id.id)

    @api.onchange('req_id')
    def onchange_req_id(self):
        if not self.req_id.user_type:
            raise UserError('The Employee Type if NOT Set')

    @api.model
    def action_multiple_confirm(self):
        for order in self:
            if order.state == 'ccso':
                order.approve_ccso()
            elif order.state == 'wod':
                order.approve_operation_director()
            else:
                raise UserError(_("The Request status is not in ccso or Operation Director,cannnot approve"))

    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    def action_submit(self):
        return self.write({'state': 'w_hr_m'})


    def action_hr_manager_approve(self):
        return self.write({'state': 'wfm'})

    def approve_finance_manager(self):
        x = []
        for emp in self.employees_line_ids:
            if not emp.employee_id.address_id:
                x.append(emp.employee_id.name)
        if x:
            raise UserError(f'{x} Doesn\'t Have Partner ')
        return self.write({'state': 'internal_aud'})

    def approve_internal_audit(self):
        if self.user_type == 'hq':
            return self.write({'state': 'ccso'})
        if self.user_type == 'site' or self.user_type == 'fleet':
            return self.write({'state': 'wod'})

    def approve_operation_director(self):
        return self.write({'state': 'wd'})

    def approve_ccso(self):
        return self.write({'state': 'wd'})

    def approve_accountant(self):
        x = []
        for emp in self.employees_line_ids:
            if not emp.employee_id.company_id:
                x.append(emp.employee_id.name)
        if x:
            raise UserError(f'{x} Doesn\'t Assign Company ')

        # Get Dictinct Analytic Account
        anal = []
        for line in self.employees_line_ids:
            if line.analytic_account_id.id in anal:
                continue
            else:
                anal.append(line.analytic_account_id.id)

        line_ids = []
        for cre in anal:

            if not cre:
                continue  # Skip invalid analytic IDs (cre=False)

            record = self.employees_line_ids.filtered(
                lambda line: line.analytic_account_id and line.analytic_account_id.id == cre
            )

            if not record:
                continue
            # record = self.employees_line_ids.filtered(lambda line: line.analytic_account_id.id == cre)

            total_tax = sum(rec.tax for rec in record)
            total_net_overtime = sum(rec.net_overtime for rec in record)
            total_overtime = sum(rec.overtime for rec in record)

            line_ids.append((0, 0,
                             {'debit': 0, 'credit': total_tax, 'name': f'Tax for [{record.analytic_account_id.name}]'
                                 , 'account_id': self.tax_account_id.id,
                              'currency_id': self.company_id.currency_id.id, }))

            line_ids.append((0, 0, {'debit': 0, 'credit': total_net_overtime,
                                    'name': f'Net Overtime for [{record.analytic_account_id.name}]'
                , 'account_id': self.net_overtime_account_id.id, 'currency_id': self.company_id.currency_id.id, }))
            line_ids.append((0, 0, {'debit': total_overtime, 'credit': 0, 'name': f'Overtime'
                , 'account_id': self.overtime_account_id.id,
                                    'analytic_distribution': {cre: 100},
                                    'currency_id': self.company_id.currency_id.id, }))

        move_line = self.env['account.move'].sudo().create({
            'ref': self.name,
            'move_type': 'entry',
            'currency_id': self.company_id.currency_id.id,
            'invoice_date': fields.Date.today(),
            'date': fields.Date.today(),
            'line_ids': line_ids,
            'company_id': self.company_id.id,
        })

        move_line.sudo().action_post()
        self.journal_id = move_line.id

        return self.write({'state': 'posted'})




class OvertimeSectionHeadLine(models.Model):
    _name = 'overtime.sectionhead.line'

    request_id = fields.Many2one("overtime.sectionhead")
    state = fields.Selection(related='request_id.state')
    month_selection = fields.Selection(related='request_id.month_selection',store=True)
    date = fields.Date(related='request_id.date')
    company_id = fields.Many2one(related='request_id.company_id',store=True)
    employee_id = fields.Many2one("hr.employee", string="Employee")
    department_id = fields.Many2one('hr.department', string="Department",related='employee_id.department_id')
    partner_id = fields.Many2one(comodel_name="res.partner", string="Partner", related='employee_id.address_id',
                                 readonly=True)
    job_id = fields.Many2one('hr.job', string="Job", related='employee_id.job_id')
    gross = fields.Integer("Gross", compute='_compute_gross', copy=True,group="")
    work_from = fields.Date(string="From", compute='_compute_dates', store=True)
    work_to = fields.Date(string="To", compute='_compute_dates', store=True)
    overtime = fields.Float(compute='_compute_hours', string='Overtime')
    tax = fields.Float(compute='_compute_hours', string='Tax')
    net_overtime = fields.Float(compute='_compute_hours', string='Net Overtime')
    request_state = fields.Selection(
        [('draft', 'Draft'),
         ('w_hr_m', 'HR Manager Approve'),
         ('reject', 'reject'), ('wfm', 'Waiting Finance Manager'), ('internal_aud', 'Internal Audit'),
         ('ccso', 'CCSO Approve'), ('wod', 'Waiting Operation Director'),
         ('wd', 'Waiting Accountant'), ('posted', 'Posted')],
        string='Status', related='request_id.state')
    remarks = fields.Text("Remarks")
    analytic_account_id = fields.Many2one("account.analytic.account", )
    b_account = fields.Many2one("res.partner.bank", related='employee_id.bank_account_id', string="Bank Account",
                                readonly=True)

    @api.onchange('request_id')
    def _onchange_request_id(self):
        if self.request_id:
            return {
                'domain': {
                    'employee_id': [
                        ('is_section_head', '=', True),
                        ('company_id', '=', self.company_id.id),
                    ]
                }
            }

    @api.depends('request_id.month_selection')
    def _compute_dates(self):
        for record in self:
            if record.request_id and record.request_id.month_selection:
                year = date.today().year  # You can modify this if you want a different year
                month = int(record.request_id.month_selection)
                start_date = date(year, month, 1)

                # Calculate the last day of the month
                if month == 12:
                    end_date = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(year, month + 1, 1) - timedelta(days=1)

                record.work_from = start_date
                record.work_to = end_date


    @api.onchange('normal_hours', 'holiday_hours', 'work_nat_hours')
    def _compute_hours(self):
        for rec in self:
            if  rec.gross:
                rec.overtime = rec.gross
                rec.tax = round(rec.overtime * 0.05)
                rec.net_overtime = rec.overtime - rec.tax
            else:
                rec.overtime = 0.0
                rec.tax = 0.0
                rec.net_overtime = 0.0

    @api.depends('employee_id')
    def _compute_gross(self):
        for rec in self:
            if rec.employee_id:
                emp = self.env['hr.employee'].search([('id', '=', rec.employee_id.id)])
                if emp:
                    # if emp.sudo().contract_id.sudo().payroll_wage:
                    rec.gross = emp.sudo().contract_id.sudo().payroll_wage
                    # else:
                    #     raise UserError(f'The Employee {emp.name} Dosen\'t Have Gross on Contract')
                    if not emp.sudo().contract_id.sudo().analytic_account_id.id:
                        raise UserError(f'The Employee {emp.name} Dosen\'t Have Analytic Account')
                    else:
                        rec.analytic_account_id = emp.sudo().contract_id.sudo().analytic_account_id.id
                else:
                    rec.gross = 0
            else:
                rec.gross = 0

    def unlink(self):
        for rec in self:
            if rec.request_id.overtime_auth_id != False:
                raise UserError("Sorry! The Overtime records can't be deleted!")

        return super(OvertimeSectionHeadLine, self).unlink()
