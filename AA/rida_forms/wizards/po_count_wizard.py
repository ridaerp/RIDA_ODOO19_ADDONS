from odoo import models, fields, api
from odoo.exceptions import UserError
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime, timedelta

class PoCountWizard(models.TransientModel):
    _name = 'po.count.wizard'
    _description = 'Purchase Order Count Report Wizard'

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    report_file = fields.Binary('Report File', attachment=False)
    report_filename = fields.Char('Report Filename', size=64)

    def generate_report(self):
        """Generates the Excel report with detailed transaction counts and enhanced formatting."""
        self.ensure_one()

        if self.start_date > self.end_date:
            raise UserError("Start date must be before end date.")

        # --- Fetch Transaction Data ---
        transaction_data = self._get_transaction_data(self.start_date, self.end_date)

        # --- Prepare Excel workbook ---
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Transaction Report')

        # --- Formatting ---
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#0070C0'})  # Odoo Blue
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1})
        data_format = workbook.add_format({'border': 1})
        bold_data_format = workbook.add_format({'bold': True, 'border': 1})
        total_format = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1})

        # --- Column Width ---
        worksheet.set_column('A:A', 40)  # Wide column for transaction types
        worksheet.set_column('B:B', 20)  # Column for counts

        # --- Write Headers ---
        worksheet.write(0, 0, 'Start Date:', title_format)
        worksheet.write(0, 1, str(self.start_date), data_format)
        worksheet.write(1, 0, 'End Date:', title_format)
        worksheet.write(1, 1, str(self.end_date), data_format)

        # Transaction Type Headers
        headers = ['Transaction Type', 'Count']
        for col_num, header in enumerate(headers):
            worksheet.write(3, col_num, header, header_format)  # Start headers from row 3

        # --- Write Transaction Data ---
        row = 4
        total_transactions = 0
        for transaction_type, count in transaction_data.items():
            worksheet.write(row, 0, transaction_type, data_format)  # Regular data format for type
            worksheet.write(row, 1, count, bold_data_format)  # Bold data format for count
            total_transactions += count
            row += 1

        # --- Write Total ---
        total_format = workbook.add_format({'bold': True})
        worksheet.write(row, 0, 'Total Transactions:', total_format)
        worksheet.write(row, 1, total_transactions, bold_data_format)  # Bold total count


        # --- Close Workbook ---
        workbook.close()
        output.seek(0)
        excel_file = output.read()
        output.close()

        # --- Attach file to the wizard ---
        self.report_file = base64.b64encode(excel_file)
        self.report_filename = 'transaction_report.xlsx'

        # --- Return action to download the report ---
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=po.count.wizard&id=%s&field=report_file&download=true&filename=%s' % (
                self.id, self.report_filename),
            'target': 'self',
        }

    def _get_transaction_data(self, start_date, end_date):
        """Fetches transaction data from various Odoo models."""
        transaction_data = {}

        # --- SCM Purchases Orders ---
        purchase_orders = self.env['purchase.order'].search_count([
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date),
            ('ore_purchased', '=', False)
        ])
        transaction_data['SCM PO'] = purchase_orders

        material_requests = self.env['material.request'].search_count([
            ('create_date', '>=', start_date),  # Replace 'request_date' if different
            ('create_date', '<=', end_date)
        ])
        transaction_data['MR Transaction'] = material_requests

        # --- Issuance Request --- *ADJUST MODEL NAME AND DATE FIELD AS NEEDED*
        issuance_requests = self.env['issuance.request'].search_count([
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date)
        ])
        transaction_data['Issuance Request'] = issuance_requests

        payment_requests = self.env['account.payment'].search_count([
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date)
        ])
        transaction_data['Account Payment'] = payment_requests

        # --- Expense Transactions ---
        expense_transactions = self.env['hr.expense'].search_count([
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date)
        ])
        transaction_data['Expense Transaction'] = expense_transactions

        custody_transactions = self.env['account.custody'].search_count([
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date)
        ])
        transaction_data['Custody Transactions'] = custody_transactions

        vehicle_requests = self.env['vehicle.equipment.request'].search_count([
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date)
        ])
        transaction_data['Equipment Request'] = vehicle_requests

        # --- Fleet Maintenance Order ---  *ADJUST MODEL NAME AND DATE FIELD AS NEEDED*
        fleet_maintenance_orders = self.env['maintenance.request'].search_count([
            ('create_date', '>=', start_date),  # You will need to verify the model
            ('create_date', '<=', end_date), ('maintenance_team_id', 'in', [2])
        ])
        transaction_data['Fleet M. Order'] = fleet_maintenance_orders

        # --- Plant Maintenance Order --- *ADJUST MODEL NAME AND DATE FIELD AS NEEDED*
        plant_maintenance_orders = self.env['maintenance.request'].search_count([
            ('create_date', '>=', start_date), # You will need to verify the model
            ('create_date', '<=', end_date) ,("maintenance_team_id", "in", [6])],)
        transaction_data['Plant M. Order'] = plant_maintenance_orders

        # --- Construction Plant Maintenance Order --- *ADJUST MODEL NAME AND DATE FIELD AS NEEDED*
        construction_orders = self.env['maintenance.request'].search_count([
            ('create_date', '>=', start_date),  # You will need to verify the model
            ('create_date', '<=', end_date), ('maintenance_team_id', 'in', [11])
        ])
        transaction_data['Construction M. Order'] = construction_orders

        # --- Scaling Unit --- *ADJUST MODEL NAME AND DATE FIELD AS NEEDED*
        scaling_units = self.env['weight.request'].search_count([
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date),('form_type','!=','external_visit')
        ])
        transaction_data['Scaling Unit'] = scaling_units
        ### External Visit Samples --------------------------------
        external_visit_sample = self.env['weight.request'].search_count([
            ('create_date', '>=', start_date),  # Replace 'date' with the actual date field
            ('create_date', '<=', end_date),('form_type','=','external_visit')
        ])
        transaction_data['Rock Ext Visits'] = external_visit_sample
        # --- Checmical Lab Request --- *ADJUST MODEL NAME AND DATE FIELD AS NEEDED*
        chemical_lab_requests = self.env['chemical.samples.request'].search_count([
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date)
        ])
        transaction_data['Chem Lab Requests'] = chemical_lab_requests

        # --- Metallurgical Lab Request --- *ADJUST MODEL NAME AND DATE FIELD AS NEEDED*
        metallurgical_lab_requests = self.env['metallurgical.request'].search_count([
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date)
        ])
        transaction_data['Metall Lab Requests'] = metallurgical_lab_requests

        # --- Purchase Orders with Ore (Revised Correctly) ---
        ore_purchase_orders = self.env['purchase.order'].search_count([
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date),
            ('ore_purchased', '=', True)

        ])
        transaction_data['Ore/Rock PO'] = ore_purchase_orders

        # --- KPI (Executive & Non-Executive) --- *ADJUST MODEL NAME AND DATE FIELD AS NEEDED*
        kpi_executive_count = self.env['kpi.person'].search_count([
            ('create_date', '>=', start_date),  # Replace 'date' with the actual date field
            ('create_date', '<=', end_date)
        ])
        transaction_data['KPI Executives'] = kpi_executive_count

        kpi_no_executive_count = self.env['kpi.non.exective'].search_count([
            ('create_date', '>=', start_date),  # Replace 'date' with the actual date field
            ('create_date', '<=', end_date)
        ])
        transaction_data['KPI Non-Executives'] = kpi_no_executive_count

        # --- Medicare Transactions --- *ADJUST MODEL NAME AND DATE FIELD AS NEEDED*
        ######################## Midcare Transaction
        medicare_issuance_request = self.env['medicare.issuance.request'].search_count([
            ('create_date', '>=', self.start_date),
            ('create_date', '<=', self.end_date)
        ])
        lab_request = self.env['lab.request'].search_count([
            ('create_date', '>=', self.start_date),
            ('create_date', '<=', self.end_date)
        ])
        minor_request = self.env['minor.room'].search_count([
            ('create_date', '>=', self.start_date),
            ('create_date', '<=', self.end_date)
        ])
        doctor_request = self.env['doctor.visit'].search_count([
            ('create_date', '>=', self.start_date),
            ('create_date', '<=', self.end_date)
        ])

        transaction_data[
            'Medicare Transactions'] = medicare_issuance_request + lab_request + minor_request + doctor_request
        ######################## End Medicare Transaction

        return transaction_data