from datetime import date, timedelta, datetime
from odoo import fields, models, api
from odoo.exceptions import UserError
import calendar


class OvertimeAuth(models.Model):
    _name = 'overtime.auth'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    @api.model
    def default_get(self, fields):
        res = super(OvertimeAuth, self).default_get(fields)
        if res.get('req_id', False):
            emp = self.env['hr.employee'].sudo().search([('user_id', '=', res['req_id'])],
                                                        limit=1)

            current_month = datetime.now().month
            print(">>>>>>>>>>",current_month)
            if current_month==1:
                month_selection='01'
            elif current_month==2:
                month_selection='02'
            elif current_month==3:
                month_selection='03'
            elif current_month==4:
                month_selection='04'
            elif current_month==5:
                month_selection='05'
            elif current_month==6:
                month_selection='06'
            elif current_month==7:
                month_selection='07'
            elif current_month==8:
                month_selection='08'
            elif current_month==9:
                month_selection='09'
            elif current_month==10:
                month_selection='10'
            elif current_month==11:
                month_selection='11'
            elif current_month==12:
                month_selection='12'

            res.update({
                'department_id': emp.department_id.id,
                'job_req_id': emp.job_id.id,
                'month_selection': month_selection if month_selection else False
            })
        return res

    name = fields.Char(string='Name', default=lambda self: 'NEW')
    date = fields.Date(default=fields.Date.today())
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True)
    department_id = fields.Many2one('hr.department', string="Department")
    job_req_id = fields.Many2one('hr.job', string='Job Title')
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    description = fields.Text('Detailed explanation why overtime is needed?')
    user_type = fields.Selection(related="req_id.user_type")
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
        [('draft', 'Draft'), ('wlm', 'Waiting Line Manager'), ('hr_off', 'HR Officer Verify'),
         ('w_hr_m', 'HR Manager Approve'),
         ('reject', 'reject'), ('ccso', 'CCSO Approve'), ('wod', 'Waiting Operation Director'),
         ('auth', 'Authorized')],
        string='Status', default='draft', track_visibility='onchange')
    state_ccso = fields.Selection(related='state')
    employees_line_ids = fields.One2many(comodel_name="overtime.auth.line", inverse_name="request_id",
                                         string="Employees", copy=1)
    overtime_count = fields.Integer(string="Count", compute='compute_overtime_count')

    show_button = fields.Boolean(string='Show Button')

    # show_button = fields.Boolean(compute='_compute_show_button', string='Show Button')

    @api.onchange('department_id')
    def _onchange_dept(self):
        for rec in self:
            if rec.department_id:
                # Fetch employees in the relevant departments
                rec_emp_ids = self.env['hr.employee'].search([
                    ('department_id', 'child_of', rec.department_id.id),
                    ('company_id', '=', rec.company_id.id)
                ])

                # Reset employees_line_ids properly
                rec.employees_line_ids = [(5, 0, 0)]  # Clears the existing lines

                # Add new lines for employees
                for rec_emp in rec_emp_ids:
                    if rec_emp.sudo().contract_id.sudo().payroll_wage:
                        print('>>>>>>>', rec_emp.id, rec.description, rec.id)
                        rec.employees_line_ids = [(0, 0, {
                            'employee_id': rec_emp.id,
                            'remarks': rec.description or False,
                            'request_id': rec.id,
                        })]

    # @api.depends('create_date')
    # def _compute_show_button(self):
    #     for record in self:
    #         current_date = date.today()
    #         current_day = current_date.day
    #         last_day_of_month = (current_date.replace(day=1, month=current_date.month + 1) - timedelta(days=1)).day
    #         record.show_button = current_day >= 25 and current_day <= last_day_of_month

    def compute_overtime_count(self):
        self.overtime_count = self.env['hr.overtime.batch'].search_count([('overtime_auth_id', '=', self.id)])

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('overtime.auth.code') or ' '
        res = super(OvertimeAuth, self).create(vals)
        return res

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(OvertimeAuth, self).unlink()

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

    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    def action_submit(self):
        return self.write({'state': 'wlm'})

    def action_approve(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                pass
            else:
                self.ensure_one()
                try:
                    line_manager = self.req_id.line_manager_id
                except:
                    line_manager = False
                # comment by ekhlas
                # if not line_manager or not self.user_has_groups('material_request.group_department_manager'):
                #     raise UserError("Sorry. Your are not authorized to approve this document!")
                if not line_manager or line_manager != rec.env.user:
                    raise UserError("Sorry. Your are not authorized to approve this document!")
        return self.write({'state': 'hr_off'})

    def action_off_approve(self):
        return self.write({'state': 'w_hr_m'})

    def action_hr_manager_approve(self):
        if self.user_type == 'hq':
            return self.write({'state': 'ccso'})
        if self.user_type == 'site' or self.user_type == 'fleet':
            return self.write({'state': 'wod'})

    def approve_operation_director(self):
        return self.write({'state': 'auth'})

    def approve_ccso(self):
        return self.write({'state': 'auth'})

    @api.model
    def action_multiple_confirm(self):
        for order in self:
            if order.state == 'ccso':
                order.approve_ccso()
            elif order.state == 'wod':
                order.approve_operation_director()
            else:
                raise UserError("The Request status is not in ccso or Operation Director,cannnot approve")


    def create_overtime_by_batch(self):
        self.ensure_one()
        emp_line_ids = []
        if self.employees_line_ids:
            for rec in self.employees_line_ids:
                emp_line_ids.append(
                    (0, 0, {'employee_id': rec.employee_id.id, 'work_from': rec.work_from, 'work_to': rec.work_to,
                            'max_normal_hours': rec.normal_hours, 'max_holiday_hours': rec.holiday_hours,
                            'max_work_nat_hours': rec.work_nat_hours, 'remarks': rec.remarks}))
            res = self.env['hr.overtime.batch'].create(
                {'month_selection': self.month_selection, 'description': self.description,
                 'company_id': self.company_id.id,
                 'department_id': self.department_id.id, 'job_req_id': self.job_req_id.id, 'overtime_auth_id': self.id,
                 'employees_line_ids': emp_line_ids or False})
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'hr.overtime.batch',
                'res_id': res.id,
                'context': {'form_view_initial_mode': 'edit'},
            }

    def set_overtime_by_batch(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'OverTime By Batch',
            'view_mode': 'tree,form',
            'res_model': 'hr.overtime.batch',
            'domain': [('overtime_auth_id', '=', self.id)],
            'context': "{'create': False}"
        }


