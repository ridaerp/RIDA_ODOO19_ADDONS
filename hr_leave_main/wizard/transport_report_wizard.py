from odoo import models, fields, api, _
import base64
from io import BytesIO
import xlsxwriter
from odoo.exceptions import UserError


class TransportReportWizard(models.TransientModel):
    _name = 'transport.report.wizard'
    _description = 'Transportation Report Wizard'

    date_from = fields.Date("From Date", required=True)
    date_to = fields.Date("To Date", required=True)

    # 1. New field: Add rotation type selection
    rotation_type = fields.Selection(
        [('in', 'Leave (Out)'), ('out', 'Arrival (In)')],
        string="Rotation Type",
        required=True
    )

    report_file = fields.Binary("Report File")
    report_name = fields.Char("Report Name", default="transportation_report.xlsx")

    def action_generate_report(self):
        """Generate Excel Transportation Report"""
        self.ensure_one()

        if not self.date_from or not self.rotation_type:
            raise UserError(_("Please select a date range and rotation type."))

        # Create the buffer
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet("Transportation")

        # --- 1. Logo Insertion (Insert Company Logo at A1) ---
        company = self.env.company
        logo_stream = False
        if company.logo:
            try:
                # Prepare logo for insertion
                logo_stream = BytesIO(base64.b64decode(company.logo))
                # Insert logo at A1. Adjust scale as needed (0.5 is a common value)
                sheet.insert_image('C1', 'logo.png', {'image_data': logo_stream, 'x_scale': 0.1, 'y_scale': 0.1})
            except Exception:
                # Handle potential errors in base64 decoding or image insertion gracefully
                pass

        # --- Formats ---
        # Format for the main title inside the Excel sheet
        title_format = workbook.add_format({
            'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'
        })
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#D9D9D9', 'border': 1,
            'align': 'center', 'valign': 'vcenter'
        })
        normal_format = workbook.add_format({
            'font_size': 11,
            'align': 'center', 'valign': 'vcenter', 'border': 1
        })
        amount_format = workbook.add_format(
            {'num_format': '#,##0.00', 'align': 'center', 'valign': 'vcenter', 'border': 1})

        # Determine the report prefix based on the selected rotation_type
        if self.rotation_type == 'in':
            report_name_prefix = _("Transport Leave")
        else:
            report_name_prefix = _("Transport Arrival")

        full_title = f"{report_name_prefix} Report ({self.date_from.strftime('%d/%m/%Y')} - {self.date_to.strftime('%d/%m/%Y')})"

        # Insert the title in the sheet (e.g., merge and center across A2:D2)
        sheet.merge_range('A5:D5', full_title, title_format)
        # Header starts at row 4 (index 3) to leave space for the logo and title
        header_row_index = 7

        # --- Header Row ---
        headers = ["Employee Code","Employee Name", "Department", "Location","Number of Bus", "Number of Ticket", "Amount"]

        # Set column widths for better readability
        sheet.set_column('A:A', 20)  # Employee Code
        sheet.set_column('B:B', 40)  # Employee Name
        sheet.set_column('C:C', 30)  # Department
        sheet.set_column('D:D', 30)  # Location
        sheet.set_column('E:E', 17)  # Numbers
        sheet.set_column('F:G', 17)  # Amount

        for col, h in enumerate(headers):
            sheet.write(header_row_index, col, h, header_format)

        # --- Filter Data ---

        # 2. Dynamic Date Filtering Logic based on type
        if self.rotation_type == 'in':
            # For 'in', use date_from/date_to overlap check
            date_domain = [
                ('date_from', '<=', self.date_to),
                ('date_to', '>=', self.date_from),
            ]
        elif self.rotation_type == 'out':
            # For 'out', use date_arrival which is the relevant date field in the line.
            date_domain = [
                ('date_arrival', '>=', self.date_from),
                ('date_arrival', '<=', self.date_to),
            ]
        else:
            date_domain = []  # Should not happen

        # Combine mandatory filters with the dynamic date filter
        domain = date_domain + [
            # فلترة حسب النوع المحدد في الويزارد
            ('request_id.type', '=', self.rotation_type),
        ]

        lines = self.env['employees.rotation.line'].search(domain)

        # --- Write Data ---
        row = header_row_index + 1
        for rec in lines:
            sheet.write(row, 0, rec.employee_id.emp_code or "", normal_format)
            sheet.write(row, 1, rec.employee_id.name or "", normal_format)
            sheet.write(row, 2, rec.employee_id.department_id.name or "", normal_format)
            sheet.write(row, 3, rec.location_id.name or "", normal_format)
            sheet.write(row, 4, rec.num_bus or 0, normal_format)
            sheet.write(row, 5, rec.num_ticket or 0, normal_format)
            sheet.write(row, 6, rec.amount or 0, amount_format)
            row += 1

        # --- Close and Encode ---
        workbook.close()

        output.seek(0)
        file_data = output.read()
        output.close()

        # Close logo stream if opened
        if logo_stream:
            logo_stream.close()

        self.report_file = base64.b64encode(file_data)

        # 3. Dynamic Filename Generation uses the determined prefix
        filename = f"{report_name_prefix}-Report-{self.date_from.strftime('%d-%m-%Y')}.xlsx"
        self.report_name = filename

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=report_file&download=true&filename={filename}',
            'target': 'self',
        }