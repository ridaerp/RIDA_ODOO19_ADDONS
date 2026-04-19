from odoo import models, fields, api, _
import base64
from io import BytesIO
import xlsxwriter
from collections import defaultdict
from odoo.exceptions import UserError


class OilConsumptionWizard(models.TransientModel):
    _name = "oil.consumption.wizard"
    _description = "Oil Consumption Report Wizard"

    # 1. دالة لتعيين القيمة الافتراضية لفئة المنتج 'Lubricants'
    def _get_default_lubricants_category(self):
        """Finds the 'Lubricants' category to set as the default value."""
        # يبحث عن الفئة بالاسم 'Lubricants' ويعيد الـ ID الخاص بها
        return self.env['product.category'].search([('name', '=', 'Lubricants')], limit=1).id

    date_from = fields.Date("Date From", required=True)
    date_to = fields.Date("Date To", required=True)

    department_id = fields.Many2one(
        'hr.department',
        string="Department",
        help="Filter the report by a specific department. Leave empty for all departments."
    )
    # 2. تعيين القيمة الافتراضية للحقل
    product_cat = fields.Many2one(
        'product.category',
        string='Product Category',
        default=_get_default_lubricants_category
    )
    file_data = fields.Binary("File", readonly=True)
    file_name = fields.Char("File Name", readonly=True)

    def action_export_excel(self):
        """Generates the Excel report for lubricants issuance requests in a pivot-style format."""
        self.ensure_one()

        if self.date_from > self.date_to:
            raise UserError(_("Date From must be before Date To"))

        # تأكد من وجود فئة منتج، سيتم تعيينها افتراضياً إلى Lubricants
        if not self.product_cat:
            raise UserError(_("Product Category is required for this report."))

        # 3. بناء نطاق البحث (Domain)
        domain = [
            ('request_id.request_date', '>=', self.date_from),
            ('request_id.request_date', '<=', self.date_to),
            ('qty_issued', '>', 0),  # Only include lines with issued quantity
            # استخدام ID الفئة المحددة/الافتراضية للتصفية
            ('product_id.categ_id', '=', self.product_cat.id)
        ]

        # 4. إضافة تصفية القسم (شرطية: يتم إضافتها فقط إذا اختار المستخدم قسماً)
        if self.department_id:
            domain.append(('request_id.department_id', '=', self.department_id.id))

        # Search for all relevant lines
        lines = self.env['issuance.request.line'].search(domain)

        if not lines:
            # رسالة خطأ أكثر تفصيلاً
            filter_info = f"Category: {self.product_cat.name}"
            if self.department_id:
                filter_info += f", Department: {self.department_id.name}"

            raise UserError(_(f"No data found in selected period with filters: {filter_info}."))

        # 5. Collect unique product names (which will be the dynamic columns)
        # and pivot the data based on (Equipment, Request Date, Product Name)
        unique_products = set()
        # Use a dictionary to store pivot data: Key = (Request Date, Equipment ID)
        pivot_data = defaultdict(lambda: {
            'products': defaultdict(float),
            'equipment_code': '',
            'equipment_name': '',
            'action_type': '',  # Placeholder for ACTION
            'equipment_hours': 0,  # Placeholder for HRS
        })

        for line in lines:
            product_name = line.product_id.name
            unique_products.add(product_name)

            req_date_str = str(line.request_id.request_date)
            equipment = line.equipment_id

            # Key for pivoting: (Date, Equipment ID)
            key = (req_date_str, equipment.id)

            # Populate pivot data
            pivot_data[key]['products'][product_name] += line.qty_issued
            # Assuming equipment.code holds the unique equipment code
            pivot_data[key]['equipment_code'] = equipment.code or equipment.name or ''
            pivot_data[key]['equipment_name'] = equipment.name or ''

            # --- Placeholder data based on the provided CSV structure ---
            # NOTE: Update these lines to the actual fields in your models
            # Assuming m_request_id.maintenance_defect.name contains the ACTION type
            pivot_data[key]['action_type'] = line.request_id.m_request_id.maintenance_defect.name or ''
            # Assuming equipment.odometer contains the HRS (operating hours/odometer)
            pivot_data[key]['equipment_hours'] = equipment.odometer or 0

            # Convert unique products set to a sorted list for consistent column order
        sorted_products = sorted(list(unique_products))

        # --- Excel Generation ---
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet("Lubricants Report")

        # Define formats
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#D9D9D9', 'border': 1,
            'align': 'center', 'valign': 'vcenter', 'font_size': 11
        })
        normal_format = workbook.add_format({
            'font_size': 10, 'align': 'center', 'valign': 'vcenter', 'border': 1
        })
        float_format = workbook.add_format({
            'font_size': 10, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '0.00'
        })

        # --- Title and Header Setup ---

        # Set column widths (Approximate widths for better readability)
        sheet.set_column('A:A', 15)  # DATE
        sheet.set_column('B:B', 25)  # EQUIP. CODE
        sheet.set_column('C:C', 15)  # ACTION
        sheet.set_column('D:D', 10)  # HRS
        sheet.set_column('E:E', 20)  # Product columns start here

        # Write Main Title (spanning across all columns)
        num_cols = 4 + len(sorted_products)  # 4 fixed columns + dynamic products
        sheet.merge_range(0, 0, 0, num_cols - 1, _("OIL CONSUMPTION REPORT"), title_format)

        # --- Fixed Headers (Row 1) ---
        fixed_headers = ["DATE", "EQUIP. CODE", "ACTION", "HRS"]
        col_index = 0
        for header in fixed_headers:
            sheet.write(1, col_index, header, header_format)
            col_index += 1

        # --- Dynamic Product Headers (Row 1 continued) ---
        for product_name in sorted_products:
            sheet.write(1, col_index, product_name, header_format)
            col_index += 1

        # --- Write Pivot Data ---
        row = 2
        # Sort pivot keys primarily by date, then by equipment code/name
        sorted_keys = sorted(pivot_data.keys(), key=lambda k: (k[0], pivot_data[k]['equipment_code']))

        for key in sorted_keys:
            data = pivot_data[key]

            # Fixed Data Columns
            col_index = 0
            sheet.write(row, col_index, key[0], normal_format)  # DATE
            col_index += 1
            sheet.write(row, col_index, data['equipment_code'], normal_format)  # EQUIP. CODE
            col_index += 1
            sheet.write(row, col_index, data['action_type'], normal_format)  # ACTION
            col_index += 1
            sheet.write(row, col_index, data['equipment_hours'] or 0, float_format)  # HRS
            col_index += 1

            # Dynamic Product Columns (Quantities)
            for product_name in sorted_products:
                qty = data['products'].get(product_name, 0.0)
                sheet.write(row, col_index, qty, float_format)
                col_index += 1

            row += 1

        workbook.close()
        output.seek(0)

        # Encode file data and set file name
        self.file_data = base64.b64encode(output.read())

        # 6. تحديث اسم الملف ليشمل القسم إذا تم اختياره، واسم الفئة إذا لم تكن هي الافتراضية
        filename_parts = ["Oil_consumption_Pivot"]
        if self.department_id:
            filename_parts.append(self.department_id.name.replace(' ', '_'))

        # إضافة اسم الفئة إذا لم تكن هي القيمة الافتراضية 'Lubricants'
        if self.product_cat and self.product_cat.name and self.product_cat.name != 'Lubricants':
            filename_parts.append(self.product_cat.name.replace(' ', '_'))

        filename_parts.append(f"{self.date_from}_to_{self.date_to}")
        self.file_name = "_".join(filename_parts) + ".xlsx"

        # Return action to download the file
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=file_data&download=true&filename={self.file_name}',
            'target': 'self',
        }