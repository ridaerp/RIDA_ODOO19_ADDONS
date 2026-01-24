from odoo import api, fields, models
from datetime import datetime
from odoo.exceptions import UserError


class OreReport(models.TransientModel):
    _name = 'ore.report'
    _description = 'Ore Purchase Wizard Report'

    date_from = fields.Datetime('From', default=fields.Datetime.now)
    date_to = fields.Datetime('To', default=fields.Datetime.now)
    rock_vendor = fields.Many2one("res.partner", "Rock Vendor")
    area_id = fields.Many2one("x_area", "Area")
    min_grade = fields.Float("Min Grade")
    max_grade = fields.Float("Max Grade")


    def print_report(self):
        """تأكد من تمرير البيانات بصيغة تتوافق مع التقرير"""
        report_data = self._get_ore_data()
        # نمرر القاموس بحيث يحتوي على مفتاح form بشكل صريح
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': report_data # هذه البيانات التي سيتم قراءتها في الـ XML
        }
        return self.env.ref('purchase_custom.report_ore_rock_report').report_action(self, data=data)

    def view_print(self):
        """دالة عرض التقرير HTML (مع التحقق من التواريخ)"""
        date_from = fields.Datetime.from_string(self.date_from)
        date_to = fields.Datetime.from_string(self.date_to)

        # التحقق من أن المدة لا تتجاوز شهرين
        if ((date_to.year - date_from.year) * 12 + date_to.month - date_from.month) > 2:
            raise UserError("The difference between the dates cannot exceed 2 months.")

        data = {
            'ids': self.ids,
            'model': self._name,
            'form': self._get_ore_data()
        }
        return self.env.ref('purchase_custom.view_report_ore_rock_report').report_action(self, data=data)

    def _get_ore_data(self):
        """الدالة الكاملة لاستخراج البيانات شاملة الجزء التحليلي الأخير"""
        show_average = self.env.user.has_group('material_request.group_ore_rock_db_geology_user')

        d_from = self.date_from
        d_to = self.date_to

        # [cite_start]حساب أول يوم في الشهر بناءً على تاريخ البداية المختار [cite: 6]
        first_day_of_month = d_from.replace(day=1, hour=0, minute=0, second=0)

        base_domain = [('ore_purchased', '=', True)]
        if self.rock_vendor:
            base_domain += [('partner_id', '=', self.rock_vendor.id)]
        if self.area_id:
            base_domain += [('x_studio_many2one_field_t3bCi', '=', self.area_id.id)]

        # --- 1. حساب إجماليات الشهر (إجمالي سعر وكمية الشهر) ---
        prev_domain = base_domain + [('create_date', '>=', first_day_of_month), ('create_date', '<=', d_to)]
        ore_purchases_prev = self.env['purchase.order'].search(prev_domain)

        total_previous_qty_purchase = 0
        total_previous_price_purchase = 0
        for line in ore_purchases_prev.mapped('order_line').filtered(lambda l: l.product_id.id == 63325):
            total_previous_qty_purchase += line.product_qty
            if line.price_unit > 0:
                total_previous_price_purchase += line.price_subtotal

        # --- 2. البيانات التفصيلية للفترة المختارة ---
        report_domain = base_domain + [('create_date', '>=', d_from), ('create_date', '<=', d_to)]
        ore_purchases = self.env['purchase.order'].search(report_domain, order='create_date asc')

        list_ore_purchases = []
        number_of_line = 0
        total_of_quantity = 0
        total_of_gold = 0
        total_of_price = 0

        # متغيرات الجزء الأخير (تحليل المشتريات)
        total_of_quantity_purchase = 0
        total_of_quantity_no_purchase = 0
        total_of_quantity_purchase_gold = 0
        total_of_quantity_no_purchase_gold = 0

        for rec in ore_purchases:
            # [cite_start]سعر النقل أو تحمل العميل [cite: 4]
            transport_line = rec.order_line.filtered(lambda l: l.product_id.id == 62437)[:1]
            transport_price = abs(transport_line.price_subtotal) if transport_line else 0

            for line in rec.order_line.filtered(lambda l: l.product_id.id == 63325):
                avg_grade = round(rec.weight_request_id.average, 2)

                if self.max_grade > 0:
                    if not (self.min_grade <= avg_grade <= self.max_grade):
                        continue

                number_of_line += 1
                # [cite_start]الذهب المتوقع = التركيز × الوزن [cite: 4]
                row_gold = avg_grade * line.product_qty

                # [cite_start]تجميع البيانات للجدول الرئيسي [cite: 4]
                list_ore_purchases.append([
                    number_of_line,
                    line.partner_id.name,
                    rec.x_studio_many2one_field_t3bCi.x_name,
                    rec.weight_request_id.date_request.strftime(
                        '%Y-%m-%d %H:%M') if rec.weight_request_id.date_request else False,
                    line.product_qty,
                    avg_grade,
                    "{:,}".format(abs(line.price_unit)),
                    "{:,}".format(transport_price),
                    "{:,}".format(line.price_subtotal),
                    round(row_gold, 2)
                ])

                # تقسيم الكميات والذهب للجزء التحليلي الأخير
                if line.price_unit > 0:
                    total_of_quantity_purchase += line.product_qty
                    total_of_quantity_purchase_gold += row_gold
                else:
                    total_of_quantity_no_purchase += line.product_qty
                    total_of_quantity_no_purchase_gold += row_gold

                total_of_quantity += line.product_qty
                total_of_gold += row_gold
                total_of_price += line.price_subtotal

        # حساب المتوسطات
        average_focus = round(total_of_gold / total_of_quantity, 2) if total_of_quantity > 0 else 0

        # [cite_start]تجهيز جدول الإجماليات [cite: 5, 7]
        list_totals_ore_purchase = [[
            number_of_line,
            round(total_of_quantity, 2),
            average_focus,
            "{:,}".format(round(total_of_price, 2)),
            round(total_previous_qty_purchase, 2),
            "{:,}".format(round(total_previous_price_purchase, 2))
        ]]

        # --- 3. تجهيز بيانات تحليل المشتريات (الجزء الأخير) ---
        analysis_qty = [round(total_of_quantity_purchase, 2), round(total_of_quantity_no_purchase, 2)]
        analysis_gold = [
            round(total_of_quantity_purchase_gold / total_of_quantity_purchase,
                  2) if total_of_quantity_purchase > 0 else 0,
            round(total_of_quantity_no_purchase_gold / total_of_quantity_no_purchase,
                  2) if total_of_quantity_no_purchase > 0 else 0
        ]

        return {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'list_ore_purchases': list_ore_purchases,
            'list_totals_ore_purchase': list_totals_ore_purchase,
            'list_of_purchase_analysis': [analysis_qty, analysis_gold],
            'rock_vendor': self.rock_vendor.name if self.rock_vendor else "All Vendors",
            'area_id': self.area_id.x_name if self.area_id else "All Areas",
            'show_average': show_average,
        }