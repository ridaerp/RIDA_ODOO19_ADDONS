from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, format_date
from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
import datetime

class RotationBatch(models.Model):
    _name = 'rotation.batch'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    holiday_status_id = fields.Many2one(
        'hr.leave.type', 'Type')
    date = fields.Date(readonly=1, default=fields.Date.today())
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True, )
    department_id = fields.Many2one('hr.department', string="Department")
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    company_id = fields.Many2one('res.company', string='Company')
    state = fields.Selection(
        [('draft', 'Draft'), ('wlm', 'Waiting Line Manager'),  ('wha', 'Waiting HR Verification'),
         ('whmp', 'Waiting HR Manager Approve'),
         ('reject', 'reject'), ('wfm', 'Waiting Finance Manager'),
         ('ccso', 'COO Approve'), ('wod', 'Waiting COO Approval'),
         ('wd', 'Waiting Accountant'),('internal_aud', 'Internal Audit'),('wdp', 'Waiting Payment'), ('paid', 'Paid')],
        string='Status', default='draft', tracking=True)
    state_ccso = fields.Selection(related='state')
    employees_line_ids = fields.One2many(comodel_name="employees.rotation.line", inverse_name="request_id",
                                         string="Employees", copy=1)
    leave_ids = fields.Many2many(comodel_name="hr.leave")
    expense_account_id = fields.Many2one('account.account', string='Expense Account', )
    journal_id = fields.Many2one('account.move', string='Journal Entry', readonly=1, copy=False)
    journal_payment_id = fields.Many2one('account.journal', string='Payment Journal', copy=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    type = fields.Selection(string="", selection=[('in', 'in'), ('out', 'out'), ], )
    user_type = fields.Selection(related="req_id.user_type")
    employee_id = fields.Many2one('hr.employee', related='employees_line_ids.employee_id', string='Employees',
                                  readonly=False)

    def _check_rotation_date_constraint(self):
        """
        يتحقق مما إذا كان اليوم الحالي يقع في فترة المنع (5-7) أو (20-نهاية الشهر).
        """
        # التحقق من وجود تاريخ
        if not self.date:
            return True  # إذا لم يكن هناك تاريخ، نسمح بإنشاء الطلب

        current_day = self.date.day
        if self.type in ['in', 'out']:
            # فترة المنع الأولى: من اليوم الخامس (5) وحتى اليوم السابع (7)
            is_blocked_period_1 = (5 <= current_day <= 7)

            # فترة المنع الثانية: من اليوم العشرين (20) وحتى نهاية الشهر
            is_blocked_period_2 = (current_day >= 20)

            if is_blocked_period_1 or is_blocked_period_2:
                return False  # التحقق فشل: يجب منع الإجراء

        return True  # التحقق نجح: الأيام المسموح بها (1-4) و (8-19)

    @api.model
    def create(self, vals):
        for val in vals:
            # التحقق من وجود type في القيم
            if 'type' in val and val['type'] in ['in', 'out']:
                # التحقق من القيد الزمني
                # إنشاء سجل مؤقت للتحقق
                new_record = self.new(val)

                # تعيين التاريخ إذا لم يكن موجوداً
                if 'date' not in val or not val['date']:
                    new_record.date = fields.Date.today()

                if not new_record._check_rotation_date_constraint():
                    raise UserError(
                        _("Rotation Leave Request (Type 'in'/'out') can only be created between the 1st and 4th, or between the 8th and 19th day of the month."))

                val['name'] = self.env['ir.sequence'].next_by_code('rotation.request') or ' '
            else:
                val['name'] = self.env['ir.sequence'].next_by_code('arrival.request') or ' '

        return super(RotationBatch, self).create(vals)


    def action_correct_ticket(self):
        x = self.env['employees.rotation.line'].search([])
        for rec in x:
            rec.amount = rec.location_id.amount

    @api.onchange('req_id')
    def onchange_req_id(self):
        if not self.req_id.user_type:
            raise UserError('The Employee Type if NOT Set')

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")

        return super(RotationBatch, self).unlink()

    @api.onchange('employees_line_ids')
    def check_for_doubles(self):
        exist_employee_list = []
        for line in self.employees_line_ids:
            if line.employee_id.id in exist_employee_list:
                raise UserError('The Employee in Time Off Line is duplicate')
            exist_employee_list.append(line.employee_id.id)

    def action_submit(self):
        if self.holiday_status_id.sudo().expense_account_id:
            self.expense_account_id = self.holiday_status_id.sudo().expense_account_id
        if self.type == "in":
            for emp in self.employees_line_ids:
                if emp.date_from > emp.date_to:
                    raise UserError('The End Date is Grather Thans Start Date')
            for emp in self.employees_line_ids:
                leave = self.env['hr.leave'].sudo().create({
                    'employee_id': emp.employee_id.id,
                    'holiday_status_id': self.holiday_status_id.id,
                    'request_date_from': emp.date_from,
                    'request_date_to': emp.date_to,
                    'number_of_days': emp.number_of_days,
                })
                self.sudo().write({'leave_ids': [(4,
                                           leave.id
                                           )]})
        return self.write({'state': 'wlm'})


    def action_approve(self):
        for rec in self:
            if not rec._check_rotation_date_constraint():
                raise UserError(
                        _("Rotation Leave Request can only be approved to HR Verification between the 1st and 4th, or between the 8th and 19th day of the month."))
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
        if self.leave_ids:
            for rec in self.leave_ids:
                if rec.state == 'confirm':
                    rec.action_approve()
                else:
                    pass
        return self.write({'state': 'wha'})

    def action_hr_manager_approve(self):
        return self.write({'state': 'wfm'})

    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    def action_reject(self):
        for _rec in self:
            if _rec.leave_ids:
                for rec in _rec.leave_ids:
                    wizard = self.env['justification.justification'].create({
                        'justification': f'Rejected By {self.env.user.name}',
                    })
                    wizard.with_context(active_id=rec.id).button_confirm()
            _rec.state = "reject"

    def action_validate(self):
        if self.leave_ids:
            for rec in self.leave_ids:
                if rec.state == 'validate1':
                    rec.action_validate()
                else:
                    pass
        return self.write({'state': 'whmp'})

    def approve_finance_manager(self):
        x = []
        for emp in self.employees_line_ids:
            if not emp.employee_id.employee_partner_id:
                x.append(emp.employee_id.name)
        if x:
            raise UserError(f'{x} Doesn\'t Have Partner ')
        return self.write({'state': 'wd'})

    def approve_internal_audit(self):
        # if self.user_type == 'hq':
        #     return self.write({'state': 'ccso'})
        # if self.user_type == 'site' or self.user_type == 'fleet':
        # if order.state == 'wdp':
        #     order.action_register_payment()
            return self.write({'state': 'wdp'})

    @api.model
    def action_multiple_confirm(self):
        for order in self:
            if order.state == 'ccso':
                order.approve_ccso()
            elif order.state == 'wod':
                order.approve_operation_director()
            else:
                raise UserError(_("The Request status is not in ccso or Operation Director,cannnot approve"))

    @api.model
    def action_multiple_payment(self):
        for order in self:
            if order.state == 'wdp':
                order.action_register_payment()
            else:
                raise UserError(_("Th Request status is not in Waiting Payment,cannnot Register Payment"))

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

        line_ids = []
        for cre in self.employees_line_ids:
            line_ids.append((0, 0, {'debit': 0, 'credit': cre.amount, 'partner_id': cre.partner_id.id
                , 'account_id': cre.account_payable.id, 'currency_id': self.company_id.currency_id.id,  }))
        for deb in self.employees_line_ids:
            line_ids.append((0, 0, {'debit': deb.amount, 'credit': 0, 'partner_id': deb.partner_id.id
                , 'account_id': self.expense_account_id.id,
                                    'analytic_distribution': {deb.analytic_account_id.id: 100},
                                    'currency_id': self.company_id.currency_id.id, }))
        move_line = self.env['account.move'].sudo().with_context(
                    check_move_validity=False).create({
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

        return self.write({'state': 'internal_aud'})

    def action_register_payment(self):
        for recc in self:
            if not recc.journal_payment_id:
                raise UserError(_("Please Enter Payment Journal"))
            for rec in recc.employees_line_ids:
                create_payment = {
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'partner_id': rec.partner_id.id,
                    # 'destination_account_id':rec.account_id.id,
                    'company_id': recc.company_id.id,
                    'amount': rec.amount,
                    'currency_id': recc.company_id.currency_id.id,
                    'payment_reference': recc.name,
                    'journal_id': recc.journal_payment_id.id,

                }
                po = self.env['account.payment'].sudo().with_context(
                    check_move_validity=False).create(create_payment)
                po.action_post()
                recc.state = "paid"
            return po

    def button_action_post(self):
        for record in self:
            po = self.env['account.payment'].search([('ref', '=', record.name)])
            po.action_post()
            record.state = "paid"

    def get_timeoff(self):
        self.ensure_one()
        tree_view_id = self.env.ref('hr_holidays.hr_leave_view_tree').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Time Off',
            # 'view_id': tree_view_id,
            'view_mode': 'list,form',
            'res_model': 'hr.leave',
            'domain': [('id', 'in', self.leave_ids.ids)],
            'context': "{'create': False}"
        }

    def get_payment(self):
        self.ensure_one()
        tree_view_id = self.env.ref('account.view_account_supplier_payment_tree').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment',
            'view_id': tree_view_id,
            'view_mode': 'list',
            'res_model': 'account.payment',
            'domain': [('payment_reference', '=', self.name)],
            'context': {'create': False}
        }


class EmployeesRotationLine(models.Model):
    _name = 'employees.rotation.line'
    _order = "create_date desc"

    request_id = fields.Many2one("rotation.batch", string="Employee")
    employee_id = fields.Many2one("hr.employee", string="Employee")
    partner_id = fields.Many2one('res.partner', string='Partner')
    location_id = fields.Many2one("locations.detail")
    amount = fields.Float()
    need_money_for_rotation = fields.Boolean(string="need money",default=True)
    b_account = fields.Many2one("res.partner.bank", related='employee_id.bank_account_id', string="Bank Account",
                                readonly=True)
    date_to = fields.Date('End Date', store=True, readonly=False, index=True,
                          tracking=True)
    date_from = fields.Date('Start Date', readonly=False, index=True,
                            tracking=True, default=fields.Date.today())
    date_arrival = fields.Date('Arrival Date', readonly=False, index=True,
                               tracking=True)
    number_of_days = fields.Float(
        'Days', compute='_compute_number_of_days', store=True, copy=False, tracking=True)
    analytic_account_id = fields.Many2one("account.analytic.account", )
    num_bus = fields.Integer(string='N.Of Bus')
    num_ticket = fields.Integer(string='N.Of Ticket')


    @api.onchange('need_money_for_rotation')
    def check_need_money_for_rotation_id(self):
        for rec in self:
            if not rec.need_money_for_rotation:
                rec.amount=0
            else:
                if rec.location_id:
                    self.amount = self.location_id.amount

    @api.constrains('date_from', 'date_to', 'location_id','amount')
    def _check_duplicate_time_off(self):
        for rec in self:
            # Skip checks if money is not needed
            if not rec.need_money_for_rotation:
                continue

            if rec.location_id != rec.employee_id.location_id:
                raise UserError(f'The Location of Employee {rec.employee_id.name} {rec.employee_id.location_id.name}')
            if rec.location_id.amount != rec.amount:
                raise UserError(f'The Amount of Location of Employee cannot be changed {rec.location_id.amount}')


        if self.request_id.type == "in":
            for record in self:
                duplicate_records = self.env['hr.leave'].search([
                    ('id', '!=', record.id),
                    ('employee_id', '=', record.employee_id.id),
                    ('holiday_status_id', '=', record.request_id.holiday_status_id.id),
                    '|',
                    '&', ('date_from', '<=', record.date_from), ('date_to', '>=', record.date_from),
                    '&', ('date_from', '<=', record.date_to), ('date_to', '>=', record.date_to),
                ])
                if duplicate_records:
                    raise UserError(
                        f"Duplicate time-off request found for the same duration for {record.employee_id.name}.")

    @api.onchange('employee_id')
    def check_employee_id(self):
        if self.employee_id:
            rec = self.env['hr.employee'].sudo().search([('id', '=', self.employee_id.id)])
            if rec.location_id:
                self.location_id = rec.location_id
                self.amount = self.location_id.amount
            else:
                raise UserError(f'The Employee {rec.name} Dosen\'t Have location (Check it with HR)')
            if not rec.sudo().analytic_account_id.id:
                raise UserError(f'The Employee {rec.name} Dosen\'t Have Analytic Account')
            else:
                self.analytic_account_id = rec.sudo().analytic_account_id.id

    @api.depends('date_from', 'date_to', 'employee_id')
    def _compute_number_of_days(self):
        for holiday in self:
            if holiday.date_from and holiday.date_to:
                holiday.number_of_days = abs((holiday.date_from - holiday.date_to).days) + 1
            else:
                holiday.number_of_days = 0


class LocationsDetail(models.Model):
    _name = 'locations.detail'
    _order = "create_date desc"

    name = fields.Char(string='Location', required=True)
    amount = fields.Float(required=True, default=0)
    city = fields.Boolean(string='City', default=False)
