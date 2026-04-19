# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import AccessError


class ResUsers(models.Model):
    _inherit = 'res.users'

    def action_connect_as(self):
        """Open the system as the selected user without requiring a password."""
        self.ensure_one()

        # Security check
        if not self.env.user.has_group('mo_connect_as_user.group_connect_as_user'):
            raise AccessError(
                _("You do not have permission to use the 'Connect As' feature.")
            )

        # Prevent connecting as yourself
        if self.id == self.env.uid:
            raise AccessError(
                _("You are already logged in as this user.")
            )

        # Prevent connecting as an inactive user
        if not self.active:
            raise AccessError(
                _("You cannot connect as an inactive user.")
            )

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/connect_as/%d' % self.id,
            'target': 'self',
        }
