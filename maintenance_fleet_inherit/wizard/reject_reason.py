import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class reject_wizard(models.TransientModel):
    _name = 'rejection.wizard'
    _description = 'Rejection Reason'

    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")

    def action_validate(self):
        self.ensure_one()
        context = dict(self._context or {})
        active_model = self.env.context.get('active_model')
        active_id = self.env.context['active_ids']

        order = self.env[active_model].browse(active_id)

        if self.reason_reject:
            order.state = 'reject'
            order.reason_reject = self.reason_reject
            message = """
            This document was rejected by: %s <br/>
            <b>Rejection Reason:</b> %s 
            """ % (self.env.user.name, self.reason_reject)
            order.message_post(body=message)

        return {'type': 'ir.actions.act_window_close'}

