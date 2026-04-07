# -*- coding: utf-8 -*-

# Klystron Global LLC
# Copyright (C) Klystron Global LLC
# All Rights Reserved
# https://www.klystronglobal.com/


from odoo import fields, models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    hide_menu_access_ids = fields.Many2many('ir.ui.menu', 'ir_ui_hide_menu_rel', 'uid', 'menu_id',
                                            string='Hide Access Menu')

    @api.model_create_multi
    def create(self, vals_list):
        res = super(ResUsers, self).create(vals_list)
        # تنظيف الكاش عند إنشاء مستخدم جديد
        self.clear_caches()
        return res

    def write(self, vals):
        res = super(ResUsers, self).write(vals)
        # تنظيف الكاش عند تعديل صلاحيات الإخفاء
        self.clear_caches()
        return res

    # def write(self, vals):
    #     res = super(ResUsers, self).write(vals)
    #     self.clear_caches()
    #     return res
