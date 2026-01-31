from odoo import models, fields, api, _
from odoo.exceptions import UserError

class Justification(models.TransientModel):
    _name = 'justification.justification'
    justification = fields.Text(string='Justification', required=True)
    

    def button_confirm(self):
        for rec in self:
            active_id = self._context.get('active_id')
            self.env['hr.leave'].search([('id','=',active_id)]).justification = self.justification
            # active_id = self._context.get('active_id')
            holiday = self.env['hr.leave'].search([('id','=',active_id)])
            current_employee = self.env.user.employee_id
            if any(leave.state not in ['confirm', 'validate', 'validate1'] for leave in holiday):
                raise UserError(_('Allocation request must be confirmed or validated in order to refuse it.'))

            validated_holidays = holiday.filtered(lambda hol: hol.state == 'validate1')
            validated_holidays.write({'state': 'refuse', 'first_approver_id': current_employee.id})
            (holiday - validated_holidays).write({'state': 'refuse', 'second_approver_id': current_employee.id})
            # If a category that created several holidays, cancel all related
            # linked_requests = holiday.mapped('holiday_status_id')
            # if linked_requests:
            #     linked_requests.action_refuse()
            # holiday.activity_update()

            linked_requests = holiday.mapped('linked_request_ids')
            linked_requests = linked_requests.filtered(lambda rec: isinstance(rec, self.env['hr.leave']))
            linked_requests.action_refuse()
            holiday.activity_update()

