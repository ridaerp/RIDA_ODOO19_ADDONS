# from typing_extensions import Required
from odoo import _, api, fields, models


class Hr_leave_extend(models.Model):
    _inherit = 'hr.leave'
    delegated_employee_id = fields.Many2one(comodel_name='hr.employee', string='Delegated Employee')
    justification = fields.Text(string='Justification', readonly=True)
    
    medical_report = fields.Binary(string= 'Medical Report')
    leave_type_test = fields.Selection(string='Leave type test', related='holiday_status_id.leave_type')

    # @api.depends('number_of_days')
    # def _compute_number_of_days_display(self):
    #     for holiday in self:
    #         if holiday.date_from and holiday.date_to:
    #             holiday.number_of_days = abs((holiday.request_date_from - holiday.request_date_to).days) + 1
    #         else:
    #             holiday.number_of_days = 0
    #         holiday.number_of_days_display=holiday.number_of_days



    # def required_lg(self):
    #     if self.medical_report:



    # def _validate_leave_request(self):
    #     """ Validate time off requests (holiday_type='employee')
    #     by creating a calendar event and a resource time off. """
    #     # holidays = self.filtered(lambda request: request.holiday_type == 'employee')
    #     holidays = self.filtered(
    #         lambda request: request.employee_id)  # Filters only if leave is for a specific employee
    #     holidays._create_resource_leave()
    #     meeting_holidays = holidays.filtered(lambda l: l.holiday_status_id.create_calendar_meeting)
    #     meetings = self.env['calendar.event']
    #     if meeting_holidays:
    #         meeting_values_for_user_id = meeting_holidays._prepare_holidays_meeting_values()
    #         for user_id, meeting_values in meeting_values_for_user_id.items():
    #             meetings += self.env['calendar.event'].with_user(user_id or self.env.uid).with_context(
    #                             no_mail_to_attendees=True,
    #                             active_model=self._name
    #                         ).sudo().create(meeting_values)
    #     Holiday = self.env['hr.leave']
    #     for meeting in meetings:
    #         Holiday.browse(meeting.res_id).meeting_id = meeting
