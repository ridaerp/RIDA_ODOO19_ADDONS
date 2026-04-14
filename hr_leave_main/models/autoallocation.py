from odoo import fields , api , models , _
import datetime
from datetime import timedelta,time
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError,UserError
import logging
_logger = logging.getLogger(__name__)


class hrLeave(models.Model):
    _inherit = 'hr.leave'

    delegated_employee_id = fields.Many2one(comodel_name='hr.employee', string='Delegated Employee')
    justification = fields.Text(string='Justification', readonly=True)

    medical_report = fields.Binary(string='Medical Report')
    leave_type_test = fields.Selection(string='Leave type test', related='holiday_status_id.leave_type')
    attachment = fields.Binary(string='Attachment')
    cut_leave = fields.Boolean("Leave Cut", default=False, tracking=True)


    mercy_relation = fields.Selection([
        ('father', 'وفاة الوالد'),
        ('mother', 'وفاة الوالدة'),
        ('spouse', 'وفاة زوج/زوجة'),
        ('child', 'وفاة الأبناء'),
        ('grandfather', 'وفاة الجد'),
        ('grandmother', 'وفاة الجدة'),
        ('hospital', 'أحد الأقارب بالمستشفى'),
        ('natural', 'كوارث طبيعية'),
    ], string="سبب الاجازة")
    show_mercy_relation = fields.Boolean(compute='_compute_show_mercy_relation')

    @api.depends('holiday_status_id')
    def _compute_show_mercy_relation(self):
        for rec in self:
            rec.show_mercy_relation = rec.holiday_status_id.name == 'Compassionate'

    @api.onchange('mercy_relation', 'holiday_status_id', 'request_date_from')
    def _onchange_mercy_relation(self):
        for rec in self:
            if rec.holiday_status_id and rec.holiday_status_id.name == 'Compassionate':
                days = 0
                if rec.mercy_relation in ['father', 'mother', 'child', 'spouse']:
                    days = 5
                elif rec.mercy_relation in ['grandfather', 'grandmother']:
                    days = 3
                elif rec.mercy_relation in ['hospital', 'natural']:
                    days = 2

                rec.number_of_days_display = days
                if rec.request_date_from and days > 0:
                    rec.request_date_to = rec.request_date_from + timedelta(days=days - 1)

    def action_cut_leave(self):
        self.write({
            'state': 'draft',
            'cut_leave': True
        })

    def action_refuse(self):

        return {
            'type': 'ir.actions.act_window',
            'name': 'Justification',
            'view_mode': 'form',
            'view_id': self.env.ref('hr_leave_main.wizard_justification_view_form').id,
            'target': 'new',
            'res_model': 'justification.justification',

        }
        # return True

    def return_wizard(self):
        # raise UserError(self.env.ref('hr_leave_main.justification_open_wizard').name)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Justification',
            'view_mode': 'form',
            'view_id': self.env.ref('hr_leave_main.wizard_justification_view_form').id,
            'target': 'new',
            'res_model': 'justification.justification',

        }

    state = fields.Selection([
        ('draft', 'To Submit'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('line_manager', 'Line Manager'),
        ('hr_officer', ' HR officer'),
        ('ccso', 'COO'),
        ('validate', 'Approved'),
        ('cancel', 'Cancelled'),
    ], string='Status', store=True, tracking=True, copy=False, readonly=False, default='draft')


    click = fields.Boolean(string='Check', default=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # طباعة للتتبع
        _logger.info(f"default_get called with fields: {fields_list}")
        _logger.info(f"default_get result before state: {res}")

        if 'state' in fields_list:
            res['state'] = 'draft'

        _logger.info(f"default_get result after setting state: {res}")
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'state' not in vals or vals.get('state') == 'cancel':
                vals['state'] = 'draft'

            if vals.get('employee_id'):
                employee = self.env['hr.employee'].browse(vals.get('employee_id'))
                contracts = self.env['hr.version'].search([
                    ('employee_id', '=', employee.id),
                ])
                if not contracts:
                    _logger.warning(f"Employee {employee.name} has no contracts when creating leave")

        records = super().create(vals_list)
        return records

    @api.constrains('date_from', 'date_to')
    def _check_contracts(self):
        """
        A leave cannot be set across multiple contracts.
        Note: a leave can be across multiple contracts despite this constraint.
        It happens if a leave is correctly created (not across multiple contracts) but
        contracts are later modifed/created in the middle of the leave.
        """
        for holiday in self.filtered('employee_id'):
            try:
                versions = holiday._get_overlapping_contracts()
                # التحقق من وجود versions وأنها ليست None
                if versions and hasattr(versions, 'resource_calendar_id'):
                    if len(versions.resource_calendar_id) > 1:
                        raise ValidationError(
                            _("A leave cannot be set across multiple versions with different working schedules.")
                        )
            except AttributeError:
                # إذا كان الموظف ليس لديه عقود، نتجاهل التحقق
                continue
            except Exception as e:
                # تسجيل الخطأ للتصحيح ولكن لا نمنع إنشاء الإجازة
                _logger.warning(f"Error checking contracts for leave {holiday.id}: {e}")
                continue

    def _get_overlapping_contracts(self):
        """
        Get contracts that overlap with the leave period.
        Overridden to handle cases where employee has no contracts.
        """
        if not self.employee_id:
            return self.env['hr.contract'].browse()

        # تأكد من وجود date_from و date_to
        if not self.date_from or not self.date_to:
            return self.env['hr.contract'].browse()

        try:
            # محاولة استدعاء الدالة الأصلية
            result = super()._get_overlapping_contracts()
            return result if result else self.env['hr.contract'].browse()
        except Exception:
            # إذا فشلت، نعيد مجموعة فارغة
            return self.env['hr.contract'].browse()

    @api.onchange('holiday_status_id')
    def _onchange_(self):
        for rec in self:
            if rec.holiday_status_id.leave_type == 'unpaid':
                leave_count = 0.0
                leave_days = self.env['hr.leave.report'].search(
                    [('employee_id', '=', self.employee_id.id), ('leave_type', 'in', ['allocation', 'request'])])
                for leave in leave_days:
                    leave_count += leave.number_of_days
                    if leave_count == 0:
                        rec.click = True
                    else:
                        raise UserError(
                            _('Sorry!!! You can not request unpaid leave. You have days left in your balance.'))
            else:
                rec.click = False




    def _get_number_of_days(self, date_from, date_to, employee_id):

        if self.request_unit_half:
            # """ Returns a float equals to the timedelta between two dates given as string."""
            if employee_id:
                employee = self.env['hr.employee'].browse(employee_id)
                return employee._get_work_days_data(date_from, date_to)

            today_hours = self.env.company.resource_calendar_id.get_work_hours_count(
                datetime.combine(date_from.date(), time.min),
                datetime.combine(date_from.date(), time.max),
                False)
            hours = self.env.company.resource_calendar_id.get_work_hours_count(date_from, date_to)
            return {'days': hours / (today_hours), 'hours': hours}

        else:
            days = 0
            from_dt = fields.Datetime.from_string(date_from)
            to_dt = fields.Datetime.from_string(date_to)
            if from_dt and to_dt:
                time_delta = to_dt - from_dt
                days = time_delta.days + 1
            day_list = []
            while from_dt <= to_dt:
                day_list.append(from_dt.date())
                from_dt += timedelta(days=1)
            if self.holiday_status_id.exclude_weekend:
                for day in day_list:
                    if day.weekday() == 4 or day.weekday() == 5:
                        days -= 1
            if self.holiday_status_id.exclude_public:
                for p_id in self.env['hr.public.holidays'].search([]):
                    for day in day_list:
                        if ((fields.Datetime.from_string(p_id.date_from).date() <= day) and (
                                day <= fields.Datetime.from_string(p_id.date_to).date())):
                            if day.weekday() != 4 and day.weekday() != 5:
                                days -= 1
            days_total = days
            hours = self.env.company.resource_calendar_id.get_work_hours_count(date_from, date_to)
            return {'days': days_total, 'hours': hours}


    def submit(self):
        self.write({ 'state': 'line_manager' })

    # line_manager buttons
    def lm_approve(self):
        self.write({ 'state': 'hr_officer' })

    def lm_approve_reject(self):
        self.write({ 'state': 'draft' })

    # hr_officer buttons
    def hr_approve(self):
        self.write({ 'state': 'validate1' })

    def hr_manager_approve(self):
        self.write({ 'state': 'validate' })

    def hr_approve_reject(self):
        self.write({ 'state': 'line_manager' })

    # ccso buttons
    def ccso_approve(self):
        self.write({ 'state': 'validate'})

    def ccso_approve_reject(self):
        self.write({ 'state': 'refuse' })

    # cancel and set to draft buttons
    def cancel(self):
        self.write({ 'state': 'refuse' })

    def set_to_draft(self):
        self.write({ 'state': 'draft' })



