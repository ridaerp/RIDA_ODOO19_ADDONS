# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super().session_info()
        if request and hasattr(request, 'session'):
            original_uid = request.session.get('connect_as_original_uid')
            if original_uid:
                res['connect_as_original_uid'] = original_uid
                res['connect_as_original_name'] = request.session.get(
                    'connect_as_original_name', ''
                )
        return res
