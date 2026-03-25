# -*- coding: utf-8 -*-

# Klystron Global LLC
# Copyright (C) Klystron Global LLC
# All Rights Reserved
# https://www.klystronglobal.com/


from odoo import models, api, tools


class Menu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    @tools.ormcache('self.env.uid', 'debug')
    def _visible_menu_ids(self, debug=False):
        # جلب القوائم المرئية من الدالة الأصلية في أودو 19
        menus = super(Menu, self)._visible_menu_ids(debug)

        # عدم تطبيق الإخفاء على مدير النظام (Admin) لتجنب قفل الحساب
        if not self.env.is_admin():
            user = self.env.user
            # التحقق من أن الحقل موجود وقيمته ليست فارغة
            if hasattr(user, 'hide_menu_access_ids') and user.hide_menu_access_ids:
                hidden_menus = set(user.hide_menu_access_ids.ids)
                # استخدام عملية الطرح بين المجموعات (Sets) وهي الأسرع في أودو 19
                menus = menus - hidden_menus

        return menus

    # @api.model
    # @tools.ormcache('frozenset(self.env.user.group_ids.ids)', 'debug')
    # def _visible_menu_ids(self, debug=False):
    #     menus = super(Menu, self)._visible_menu_ids(debug)
    #     if self.env.user.hide_menu_access_ids and not self.env.user.has_group('base.group_system'):
    #         for rec in self.env.user.hide_menu_access_ids:
    #             menus.discard(rec.id)
    #         return menus
    #     return menus
