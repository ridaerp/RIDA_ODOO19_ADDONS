# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2021-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        # 1. تنفيذ الكود الأصلي لـ Odoo لترحيل المخزون أولاً
        res = super(StockPicking, self).button_validate()

        # 2. الكود الخاص بنا لإنشاء الفاتورة بعد الترحيل
        for picking in self:
            # التحقق: هل العملية استلام وارد؟ وهل هي مرتبطة بأمر شراء؟
            if picking.picking_type_code == 'incoming' and picking.purchase_id:
                purchase = picking.purchase_id

                # التحقق من شرط المستخدم الخاص بكم (rohax)
                # نستخدم sudo() لقراءة بيانات المستخدمين إذا لم تكن هناك صلاحية
                requesting_user = purchase.requested_by.sudo()
                if requesting_user.user_type and requesting_user.user_type == 'rohax':
                    continue  # تخطي إذا كان المستخدم rohax

                # التحقق الجوهري: هل توجد كميات تحتاج للفوترة؟
                # هذا السطر هو الذي يمنع إنشاء الفاتورة عند الإرجاع (Return)
                # لأن عند الإرجاع لن تكون هناك كميات موجبة متبقية للفوترة
                if any(line.qty_to_invoice > 0 for line in purchase.order_line):
                    try:
                        # استخدام مستخدم النظام (رقم 1) لتجاوز مشاكل الصلاحيات عند إنشاء الفاتورة
                        # كما كان في كودك الأصلي
                        purchase_sudo = purchase.with_user(1)

                        # التأكد من حالة الفوترة لتجنب الأخطاء
                        if purchase_sudo.invoice_status == 'to invoice':
                            purchase_sudo.action_create_invoice()

                    except Exception as e:
                        # يفضل طباعة الخطأ في السجلات (Logs)
                        # _logger.error("Failed to create invoice automatically: %s", e)
                        pass

        return res


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    delivery_status = fields.Selection(selection=[
        ('nothing', 'Nothing to Receive'), ('to_receive', 'To Receive'),
        ('partial', 'Partially Received'), ('received', 'Received'),
        ('processing', 'Processing')
    ], string='Delivery Status', compute='_compute_delivery_status', store=True,
        readonly=True, copy=False, default='nothing')

    @api.depends('state', 'order_line.qty_received')
    def _compute_delivery_status(self):
        for rec in self:
            pickings = self.env['stock.picking'].search([
                ('purchase_id', '=', rec.id)])
            orderlines = rec.mapped('order_line')

            # مجرد منطق حسابي لتحديد الكلمة التي ستظهر
            if not pickings and not orderlines.filtered(lambda x: x.product_id.type == 'service'):
                rec.delivery_status = 'nothing'
            elif all(o.qty_received == 0 for o in orderlines):
                rec.delivery_status = 'to_receive'
            elif orderlines.filtered(lambda x: x.qty_received < x.product_qty):
                rec.delivery_status = 'partial'
            elif all(o.qty_received == o.product_qty for o in orderlines):
                rec.delivery_status = 'received'
            elif any(p.state in ('waiting', 'confirmed') for p in pickings):
                rec.delivery_status = 'processing'
            else:
                rec.delivery_status = 'nothing'
