# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
import pytz
from io import BytesIO
import base64
import xlsxwriter
from odoo.exceptions import UserError
from collections import defaultdict


class DailyAvailabilityReportWizard(models.TransientModel):
    _name = 'daily.availability.report.wizard'
    _description = 'Daily Availability Report Wizard'

    report_day = fields.Date(string='Report Day', required=True)
    report_file = fields.Binary('Report File', attachment=False)
    report_filename = fields.Char('Report Filename', size=64)

    # ==================================================
    # 🛠️ دوال مساعدة لحساب الوقت (مضافة من التقرير السابق)
    # ==================================================
    def _hours_to_datetime(self, date_obj, hours_float, user_tz):
        """تحويل الساعات العائمة إلى كائن datetime مع المنطقة الزمنية، مع احتساب عبور اليوم."""
        hour = int(hours_float)
        minute = int((hours_float % 1) * 60)

        target_dt = datetime.combine(date_obj, time(hour % 24, minute))

        if hours_float >= 24:
            target_dt += timedelta(days=int(hours_float // 24))

        return user_tz.localize(target_dt)

    def _get_shift_boundaries(self, report_day, shift_type, start_day, end_day, start_night, end_night, user_tz):
        """تحديد أوقات بداية ونهاية الوردية بناءً على نوع الوردية المختار للمعدة."""

        # قم بتعيين قيم افتراضية تغطي اليوم بأكمله كخيار احتياطي
        start_dt = self._hours_to_datetime(report_day, 0.0, user_tz)
        end_dt = self._hours_to_datetime(report_day + timedelta(days=1), 0.0, user_tz)

        if shift_type in ['d_s', 'd_n_s']:
            if start_day is not None and end_day is not None:
                start_dt = self._hours_to_datetime(report_day, start_day, user_tz)
                end_dt = self._hours_to_datetime(report_day, end_day, user_tz)
                if end_day <= start_day:
                    end_dt += timedelta(days=1)

            if shift_type == 'd_n_s':
                if start_night is not None and end_night is not None:
                    night_start_dt = self._hours_to_datetime(report_day, start_night, user_tz)
                    night_end_dt = self._hours_to_datetime(report_day, end_night, user_tz)
                    if end_night <= start_night:
                        night_end_dt += timedelta(days=1)

                    # تحديد الحدود القصوى للفترة
                    end_dt = max(end_dt, night_end_dt)
                    start_dt = min(start_dt, night_start_dt)

        elif shift_type == 'n_s':
            if start_night is not None and end_night is not None:
                start_dt = self._hours_to_datetime(report_day, start_night, user_tz)
                end_dt = self._hours_to_datetime(report_day, end_night, user_tz)
                if end_night <= start_night:
                    end_dt += timedelta(days=1)

        return {
            'start_dt': start_dt,
            'end_dt': end_dt,
        }

    def _float_to_time_str(self, hours_float):
        """Convert float hours (e.g., 5.5) to 'HH:MM' format."""
        try:
            hours_float = float(hours_float or 0.0)
        except Exception:
            hours_float = 0.0
        if hours_float <= 0:
            return "00:00"

        total_minutes = int(round(hours_float * 60))
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    def generate_machines_availability_report(self):
        self.ensure_one()

        if not self.report_day:
            raise UserError("Please select a report day.")

        report_day = self.report_day
        team_id = 2
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')

        # 1. جلب سجل العمليات اليومية وساعات الوردية
        fleet_op = self.env['fleet.operation'].search([('date', '=', report_day)], limit=1)
        if not fleet_op:
            raise UserError(
                _("No Fleet Daily Operation record found for the selected date. Please ensure shift hours are entered."))

        start_day_float = fleet_op.start_day or 0.0
        end_day_float = fleet_op.end_day or 0.0
        start_night_float = fleet_op.start_night or 0.0
        end_night_float = fleet_op.end_night or 0.0

        # حدود التقرير الرئيسية (اليوم بأكمله)
        report_start_dt = self._hours_to_datetime(report_day, 0.0, user_tz)
        report_end_dt = self._hours_to_datetime(report_day + timedelta(days=1), 0.0, user_tz)

        equipments = self.env['maintenance.equipment'].search([
            ('maintenance_team_id', '=', team_id),
            ('custom_sequence', '>', 0)
        ], order='custom_sequence asc')

        if not equipments:
            raise UserError("No equipment found for this team.")

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Daily Fleet Operation Report')

        # تنسيقات (كما هي)
        title_format = workbook.add_format({
            'bold': True, 'font_size': 16, 'font_color': '#0070C0',
            'align': 'center', 'valign': 'vcenter'
        })
        subtitle_format = workbook.add_format({
            'bold': True, 'font_size': 12,
            'align': 'center', 'valign': 'vcenter'
        })
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#D9D9D9', 'border': 1,
            'align': 'center', 'valign': 'vcenter'
        })
        data_format = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'text_wrap': True
        })
        yellow_format = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#FFF2CC', 'text_wrap': True
        })
        red_bg = workbook.add_format({'bg_color': '#FFC7CE', 'border': 1, 'align': 'center', 'valign': 'vcenter',
                                      'text_wrap': True})  # احمر فاتح
        blue_bg = workbook.add_format({'bg_color': '#C6E0FF', 'border': 1, 'align': 'center', 'valign': 'vcenter',
                                       'text_wrap': True})  # ازرق فاتح

        headers = [
            'No.', 'Code', 'Machine Type', 'Equipment Type',
            'Day Type', 'Operation Type',
            'Work Location',
            'Target Hrs', 'Start', 'End',
            'Actual Hrs', 'Downtime Hrs', 'Standby Hrs',
            'Available Hrs', 'Availability %', 'Utilization %', 'Fuel Cons. (L)', 'Fuel/L-H',
            'Standard Fuel L/H'
        ]

        # العنوان الرئيسي
        worksheet.set_row(0, 30)
        worksheet.merge_range(0, 0, 0, len(headers) - 1,
                              'Daily Fleet Operation Report', title_format)

        # عنوان التاريخ (تم تحديثه ليعكس حدود التقرير)
        date_range_str = f"Date: {report_day.strftime('%d-%b-%Y')} (Report Period: {report_start_dt.strftime('%H:%M')} to {report_end_dt.strftime('%H:%M')})"
        worksheet.merge_range(1, 0, 1, len(headers) - 1, date_range_str, subtitle_format)

        # الهيدر
        header_row = 2
        for col, header in enumerate(headers):
            worksheet.write(header_row, col, header, header_format)

        row = header_row + 1
        seq = 1

        for eq in equipments:
            odometer_lines = self.env['fleet.vehicle.odometer.line'].search([
                ('equipment_id', '=', eq.id),
                ('operation_id.date', '=', self.report_day)
            ])

            od_line = odometer_lines[:1]
            standard_fuel = eq.stander_fuel or 0.0
            equipment_type = eq.type_of_equipment or ''

            # 2. جلب نوع الوردية للمعدة وتحديد حدود الوردية
            shift_type_for_equipment = od_line.day_type if od_line else 'd_s'

            shift_info = self._get_shift_boundaries(
                report_day, shift_type_for_equipment,
                start_day_float, end_day_float,
                start_night_float, end_night_float, user_tz
            )

            shift_start_dt = shift_info['start_dt']
            shift_end_dt = shift_info['end_dt']

            # 3. حساب زمن التوقف (Downtime) حسب الوردية المحددة (نفس منطق التقرير السابق)
            downtime_hrs = 0.0
            requests = self.env['maintenance.request'].search([
                ('equipment_id', '=', eq.id),
                ('stage_id.name', 'not in', ['Cancelled', 'Rejected']),
                # نجلب البلاغات التي تنتهي بعد بداية الوردية أو لم تنته بعد
                ('request_date_time', '<', shift_end_dt.astimezone(pytz.utc).replace(tzinfo=None)),
                '|',
                ('complete_datetime', '>=', shift_start_dt.astimezone(pytz.utc).replace(tzinfo=None)),
                ('complete_datetime', '=', False),
            ], order='request_date_time asc')

            for req in requests:
                if not req.request_date_time:
                    continue

                request_dt_local = req.request_date_time.astimezone(user_tz)

                # نهاية زمن التوقف الفعلي (إما الإغلاق أو نهاية الوردية)
                if req.stage_id.name in ['Closed', 'Completed'] and req.complete_datetime:
                    complete_dt_local = req.complete_datetime.astimezone(user_tz)
                    end_of_actual_downtime = complete_dt_local
                else:
                    end_of_actual_downtime = shift_end_dt

                # تقاطع الفترة الزمنية للبلاغ مع فترة الوردية المحددة
                calc_start_dt = max(request_dt_local, shift_start_dt)
                calc_end_dt = min(end_of_actual_downtime, shift_end_dt)

                if calc_end_dt > calc_start_dt:
                    delta = calc_end_dt - calc_start_dt
                    downtime_hrs += delta.total_seconds() / 3600.0

            # 4. باقي الحسابات تعتمد على البيانات المتوفرة في سطر العملية اليومية (od_line)

            target_hrs = od_line.day_duration if od_line else 11.0

            # القيم المتاحة في سطر العملية
            start_val = od_line.start_value if od_line else 0.0
            end_val = od_line.end_value if od_line else 0.0
            actual_hrs = od_line.distance if od_line else 0.0  # محسوبة: end_value - start_value

            # 5. حسابات الأداء
            standby_hrs = target_hrs - actual_hrs + downtime_hrs
            available_hrs = actual_hrs + standby_hrs

            # Fuel Consumption (يفضل جلبها من تقرير الـ odometer.line إذا كانت محسوبة هناك)
            fuel_line = self.env['issuance.request.line'].search([
                ('product_id.default_code', '=', 'GM-GAS-00-0000'),
                ('equipment_id', '=', eq.id),
                ('x_studio_request_date', '>=', shift_start_dt),
                ('x_studio_request_date', '<=', shift_end_dt),
            ], order='x_studio_request_date desc', limit=1)

            fuel_consumption = fuel_line.qty_issued if fuel_line else 0.0
            fuel_per_hr = round(fuel_consumption / actual_hrs if actual_hrs else 0.0, 2)

            total_time_for_availability = actual_hrs + downtime_hrs + standby_hrs
            availability = round(
                (available_hrs / total_time_for_availability) if total_time_for_availability > 0 else 0.0, 2
            )

            utilization = round(
                (actual_hrs / (actual_hrs + standby_hrs)) if (actual_hrs + standby_hrs) > 0 else 0.0, 2
            )

            supposed_fuel = actual_hrs * standard_fuel

            downtime_str = self._float_to_time_str(downtime_hrs)
            standby_str = self._float_to_time_str(standby_hrs)
            available_str = self._float_to_time_str(available_hrs)

            # 6. تجهيز البيانات للتقرير
            day_type = od_line._fields['day_type'].convert_to_export(od_line.day_type, od_line) if od_line else ''
            operation_type = od_line._fields['operation_type'].convert_to_export(od_line.operation_type,
                                                                                 od_line) if od_line else ''
            location = od_line.location_id.name if od_line and od_line.location_id else ''

            row_data = [
                seq,
                eq.code or '',
                eq.display_name or '',
                equipment_type,
                day_type,
                operation_type,
                location,
                target_hrs,
                start_val,
                end_val,
                actual_hrs,
                downtime_str,
                standby_str,
                available_str,
                availability,  # تم تحويلها إلى نسبة مئوية مباشرة
                utilization,  # تم تحويلها إلى نسبة مئوية مباشرة
                fuel_consumption,
                fuel_per_hr,
                supposed_fuel,
            ]

            # تحديد لون الصف
            row_format = data_format
            day_type_value = od_line.day_type if od_line else None
            operation_type_value = od_line.operation_type if od_line else None

            if operation_type_value == 'non_operation':
                row_format = red_bg
            elif day_type_value == 'd_n_s':
                row_format = blue_bg

            # كتابة الصف
            for col, value in enumerate(row_data):
                # تنسيقات الأرقام
                fmt = row_format
                if col in [6, 7, 8, 9, 15, 16, 17]:  # Target, Start, End, Actual, Fuel Cons, Fuel/hr, Supposed Fuel
                    fmt = workbook.add_format(
                        {'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '0.00'})
                elif col in [13, 14]:  # Availability %, Utilization %
                    fmt = workbook.add_format(
                        {'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '0.00%'})
                elif col in [10, 11, 12]:  # Downtime, Standby, Available (HH:MM)
                    fmt = row_format  # نستخدم التنسيق العادي لأننا نمررها كسلسلة نصية 'HH:MM'

                worksheet.write(row, col, value, fmt)

            row += 1
            seq += 1

        # توسيع الأعمدة
        for col in range(len(headers)):
            worksheet.set_column(col, col, 15)

        workbook.close()
        output.seek(0)
        self.report_file = base64.b64encode(output.read())
        output.close()

        filename = f"{self.report_day.strftime('%d')}-Daily Fleet Operation Report-{self.report_day.strftime('%d-%m-%Y')}.xlsx"
        self.report_filename = filename

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=report_file&download=true&filename={filename}',
            'target': 'self',
        }