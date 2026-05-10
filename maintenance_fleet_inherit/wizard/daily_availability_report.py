# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
import pytz
from io import BytesIO
import base64
import xlsxwriter
from odoo.exceptions import UserError


class DailyAvailabilityReportWizard(models.TransientModel):
    _name = 'daily.availability.report.wizard'
    _description = 'Daily Availability Report Wizard'

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)

    report_file = fields.Binary('Report File', attachment=False)
    report_filename = fields.Char('Report Filename', size=64)

    # ==================================================
    # Helpers
    # ==================================================

    def _hours_to_datetime(self, date_obj, hours_float, user_tz):
        hour = int(hours_float)
        minute = int((hours_float % 1) * 60)

        target_dt = datetime.combine(date_obj, time(hour % 24, minute))

        if hours_float >= 24:
            target_dt += timedelta(days=int(hours_float // 24))

        return user_tz.localize(target_dt)

    def _get_shift_boundaries(
            self,
            report_day,
            shift_type,
            start_day,
            end_day,
            start_night,
            end_night,
            user_tz
    ):

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

    # ==================================================
    # Main Report
    # ==================================================

    def generate_machines_availability_report(self):

        self.ensure_one()

        if not self.date_from or not self.date_to:
            raise UserError(_("Please select date range."))

        if self.date_from > self.date_to:
            raise UserError(_("Date From must be before Date To."))

        user_tz = pytz.timezone(self.env.user.tz or 'UTC')

        team_id = 2

        equipments = self.env['maintenance.equipment'].search([
            ('maintenance_team_id', '=', team_id),
            ('custom_sequence', '>', 0)
        ], order='custom_sequence asc')

        if not equipments:
            raise UserError(_("No equipment found for this team."))

        output = BytesIO()

        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        worksheet = workbook.add_worksheet('Daily Fleet Operation Report')

        # ==================================================
        # Formats
        # ==================================================

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'font_color': '#0070C0',
            'align': 'center',
            'valign': 'vcenter'
        })

        subtitle_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter'
        })

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9D9D9',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        data_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })

        red_bg = workbook.add_format({
            'bg_color': '#FFC7CE',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })

        blue_bg = workbook.add_format({
            'bg_color': '#C6E0FF',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })

        percent_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'num_format': '0.00%'
        })

        float_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'num_format': '0.00'
        })

        # ==================================================
        # Headers
        # ==================================================

        headers = [
            'Day',
            'No.',
            'Code',
            'Machine Type',
            'Equipment Type',
            'Day Type',
            'Operation Type',
            'Work Location',
            'Target Hrs',
            'Start',
            'End',
            'Actual Hrs',
            'Downtime Hrs',
            'Standby Hrs',
            'Available Hrs',
            'Availability %',
            'Utilization %',
            'Fuel Cons. (L)',
            'Fuel/L-H',
            'Standard Fuel L/H'
        ]

        worksheet.set_row(0, 30)

        worksheet.merge_range(
            0,
            0,
            0,
            len(headers) - 1,
            'Daily Fleet Operation Report',
            title_format
        )

        period_str = (
            f"Period: "
            f"{self.date_from.strftime('%d-%b-%Y')} "
            f"To "
            f"{self.date_to.strftime('%d-%b-%Y')}"
        )

        worksheet.merge_range(
            1,
            0,
            1,
            len(headers) - 1,
            period_str,
            subtitle_format
        )

        header_row = 2

        for col, header in enumerate(headers):
            worksheet.write(header_row, col, header, header_format)

        row = header_row + 1
        seq = 1

        current_day = self.date_from

        # ==================================================
        # Loop Days
        # ==================================================

        while current_day <= self.date_to:

            fleet_op = self.env['fleet.operation'].search([
                ('date', '=', current_day)
            ], limit=1)

            if not fleet_op:
                current_day += timedelta(days=1)
                continue

            start_day_float = fleet_op.start_day or 0.0
            end_day_float = fleet_op.end_day or 0.0
            start_night_float = fleet_op.start_night or 0.0
            end_night_float = fleet_op.end_night or 0.0

            for eq in equipments:

                odometer_lines = self.env['fleet.vehicle.odometer.line'].search([
                    ('equipment_id', '=', eq.id),
                    ('operation_id.date', '=', current_day)
                ])

                od_line = odometer_lines[:1]

                standard_fuel = eq.stander_fuel or 0.0

                equipment_type = eq.type_of_equipment or ''

                shift_type_for_equipment = od_line.day_type if od_line else 'd_s'

                shift_info = self._get_shift_boundaries(
                    current_day,
                    shift_type_for_equipment,
                    start_day_float,
                    end_day_float,
                    start_night_float,
                    end_night_float,
                    user_tz
                )

                shift_start_dt = shift_info['start_dt']
                shift_end_dt = shift_info['end_dt']

                # ==================================================
                # Downtime
                # ==================================================

                downtime_hrs = 0.0

                requests = self.env['maintenance.request'].search([
                    ('equipment_id', '=', eq.id),
                    ('stage_id.name', 'not in', ['Cancelled', 'Rejected']),
                    ('request_date_time', '<', shift_end_dt.astimezone(pytz.utc).replace(tzinfo=None)),
                    '|',
                    ('complete_datetime', '>=', shift_start_dt.astimezone(pytz.utc).replace(tzinfo=None)),
                    ('complete_datetime', '=', False),
                ], order='request_date_time asc')

                for req in requests:

                    if not req.request_date_time:
                        continue

                    request_dt_local = req.request_date_time.astimezone(user_tz)

                    if req.stage_id.name in ['Closed', 'Completed'] and req.complete_datetime:
                        complete_dt_local = req.complete_datetime.astimezone(user_tz)
                        end_of_actual_downtime = complete_dt_local
                    else:
                        end_of_actual_downtime = shift_end_dt

                    calc_start_dt = max(request_dt_local, shift_start_dt)
                    calc_end_dt = min(end_of_actual_downtime, shift_end_dt)

                    if calc_end_dt > calc_start_dt:
                        delta = calc_end_dt - calc_start_dt
                        downtime_hrs += delta.total_seconds() / 3600.0

                # ==================================================
                # Metrics
                # ==================================================

                target_hrs = od_line.day_duration if od_line else 11.0

                start_val = od_line.start_value if od_line else 0.0
                end_val = od_line.end_value if od_line else 0.0

                actual_hrs = od_line.distance if od_line else 0.0

                standby_hrs = target_hrs - actual_hrs + downtime_hrs

                available_hrs = actual_hrs + standby_hrs

                fuel_line = self.env['issuance.request.line'].search([
                    ('product_id.default_code', '=', 'GM-GAS-00-0000'),
                    ('equipment_id', '=', eq.id),
                    ('x_studio_request_date', '>=', shift_start_dt),
                    ('x_studio_request_date', '<=', shift_end_dt),
                ], order='x_studio_request_date desc', limit=1)

                fuel_consumption = fuel_line.qty_issued if fuel_line else 0.0

                fuel_per_hr = round(
                    fuel_consumption / actual_hrs if actual_hrs else 0.0,
                    2
                )

                total_time_for_availability = (
                        actual_hrs +
                        downtime_hrs +
                        standby_hrs
                )

                availability = round(
                    (
                        available_hrs / total_time_for_availability
                    ) if total_time_for_availability > 0 else 0.0,
                    2
                )

                utilization = round(
                    (
                        actual_hrs / (actual_hrs + standby_hrs)
                    ) if (actual_hrs + standby_hrs) > 0 else 0.0,
                    2
                )

                supposed_fuel = actual_hrs * standard_fuel

                downtime_str = self._float_to_time_str(downtime_hrs)
                standby_str = self._float_to_time_str(standby_hrs)
                available_str = self._float_to_time_str(available_hrs)

                day_type = (
                    od_line._fields['day_type'].convert_to_export(
                        od_line.day_type,
                        od_line
                    ) if od_line else ''
                )

                operation_type = (
                    od_line._fields['operation_type'].convert_to_export(
                        od_line.operation_type,
                        od_line
                    ) if od_line else ''
                )

                location = (
                    od_line.location_id.name
                    if od_line and od_line.location_id
                    else ''
                )

                # ==================================================
                # Row Data
                # ==================================================

                row_data = [
                    current_day.strftime('%d-%m-%Y'),
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
                    availability,
                    utilization,
                    fuel_consumption,
                    fuel_per_hr,
                    supposed_fuel,
                ]

                row_format = data_format

                day_type_value = od_line.day_type if od_line else None
                operation_type_value = od_line.operation_type if od_line else None

                if operation_type_value == 'non_operation':
                    row_format = red_bg

                elif day_type_value == 'd_n_s':
                    row_format = blue_bg

                # ==================================================
                # Write Row
                # ==================================================

                for col, value in enumerate(row_data):

                    fmt = row_format

                    if col in [8, 9, 10, 11, 17, 18, 19]:
                        fmt = float_format

                    elif col in [15, 16]:
                        fmt = percent_format

                    worksheet.write(row, col, value, fmt)

                row += 1
                seq += 1

            current_day += timedelta(days=1)

        # ==================================================
        # Column Widths
        # ==================================================

        for col in range(len(headers)):
            worksheet.set_column(col, col, 18)

        workbook.close()

        output.seek(0)

        self.report_file = base64.b64encode(output.read())

        output.close()

        filename = (
            f"Daily_Fleet_Report_"
            f"{self.date_from.strftime('%d-%m-%Y')}"
            f"_TO_"
            f"{self.date_to.strftime('%d-%m-%Y')}.xlsx"
        )

        self.report_filename = filename

        return {
            'type': 'ir.actions.act_url',
            'url': (
                f'/web/content?model={self._name}'
                f'&id={self.id}'
                f'&field=report_file'
                f'&download=true'
                f'&filename={filename}'
            ),
            'target': 'self',
        }