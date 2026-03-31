from odoo import api, fields, models
from datetime import datetime
from odoo.exceptions import UserError
import io
import base64
import xlsxwriter


class OreReport(models.TransientModel):
    _name = 'ore.report'
    _description = 'Ore Purchase Wizard Report'

    date_from = fields.Datetime('From', default=fields.Datetime.now)
    date_to = fields.Datetime('To', default=fields.Datetime.now)
    rock_vendor = fields.Many2one("res.partner", "Rock Vendor")
    area_id = fields.Many2one("x_area", "Area")
    min_grade = fields.Float("Min Grade")
    max_grade = fields.Float("Max Grade")

    def print_xlsx(self):
        data = self._get_ore_data()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Rock Purchases')

        # --- 1. التنسيقات (Styles) ---
        sheet.right_to_left()

        title_style = workbook.add_format({
            'bold': True, 'size': 14, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#1F4E78', 'font_color': 'white', 'border': 1
        })

        header_style = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#D9D9D9', 'border': 1, 'text_wrap': True
        })

        cell_style = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        float_style = workbook.add_format({'border': 1, 'align': 'center', 'num_format': '#,##0.00'})
        bold_cell = workbook.add_format({'border': 1, 'bold': True, 'align': 'center', 'bg_color': '#F9F9F9'})

        # ضبط عرض الأعمدة
        sheet.set_column('A:A', 6)  # العدد
        sheet.set_column('B:B', 25)  # العميل
        sheet.set_column('C:E', 15)  # المنطقة، الولاية، اللوت
        sheet.set_column('F:F', 18)  # التاريخ
        sheet.set_column('G:M', 12)  # الأوزان والأسعار

        # --- 2. بناء الهيدر الرئيسي (الجدول التفصيلي) ---
        headers = ['العدد', 'أسم العميل', 'منطقة الخام', 'الولاية', 'رقم اللوت (Lot)', 'تاريخ الأستلام', 'وزن (طن)',
                   'التركيز']

        if data.get('show_average'):
            headers.append('سعر الطن')

        headers.extend(['تحمل العميل', 'سعر الشراء', 'الذهب المتوقع'])

        sheet.merge_range('A1:L2', 'تقرير مشتريات الخام التفصيلي', title_style)

        # معلومات الفلتر
        sheet.write('A4', 'المورد:', header_style)
        sheet.write('B4', data.get('rock_vendor'), cell_style)
        sheet.write('A5', 'المنطقة:', header_style)
        sheet.write('B5', data.get('area_id'), cell_style)

        # كتابة رؤوس الجدول
        for col, title in enumerate(headers):
            sheet.write(6, col, title, header_style)

        row = 7
        for line in data['list_ore_purchases']:
            sheet.write(row, 0, line[0], cell_style)  # العدد
            sheet.write(row, 1, line[1], cell_style)  # العميل
            sheet.write(row, 2, line[2], cell_style)  # المنطقة
            sheet.write(row, 3, line[3], cell_style)  # الولاية
            sheet.write(row, 4, line[4], cell_style)  # رقم اللوت
            sheet.write(row, 5, line[5], cell_style)  # التاريخ
            sheet.write(row, 6, line[6], float_style)  # وزن
            sheet.write(row, 7, line[7], float_style)  # تركيز

            col_idx = 8
            if data.get('show_average'):
                sheet.write(row, col_idx, line[8], cell_style)  # سعر الطن
                col_idx += 1

            sheet.write(row, col_idx, line[9], cell_style)  # تحمل العميل
            sheet.write(row, col_idx + 1, line[10], cell_style)  # سعر الشراء
            sheet.write(row, col_idx + 2, line[11], float_style)  # الذهب المتوقع
            row += 1

        # --- 3. جداول الإجماليات والولايات (أسفل الجدول الرئيسي) ---
        row += 2
        # جدول تفصيل الولايات (كما في الـ PDF)
        sheet.merge_range(row, 0, row, 2, 'إحصائيات الولايات', title_style)
        row += 1
        sheet.write(row, 0, 'الولاية', header_style)
        sheet.write(row, 1, 'إجمالي الوزن', header_style)
        sheet.write(row, 2, 'متوسط التركيز', header_style)

        row += 1
        for state in data.get('state_details', []):
            sheet.write(row, 0, state['name'], cell_style)
            sheet.write(row, 1, state['weight'], float_style)
            sheet.write(row, 2, state['average'], float_style)
            row += 1

        # جدول CIC / CIL
        row += 1
        sheet.merge_range(row, 0, row, 2, 'إحصائيات النوع (CIC/CIL)', title_style)
        row += 1
        sheet.write(row, 0, 'النوع', header_style)
        sheet.write(row, 1, 'الوزن', header_style)
        sheet.write(row, 2, 'المتوسط', header_style)

        row += 1
        sheet.write(row, 0, 'CIL', cell_style);
        sheet.write(row, 1, data.get('cil_weight'), float_style);
        sheet.write(row, 2, data.get('cil_avg'), float_style)
        row += 1
        sheet.write(row, 0, 'CIC', cell_style);
        sheet.write(row, 1, data.get('cic_weight'), float_style);
        sheet.write(row, 2, data.get('cic_avg'), float_style)

        # جدول الإجماليات النهائية
        row += 2
        sheet.merge_range(row, 0, row, 4, 'الإجماليات العامة', title_style)
        row += 1
        t_headers = ['عدد العمليات', 'إجمالي الوزن الكلي', 'المتوسط العام', 'إجمالي السعر']
        for col, title in enumerate(t_headers):
            sheet.write(row, col, title, header_style)

        row += 1
        totals = data['list_totals_ore_purchase'][0]
        sheet.write(row, 0, totals[0], bold_cell)  # عدد العمليات
        sheet.write(row, 1, totals[1], float_style)  # الوزن
        sheet.write(row, 2, totals[2], float_style)  # التركيز
        sheet.write(row, 3, totals[3], bold_cell)  # السعر

        workbook.close()
        output.seek(0)

        # إنشاء المرفق
        file_name = 'Detailed_Ore_Purchase_%s.xlsx' % datetime.now().strftime('%Y%m%d')
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }


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
        """
        الدالة الكاملة لاستخراج البيانات مع متوسط التركيز لكل ولاية و CIC/CIL
        بناءً على الهيكل المطلوب للـ Return.
        """
        # التحقق من صلاحية رؤية التركيز
        show_average = self.env.user.has_group('material_request.group_ore_rock_db_geology_user')

        d_from = self.date_from
        d_to = self.date_to
        first_day_of_month = d_from.replace(day=1, hour=0, minute=0, second=0)

        # بناء الدومين
        base_domain = [('ore_purchased', '=', True)]
        if self.rock_vendor:
            base_domain += [('partner_id', '=', self.rock_vendor.id)]
        if self.area_id:
            base_domain += [('x_studio_many2one_field_t3bCi', '=', self.area_id.id)]

        # 1. إحصائيات الشهر التراكمية
        prev_domain = base_domain + [('create_date', '>=', first_day_of_month), ('create_date', '<=', d_to)]
        ore_purchases_prev = self.env['purchase.order'].search(prev_domain)
        total_previous_qty_purchase = 0
        total_previous_price_purchase = 0
        for po in ore_purchases_prev:
            for line in po.order_line.filtered(lambda l: l.product_id.id == 63325):
                total_previous_qty_purchase += line.product_qty
                if line.price_unit > 0:
                    total_previous_price_purchase += line.price_subtotal

        # 2. معالجة البيانات التفصيلية للفترة
        report_domain = base_domain + [('create_date', '>=', d_from), ('create_date', '<=', d_to)]
        ore_purchases = self.env['purchase.order'].search(report_domain, order='create_date asc')

        list_ore_purchases = []
        # قواميس لتخزين الوزن والذهب الإجمالي لحساب المتوسطات
        state_stats = {}  # { 'اسم الولاية': {'weight': 0.0, 'gold': 0.0} }
        cil_weight, cil_gold = 0.0, 0.0
        cic_weight, cic_gold = 0.0, 0.0
        other_lot_weight = 0.0

        number_of_line = 0
        total_of_quantity = 0
        total_of_gold = 0
        total_of_price = 0
        total_of_quantity_purchase = 0
        total_of_quantity_no_purchase = 0
        total_of_quantity_purchase_gold = 0
        total_of_quantity_no_purchase_gold = 0

        for rec in ore_purchases:
            lot_name = rec.weight_request_id.lot_id.name or ""
            state_obj = rec.x_studio_many2one_field_t3bCi.x_studio_state
            state_name = state_obj.name if state_obj else "غير محدد"

            for line in rec.order_line.filtered(lambda l: l.product_id.id == 63325):
                current_qty = line.product_qty
                avg_grade = rec.weight_request_id.average if rec.weight_request_id else 0.0

                if self.max_grade > 0 and not (self.min_grade <= avg_grade <= self.max_grade):
                    continue

                number_of_line += 1
                row_gold = avg_grade * current_qty  # كمية الذهب المطلقة في هذه الحمولة

                # تحديث إحصائيات الولايات
                if state_name not in state_stats:
                    state_stats[state_name] = {'weight': 0.0, 'gold': 0.0}
                state_stats[state_name]['weight'] += current_qty
                state_stats[state_name]['gold'] += row_gold

                # تحديث إحصائيات CIC/CIL
                if lot_name.upper().startswith('D'):
                    cil_weight += current_qty
                    cil_gold += row_gold
                elif lot_name.upper().startswith('H'):
                    cic_weight += current_qty
                    cic_gold += row_gold
                else:
                    other_lot_weight += current_qty

                # بيانات الشراء والتحليل
                total_of_quantity += current_qty
                total_of_gold += row_gold
                total_of_price += line.price_subtotal

                if line.price_unit > 0:
                    total_of_quantity_purchase += current_qty
                    total_of_quantity_purchase_gold += row_gold
                else:
                    total_of_quantity_no_purchase += current_qty
                    total_of_quantity_no_purchase_gold += row_gold

                # إضافة البيانات للقائمة التفصيلية
                list_ore_purchases.append([
                    number_of_line, line.partner_id.name, rec.x_studio_many2one_field_t3bCi.x_name,
                    state_name, lot_name,
                    rec.weight_request_id.date_request.strftime(
                        '%Y-%m-%d %H:%M') if rec.weight_request_id.date_request else False,
                    current_qty, round(avg_grade, 2), "{:,}".format(abs(line.price_unit)),
                    "0", "{:,}".format(line.price_subtotal), round(row_gold, 2)
                ])

        # تحويل بيانات الولايات مع حساب المتوسط لكل ولاية
        state_details = []
        for name, stats in state_stats.items():
            state_details.append({
                'name': name,
                'weight': round(stats['weight'], 2),
                'average': round(stats['gold'] / stats['weight'], 2) if stats['weight'] > 0 else 0
            })

        # حساب المتوسطات النهائية لـ CIC/CIL
        cil_average = round(cil_gold / cil_weight, 2) if cil_weight > 0 else 0
        cic_average = round(cic_gold / cic_weight, 2) if cic_weight > 0 else 0
        average_focus = round(total_of_gold / total_of_quantity, 2) if total_of_quantity > 0 else 0

        # تحليل المشتريات
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
            'list_totals_ore_purchase': [[
                number_of_line,
                round(total_of_quantity, 2),
                average_focus,
                "{:,}".format(round(total_of_price, 2)),
                round(total_previous_qty_purchase, 2),
                "{:,}".format(round(total_previous_price_purchase, 2))
            ]],
            'list_of_purchase_analysis': [analysis_qty, analysis_gold],
            'rock_vendor': self.rock_vendor.name if self.rock_vendor else "All Vendors",
            'area_id': self.area_id.x_name if self.area_id else "All Areas",
            'show_average': show_average,
            'state_details': state_details,
            'cil_weight': round(cil_weight, 2),
            'cil_avg': cil_average,  # متغير جديد للمتوسط
            'cic_weight': round(cic_weight, 2),
            'cic_avg': cic_average,  # متغير جديد للمتوسط
            'other_lot_weight': round(other_lot_weight, 2),
            'number_of_line_total': number_of_line,
        }