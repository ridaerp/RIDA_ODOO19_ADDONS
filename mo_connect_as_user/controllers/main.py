# -*- coding: utf-8 -*-
import logging

from odoo import http, _
from odoo.exceptions import AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)


class ConnectAsController(http.Controller):

    @http.route('/web/connect_as/<int:uid>', type='http', auth='user', website=False)
    def connect_as_user(self, uid, **kw):
        """Switch the current session to the target user and redirect to /web."""

        # ---- Permission check ----
        if not request.env.user.has_group('mo_connect_as_user.group_connect_as_user'):
            raise AccessError(
                _("You do not have permission to use the 'Connect As' feature.")
            )

        target_user = request.env['res.users'].sudo().browse(uid)
        if not target_user.exists():
            raise AccessError(_("The target user does not exist."))

        if not target_user.active:
            raise AccessError(_("You cannot connect as an inactive user."))

        # ---- Store original user for "Return" feature ----
        # Only store if not already in a "connect as" session
        if not request.session.get('connect_as_original_uid'):
            request.session['connect_as_original_uid'] = request.env.uid
            request.session['connect_as_original_login'] = request.env.user.login
            request.session['connect_as_original_name'] = request.env.user.name

        _logger.info(
            "User %s (id=%s) is connecting as user %s (id=%s)",
            request.session.get('connect_as_original_login', request.env.user.login),
            request.session.get('connect_as_original_uid', request.env.uid),
            target_user.login, target_user.id,
        )

        # ---- Switch session ----
        request.session.uid = target_user.id
        request.session.login = target_user.login
        request.session.session_token = target_user._compute_session_token(
            request.session.sid
        )
        request.session.context = dict(request.env['res.users'].context_get() or {})

        return request.redirect('/web')

    @http.route('/web/connect_as/return', type='http', auth='user', website=False)
    def connect_as_return(self, **kw):
        """Return to the original user session."""

        original_uid = request.session.get('connect_as_original_uid')
        original_login = request.session.get('connect_as_original_login')

        if not original_uid or not original_login:
            return request.redirect('/web')

        original_user = request.env['res.users'].sudo().browse(original_uid)
        if not original_user.exists() or not original_user.active:
            raise AccessError(_("The original user no longer exists or is inactive."))

        _logger.info(
            "User %s (id=%s) is returning to original user %s (id=%s)",
            request.env.user.login, request.env.uid,
            original_login, original_uid,
        )

        # ---- Switch back to original user ----
        request.session.uid = original_user.id
        request.session.login = original_user.login
        request.session.session_token = original_user._compute_session_token(
            request.session.sid
        )
        request.session.context = dict(request.env['res.users'].context_get() or {})

        # ---- Clear the connect-as session data ----
        request.session.pop('connect_as_original_uid', None)
        request.session.pop('connect_as_original_login', None)
        request.session.pop('connect_as_original_name', None)

        return request.redirect('/web')
