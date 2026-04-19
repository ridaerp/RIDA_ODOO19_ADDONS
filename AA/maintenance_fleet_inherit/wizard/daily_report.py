# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
import pytz
from io import BytesIO
import base64
import xlsxwriter
from odoo.exceptions import UserError
from collections import defaultdict


class DailyReportWizard(models.TransientModel):
    _name = 'daily.report.wizard'
    _description = 'Daily Report Wizard'

    report_day = fields.Date(string='Report Day', required=True)
    show_24h_equipment = fields.Boolean(
        string='Show 24 Hours Equipment',
        default=True,
        help='Include equipment that works in two shifts (24 hours)'
    )
    report_file = fields.Binary('Report File', attachment=False)
    report_filename = fields.Char('Report Filename', size=64)

    # ==================================================
    # 🛠️ دوال مساعدة لحساب الوقت
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

        # تحديد الحدود الزمنية بناءً على نوع الوردية
        if shift_type in ['d_s', 'd_n_s']:
            start_dt = self._hours_to_datetime(report_day, start_day, user_tz)
            end_dt = self._hours_to_datetime(report_day, end_day, user_tz)
            if end_day <= start_day:
                end_dt += timedelta(days=1)

            if shift_type == 'd_n_s':
                night_start_dt = self._hours_to_datetime(report_day, start_night, user_tz)
                night_end_dt = self._hours_to_datetime(report_day, end_night, user_tz)
                if end_night <= start_night:
                    night_end_dt += timedelta(days=1)

                end_dt = max(end_dt, night_end_dt)
                start_dt = min(start_dt, night_start_dt)

        elif shift_type == 'n_s':
            start_dt = self._hours_to_datetime(report_day, start_night, user_tz)
            end_dt = self._hours_to_datetime(report_day, end_night, user_tz)
            if end_night <= start_night:
                end_dt += timedelta(days=1)

        else:
            # حالة افتراضية إذا لم يتم تحديد day_type
            start_dt = self._hours_to_datetime(report_day, 0.0, user_tz)
            end_dt = self._hours_to_datetime(report_day + timedelta(days=1), 0.0, user_tz)

        return {
            'start_dt': start_dt,
            'end_dt': end_dt,
        }

    def _hours_to_time_str(self, total_hours):
        """تحويل الساعات العشرية إلى تنسيق hh:mm."""
        hours = int(total_hours)
        minutes = int((total_hours - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    # ==================================================
    # ⚙️ الدالة الرئيسية لتوليد التقرير
    # ==================================================
    def generate_report(self):
        self.ensure_one()

        if not self.report_day:
            raise UserError("Please select a report day.")

        # يجب تحديده بشكل صحيح في بيئة العمل الخاصة بك (أو جعله إدخالاً)
        team_id = 2
        report_day = self.report_day
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')

        # 1. جلب سجل العمليات اليومية وساعات الوردية
        fleet_op = self.env['fleet.operation'].search([('date', '=', report_day)], limit=1)
        if not fleet_op:
            raise UserError(
                _("No Fleet Daily Operation record found for the selected date. Please ensure shift hours are entered."))

        start_day_float = fleet_op.start_day
        end_day_float = fleet_op.end_day
        start_night_float = fleet_op.start_night
        end_night_float = fleet_op.end_night

        # حدود التقرير الرئيسية (مفيدة لاستعلام الـ DB)
        report_start_dt = self._hours_to_datetime(report_day, 0.0, user_tz)
        report_end_dt = self._hours_to_datetime(report_day + timedelta(days=1), 0.0, user_tz)

        # 2. جلب جميع طلبات الصيانة المحتملة
        all_potential_records = self.env['maintenance.request'].search([
            ('maintenance_team_id', '=', team_id),
            ('stage_id.name', 'not in', ['Cancelled', 'Rejected', 'Draft W.O']),
            ('request_date_time', '<', report_end_dt.astimezone(pytz.utc)),
            '|',
            ('complete_datetime', '>=', report_start_dt.astimezone(pytz.utc)),
            ('complete_datetime', '=', False),
        ], order='request_date_time asc')

        records_by_equipment = defaultdict(list)
        for rec in all_potential_records:
            if rec.equipment_id:
                records_by_equipment[rec.equipment_id].append(rec)

        # 3. معالجة كل معدة وحساب زمن التوقف
        equipment_data = {}
        for equipment, records in records_by_equipment.items():
            if not records:
                continue

            # جلب نوع الوردية للمعدة من سجل العمليات اليومية
            odometer_line = self.env['fleet.vehicle.odometer.line'].search([
                ('operation_id', '=', fleet_op.id),
                ('equipment_id', '=', equipment.id)
            ], limit=1)

            shift_type_for_equipment = odometer_line.day_type if odometer_line else 'd_s'

            # تحديد حدود الوردية الفعلية للمعدة في هذا اليوم
            shift_info = self._get_shift_boundaries(
                report_day, shift_type_for_equipment,
                start_day_float, end_day_float,
                start_night_float, end_night_float, user_tz
            )

            shift_start_dt = shift_info['start_dt']
            shift_end_dt = shift_info['end_dt']

            equipment_jobs = []
            total_downtime_hours = 0.0

            for rec in records:
                if not rec.request_date_time:
                    continue

                request_dt_local = rec.request_date_time.astimezone(user_tz)

                if rec.stage_id.name in ['Closed', 'Completed'] and rec.complete_datetime:
                    complete_dt_local = rec.complete_datetime.astimezone(user_tz)
                    end_of_actual_downtime = complete_dt_local
                else:
                    end_of_actual_downtime = shift_end_dt

                calc_start_dt = max(request_dt_local, shift_start_dt)
                calc_end_dt = min(end_of_actual_downtime, shift_end_dt)

                simple_downtime_str, downtime_in_hours = '00:00', 0.0
                if calc_end_dt > calc_start_dt:
                    delta = calc_end_dt - calc_start_dt
                    total_seconds = delta.total_seconds()
                    hours = int(total_seconds // 3600)
                    minutes = int((total_seconds % 3600) // 60)
                    simple_downtime_str = f"{hours:02d}:{minutes:02d}"
                    downtime_in_hours = hours + (minutes / 60.0)
                    total_downtime_hours += downtime_in_hours

                if downtime_in_hours <= 0:
                    continue

                job_data = {
                    'wo_number': rec.wo_number or '',
                    'maintenance_type': rec.maintenance_type or '',
                    'time_in': calc_start_dt.strftime('%H:%M'),
                    'time_out': calc_end_dt.strftime('%H:%M'),
                    'simple_downtime': simple_downtime_str,
                    'downtime_hours': downtime_in_hours,
                    'status': rec.stage_id.name or '',
                    'should_be_highlighted': request_dt_local >= shift_start_dt
                }
                equipment_jobs.append(job_data)

            if equipment_jobs:
                equipment_data[equipment.id] = {
                    'equipment': equipment,
                    'jobs': equipment_jobs,
                    'total_downtime_hours': total_downtime_hours,
                    'total_simple_downtime': self._hours_to_time_str(total_downtime_hours),
                }

        # 4. إنشاء ملف Excel وتنسيقه
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Daily Breakdowns Report')

        # --- التنسيقات ---
        title_format = workbook.add_format(
            {'bold': True, 'font_size': 16, 'font_color': '#0070C0', 'align': 'center', 'valign': 'vcenter'})
        subtitle_format = workbook.add_format({'bold': True, 'font_size': 11, 'align': 'center', 'valign': 'vcenter'})
        header_format = workbook.add_format(
            {'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        data_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        time_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': 'hh:mm'})
        hours_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '0.00'})

        # --- كتابة العناوين ---
        headers = ['No.', 'Job No.', 'Code', 'Machine Type', 'Type of downtime', 'Count',
                   'Time In', 'Time Out', 'Total Downtime', 'Downtime Hours', 'Status']
        column_widths = [5, 10, 10, 20, 20, 5, 10, 10, 15, 15, 15]

        worksheet.set_row(1, 30)
        worksheet.merge_range(1, 0, 1, len(headers) - 1, 'Follow up on daily breakdowns report', title_format)
        date_range_str = f"Date: {report_day.strftime('%d-%b-%Y')} (Report Period: {report_start_dt.strftime('%H:%M')} to {report_end_dt.strftime('%H:%M')})"
        worksheet.merge_range(2, 0, 2, len(headers) - 1, date_range_str, subtitle_format)

        header_row = 4
        for col, header in enumerate(headers):
            worksheet.write(header_row, col, header, header_format)
            worksheet.set_column(col, col, column_widths[col])

        # 5. ملء البيانات
        row = header_row + 1
        sequence = 1

        all_sequenced_equipment = self.env['maintenance.equipment'].search(
            [('maintenance_team_id', '=', team_id), ('custom_sequence', '>', 0)],
            order='custom_sequence asc'
        )

        for equipment_rec in all_sequenced_equipment:
            equipment_info = equipment_data.get(equipment_rec.id, {})
            jobs = equipment_info.get('jobs', [])

            job_numbers = ", ".join(j['wo_number'] for j in jobs if j.get('wo_number'))
            time_ins = ", ".join(j['time_in'] for j in jobs)
            time_outs = ", ".join(j['time_out'] for j in jobs)
            statuses = ", ".join(j['status'] for j in jobs)
            maintenance_types = ", ".join(j['maintenance_type'] for j in jobs if j.get('maintenance_type'))
            job_count = len(jobs)
            total_simple_downtime = equipment_info.get('total_simple_downtime', '00:00')
            total_downtime_hours = equipment_info.get('total_downtime_hours', 0.0)

            row_data = [
                sequence, job_numbers, equipment_rec.code or '', equipment_rec.display_name,
                maintenance_types, job_count, time_ins, time_outs,
                total_simple_downtime, total_downtime_hours, statuses,
            ]

            # كتابة الصف
            for col, value in enumerate(row_data):
                fmt = data_format
                if col == 6 or col == 7:  # Time In, Time Out
                    fmt = data_format
                elif col == 8:  # Total Downtime (hh:mm)
                    fmt = data_format
                elif col == 9:  # Downtime Hours (Decimal)
                    fmt = hours_format

                worksheet.write(row, col, value, fmt)

            row += 1
            sequence += 1

        # 6. إغلاق وإرجاع الملف
        workbook.close()
        output.seek(0)
        self.report_file = base64.b64encode(output.read())
        output.close()
        date_str = self.report_day.strftime('%d-%m-%Y')
        day_num = self.report_day.strftime('%d')
        self.report_filename = f'{day_num}-day_daily_breakdowns_report_{date_str}.xlsx'

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=report_file&download=true&filename={self.report_filename}',
            'target': 'self',
        }