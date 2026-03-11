# -*- coding: utf-8 -*-

# Klystron Global LLC
# Copyright (C) Klystron Global LLC
# All Rights Reserved
# https://www.klystronglobal.com/


from odoo import models, api, tools

class Menu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    @tools.ormcache(
        'frozenset(self.env.user.group_ids.ids)',
        'frozenset(self.env.user.hide_menu_access_ids.ids)',
        'debug'
    )
    def _visible_menu_ids(self, debug=False):
        menus = super()._visible_menu_ids(debug)

        if not self.env.user.has_group('base.group_system'):
            hidden_menus = self.env.user.hide_menu_access_ids.ids
            for menu_id in hidden_menus:
                menus.discard(menu_id)

        return menus