class OvertimeAuthLine(models.Model):
    _name = 'overtime.auth.line'

    # @api.model
    # def default_get(self, fields):
    #     res = super(OvertimeAuthLine, self).default_get(fields)
    #     start_date = date.today().strftime('%Y-%m-01')
    #     current_date = date.today()
    #     default_date = calendar.monthrange(current_date.year, current_date.month)[1]
    #     end_date = current_date.replace(day=default_date).strftime('%Y-%m-%d')
    #     res.update({
    #         'work_from': start_date,
    #         'work_to': end_date,
    #     })
    #     return res

    request_id = fields.Many2one("overtime.auth")
    employee_id = fields.Many2one("hr.employee", string="Employee")
    work_from = fields.Date(string="From", compute='_compute_dates', store=True)
    work_to = fields.Date(string="To", compute='_compute_dates', store=True)
    normal_hours = fields.Float(string="Normal H")
    holiday_hours = fields.Float(string="Holidays H")
    work_nat_hours = fields.Float(string="Work Nature H")
    job_id = fields.Many2one('hr.job', string="Job", related='employee_id.job_id', readonly=1)
    department_id = fields.Many2one('hr.department', string="Department requires support")
    remarks = fields.Text("Remarks")

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

    @api.constrains('employee_id')
    def check_employee_auth_id(self):
        for rec in self:
            if rec.employee_id:
                emp = self.env['hr.employee'].search([('id', '=', rec.employee_id.id)])
                if emp:
                    if not emp.sudo().contract_id.sudo().payroll_wage:
                        raise UserError(f'The Employee {emp.name} Dosen\'t Have Gross on Contract')
                    if not emp.sudo().contract_id.sudo().analytic_account_id.id:
                        raise UserError(f'The Employee {emp.name} Dosen\'t Have Analytic Account')
