# models/report_overtime_wizard.py
import io
import base64
from datetime import date
import xlsxwriter

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from calendar import monthrange

class OvertimeReportWizard(models.TransientModel):
    _name = 'overtime.report.wizard'
    _description = 'Overtime Report Wizard'

    month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Month', required=True, default=lambda self: date.today().strftime("%m"))

    year = fields.Integer(string='Year', required=True, default=lambda self: date.today().year)
    department_id = fields.Many2one('hr.department', string='Department', help="Leave empty to include all departments")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # For download
    xlsx_file = fields.Binary('XLSX Report', readonly=True)
    xlsx_filename = fields.Char('Filename', readonly=True)

    def _get_date_range(self):
        m = int(self.month)
        y = int(self.year)

        # أول يوم في الشهر
        start_date = date(y, m, 1)

        # آخر يوم في الشهر
        last_day = monthrange(y, m)[1]
        end_date = date(y, m, last_day)

        return str(start_date), str(end_date)

    def _gather_lines(self):
        """Collect overtime.batch.line records for batches inside selected month +/- optional department."""
        start, end = self._get_date_range()
        domain = [('date', '>=', start), ('date', '<=', end)]

        # Filter by company too to be safe
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))

        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))

        batches = self.env['hr.overtime.batch'].search(domain)
        if not batches:
            return self.env['overtime.batch.line'].browse()  # empty recordset

        # Gather all lines from those batches
        lines = self.env['overtime.batch.line'].search([('request_id', 'in', batches.ids)])
        return lines.sorted(key=lambda r: (r.employee_id and r.employee_id.emp_code or '', r.employee_id.name))

    def action_print_xlsx(self):
        lines = self._gather_lines()
        if not lines:
            raise UserError(_('No data found for the selected period/filters.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Overtime Report')

        # ===== Formats =====
        bold = workbook.add_format({'bold': True})
        title_format = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'})
        sub_title_fmt = workbook.add_format({'italic': True, 'font_size': 12, 'align': 'center'})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center'})
        date_fmt = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1, 'align': 'center'})
        text_fmt = workbook.add_format({'font_size': 11, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        number_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1, 'align': 'center'})
        integer_fmt = workbook.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center'})
        total_label_fmt = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#F2F2F2'})
        total_number_fmt = workbook.add_format(
            {'bold': True, 'num_format': '#,##0.00', 'border': 1, 'align': 'center', 'bg_color': '#F2F2F2'})

        # ===== Title =====
        title = f"Overtime Report - {self.year}-{self.month}"
        sheet.merge_range(0, 0, 0, 11, title, title_format)
        sheet.set_row(0, 28)
        sheet.set_row(1, 22)

        # ===== Column Headers =====
        headers = [
            'Employee Code', 'Employee Name', 'Department', 'Company', 'Work From', 'Work To',
            'Normal Hours', 'Holiday Hours', 'Work Nat Hours', 'Overtime', 'Tax', 'Net Overtime'
        ]
        for col, head in enumerate(headers):
            sheet.write(2, col, head, header_fmt)

        # ===== Set Column Widths =====
        col_widths = [15, 50, 20, 25, 12, 12, 15, 15, 15, 15, 15, 15]
        for idx, width in enumerate(col_widths):
            sheet.set_column(idx, idx, width)

        # ===== Write Rows =====
        row = 3
        total_normal = total_holiday = total_work_nat = total_ot = total_tax = total_net = 0.0

        for ln in lines:
            emp = ln.employee_id
            sheet.write(row, 0, emp.emp_code or '', text_fmt)
            sheet.write(row, 1, emp.name or '', text_fmt)
            sheet.write(row, 2, emp.department_id.name or '', text_fmt)
            sheet.write(row, 3, ln.company_id.name or '', text_fmt)

            if ln.work_from:
                sheet.write_datetime(row, 4, fields.Datetime.to_datetime(str(ln.work_from)), date_fmt)
            else:
                sheet.write(row, 4, '', text_fmt)
            if ln.work_to:
                sheet.write_datetime(row, 5, fields.Datetime.to_datetime(str(ln.work_to)), date_fmt)
            else:
                sheet.write(row, 5, '', text_fmt)

            sheet.write_number(row, 6, ln.normal_hours or 0.0, integer_fmt)
            sheet.write_number(row, 7, ln.holiday_hours or 0.0, integer_fmt)
            sheet.write_number(row, 8, ln.work_nat_hours or 0.0, integer_fmt)
            sheet.write_number(row, 9, ln.overtime or 0.0, number_fmt)
            sheet.write_number(row, 10, ln.tax or 0.0, number_fmt)
            sheet.write_number(row, 11, ln.net_overtime or 0.0, number_fmt)

            total_normal += ln.normal_hours or 0.0
            total_holiday += ln.holiday_hours or 0.0
            total_work_nat += ln.work_nat_hours or 0.0
            total_ot += ln.overtime or 0.0
            total_tax += ln.tax or 0.0
            total_net += ln.net_overtime or 0.0

            row += 1

        # ===== Totals Row =====
        sheet.write(row, 0, 'TOTAL', total_label_fmt)
        sheet.write(row, 6, total_normal, total_number_fmt)
        sheet.write(row, 7, total_holiday, total_number_fmt)
        sheet.write(row, 8, total_work_nat, total_number_fmt)
        sheet.write(row, 9, total_ot, total_number_fmt)
        sheet.write(row, 10, total_tax, total_number_fmt)
        sheet.write(row, 11, total_net, total_number_fmt)

        # ===== Close workbook =====
        workbook.close()
        output.seek(0)
        data = output.read()
        output.close()

        self.xlsx_file = base64.b64encode(data)
        self.xlsx_filename = f"Overtime_Report_{self.year}_{self.month}.xlsx"

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{self._name}/{self.id}/xlsx_file/{self.xlsx_filename}?download=true",
            'target': 'self',
        }

    # helper to open wizard from a hr.overtime.batch with default values
    @api.model
    def open_wizard_from_batch(self, batch_id):
        batch = self.env['hr.overtime.batch'].browse(batch_id)
        month = batch.date.strftime("%m") if batch.date else date.today().strftime("%m")
        year = batch.date.year if batch.date else date.today().year
        return {
            'name': _('Overtime Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'overtime.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_month': month,
                'default_year': year,
                'default_department_id': batch.department_id.id or False,
                'default_company_id': batch.company_id.id or batch.company_id.id,
            }
        }
