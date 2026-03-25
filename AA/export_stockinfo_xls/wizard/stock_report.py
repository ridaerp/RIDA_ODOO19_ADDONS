# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import io
import json
from datetime import datetime
import pytz
from odoo import fields, models
from odoo.tools import date_utils

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class StockReport(models.TransientModel):
    _name = "stock.xls.report"
    _description = "Current Stock History"

    warehouse_ids = fields.Many2many('stock.warehouse',
                                     string='Warehouse',
                                     required=True)
    category_ids = fields.Many2many('product.category',
                                    string='Category')

    def export_xls(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'warehouse': self.warehouse_ids.ids,
            'category': self.category_ids.ids,
        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'stock.xls.report',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Current Stock History',
                     },
            'report_type': 'stock_xlsx'
        }

    def get_warehouse(self, data):
        warehouse = self.env['stock.warehouse'].search(
            [('id', 'in', data.warehouse_ids.mapped('id'))])
        warehouse_name = [rec.name for rec in warehouse]
        warehouse_id = [rec.id for rec in warehouse]
        return warehouse_name, warehouse_id

    def get_lines(self, data, warehouse_id_int):
        lines = []
        if data.mapped('id'):
            category_products = self.env['product.product'].search(
                [('categ_id', 'in', data.mapped('id'))])
        else:
            category_products = self.env['product.product'].search([])
        product_ids_tuple = tuple([pro_id.id for pro_id in category_products])

        sale_data = {}
        purchase_data = {}

        if product_ids_tuple:
            sale_query = """
                   SELECT sum(s_o_l.product_uom_qty) AS product_uom_qty, s_o_l.product_id FROM sale_order_line AS s_o_l
                   JOIN sale_order AS s_o ON s_o_l.order_id = s_o.id
                   WHERE s_o.state IN ('sale','done')
                   AND s_o.warehouse_id = %s
                   AND s_o_l.product_id in %s group by s_o_l.product_id"""
            params_sale = (warehouse_id_int, product_ids_tuple)
            self._cr.execute(sale_query, params_sale)
            for res in self._cr.dictfetchall():
                sale_data[res['product_id']] = res['product_uom_qty']

            purchase_query = """
                   SELECT sum(p_o_l.product_qty) AS product_qty, p_o_l.product_id FROM purchase_order_line AS p_o_l
                   JOIN purchase_order AS p_o ON p_o_l.order_id = p_o.id
                   INNER JOIN stock_picking_type AS s_p_t ON p_o.picking_type_id = s_p_t.id
                   WHERE p_o.state IN ('purchase','done')
                   AND s_p_t.warehouse_id = %s AND p_o_l.product_id in %s group by p_o_l.product_id"""
            params_purchase = (warehouse_id_int, product_ids_tuple)
            self._cr.execute(purchase_query, params_purchase)
            for res in self._cr.dictfetchall():
                purchase_data[res['product_id']] = res['product_qty']

        for rec in category_products:
            sale_value = sale_data.get(rec.id, 0)
            purchase_value = purchase_data.get(rec.id, 0)

            ctx_warehouse = {'warehouse': warehouse_id_int}
            virtual_available = rec.with_context(ctx_warehouse).virtual_available
            outgoing_qty = rec.with_context(ctx_warehouse).outgoing_qty
            incoming_qty = rec.with_context(ctx_warehouse).incoming_qty
            available_qty = virtual_available + outgoing_qty - incoming_qty
            net_on_hand_qty = rec.with_context(ctx_warehouse).qty_available

            stock_locations_str = ""
            warehouse_obj = self.env['stock.warehouse'].browse(warehouse_id_int)
            if warehouse_obj.lot_stock_id:
                child_location_ids = self.env['stock.location'].search([
                    ('id', 'child_of', warehouse_obj.lot_stock_id.id),
                    ('usage', '=', 'internal')
                ]).ids
                if child_location_ids:
                    quants = self.env['stock.quant'].search([
                        ('product_id', '=', rec.id),
                        ('quantity', '>', 0),
                        ('location_id', 'in', child_location_ids)
                    ])
                    location_names = sorted(list(set([q.location_id.display_name for q in quants])))
                    stock_locations_str = ", ".join(location_names)

            # Removed product_default_location fetching

            vals = {
                'sku': rec.default_code,
                'part_number': rec.part_number if hasattr(rec, 'part_number') else '',
                'name': rec.name,
                'category': rec.categ_id.name,
                # 'product_default_location': product_default_location_str, # Removed
                'cost_price': rec.standard_price,
                'available': available_qty,
                'virtual': virtual_available,
                'incoming': incoming_qty,
                'outgoing': outgoing_qty,
                'net_on_hand': net_on_hand_qty,
                'total_value': net_on_hand_qty * rec.standard_price,
                'sale_value': sale_value,
                'purchase_value': purchase_value,
                'stock_locations': stock_locations_str,  # Actual stock locations in this warehouse
            }
            lines.append(vals)
        return lines

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Stock Info')
        # Styles
        format0 = workbook.add_format({'font_size': 20, 'align': 'center', 'bold': True})
        format1 = workbook.add_format({'font_size': 14, 'align': 'vcenter', 'bold': True})
        format11 = workbook.add_format({'font_size': 12, 'align': 'center', 'bold': True})
        format21 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True, 'valign': 'vcenter'})
        format4 = workbook.add_format({'font_size': 12, 'align': 'left', 'bold': True})
        font_size_8 = workbook.add_format({'font_size': 8, 'align': 'center', 'valign': 'vcenter'})
        font_size_8_l = workbook.add_format({'font_size': 8, 'align': 'left', 'valign': 'vcenter'})
        font_size_8_r = workbook.add_format({'font_size': 8, 'align': 'right', 'valign': 'vcenter'})
        red_mark = workbook.add_format({'font_size': 8, 'bg_color': 'red', 'align': 'center', 'valign': 'vcenter'})

        # Product Info: SKU(1),PartNo(1),Name(3),Cat(2),Cost(1) = 8 columns
        product_info_cols = 8
        # Warehouse block: Avail(1),Virt(1),In(1),Out(1),NetOnHand(2),WHLocations(2),Sold(2),Purch(2),Val(1) = 13 columns
        cols_per_warehouse = 13

        # Titles (Adjusted for 8 product info columns)
        title_start_col = (product_info_cols // 2) - 1  # e.g. 8//2 - 1 = 3 (D)
        title_end_col = title_start_col + 2  # e.g. 3+2 = 5 (F)
        sheet.merge_range(1, title_start_col, 2, title_end_col, 'Product Stock Info', format0)
        sheet.merge_range(3, title_start_col, 3, title_end_col, self.env.user.company_id.name, format11)

        y_offset = 4
        if self.browse(data['ids']).category_ids:
            category_names = self.browse(data['ids']).category_ids.mapped('name')
            sheet.merge_range(y_offset, 0, y_offset, 1, 'Category(s):', format4)
            sheet.merge_range(y_offset, 2, y_offset, 2 + len(category_names), ', '.join(category_names), format4)
            y_offset += 1

        ware_house_names, ware_house_ids = self.get_warehouse(self.browse(data['ids']))
        sheet.merge_range(y_offset, 0, y_offset, 1, 'Warehouse(s):', format4)
        sheet.merge_range(y_offset, 2, y_offset, 2 + len(ware_house_names), ', '.join(ware_house_names), format4)
        y_offset += 2

        user = self.env.user
        tz = pytz.timezone(user.tz or 'UTC')
        report_datetime = pytz.utc.localize(datetime.now()).astimezone(tz)
        report_date_col_end = product_info_cols - 1

        sheet.merge_range(f'A{y_offset}:{xlsxwriter.utility.xl_col_to_name(report_date_col_end)}{y_offset}',
                          'Report Date: ' + report_datetime.strftime("%Y-%m-%d %H:%M %p"), format1)

        warehouse_header_start_col = product_info_cols
        if ware_house_names:
            sheet.merge_range(y_offset - 1, warehouse_header_start_col, y_offset - 1,
                              warehouse_header_start_col + (len(ware_house_names) * cols_per_warehouse) - 1,
                              'Warehouses', format1)

        header_row = y_offset + 1
        sheet.merge_range(f'A{header_row}:{xlsxwriter.utility.xl_col_to_name(report_date_col_end)}{header_row}',
                          'Product Information', format11)

        # Product Information Column Headers
        col_idx = 0
        sheet.write(header_row + 1, col_idx, 'SKU', format21);
        col_idx += 1
        sheet.write(header_row + 1, col_idx, 'Part Number', format21);
        col_idx += 1
        sheet.merge_range(header_row + 1, col_idx, header_row + 1, col_idx + 2, 'Name', format21);
        col_idx += 3
        sheet.merge_range(header_row + 1, col_idx, header_row + 1, col_idx + 1, 'Category', format21);
        col_idx += 2
        # Removed 'Product Location' header
        sheet.write(header_row + 1, col_idx, 'Cost Price', format21)  # Cost Price now at col_idx

        # Warehouse specific headers
        current_wh_header_col = product_info_cols  # Starts after 8 product info columns
        for wh_name in ware_house_names:
            sheet.merge_range(header_row, current_wh_header_col, header_row,
                              current_wh_header_col + cols_per_warehouse - 1, wh_name, format11)
            col = current_wh_header_col
            sheet.write(header_row + 1, col, 'Available', format21);
            col += 1
            sheet.write(header_row + 1, col, 'Virtual', format21);
            col += 1
            sheet.write(header_row + 1, col, 'Incoming', format21);
            col += 1
            sheet.write(header_row + 1, col, 'Outgoing', format21);
            col += 1
            sheet.merge_range(header_row + 1, col, header_row + 1, col + 1, 'Net On Hand', format21);
            col += 2
            sheet.merge_range(header_row + 1, col, header_row + 1, col + 1, 'Stock Locations', format21);
            col += 2
            sheet.merge_range(header_row + 1, col, header_row + 1, col + 1, 'Total Sold', format21);
            col += 2
            sheet.merge_range(header_row + 1, col, header_row + 1, col + 1, 'Total Purchased', format21);
            col += 2
            sheet.write(header_row + 1, col, 'Valuation', format21)
            current_wh_header_col += cols_per_warehouse

        data_start_row = header_row + 2

        if ware_house_ids:
            first_wh_id = ware_house_ids[0]
            product_lines_for_static_info = self.get_lines(self.browse(data['ids']).category_ids, first_wh_id)
            current_data_row = data_start_row
            for line in product_lines_for_static_info:
                col_idx = 0
                sheet.write(current_data_row, col_idx, line.get('sku', ''), font_size_8);
                col_idx += 1
                sheet.write(current_data_row, col_idx, line.get('part_number', ''), font_size_8_l);
                col_idx += 1
                sheet.merge_range(current_data_row, col_idx, current_data_row, col_idx + 2, line.get('name', ''),
                                  font_size_8_l);
                col_idx += 3
                sheet.merge_range(current_data_row, col_idx, current_data_row, col_idx + 1, line.get('category', ''),
                                  font_size_8_l);
                col_idx += 2
                # Removed 'product_default_location' data writing
                sheet.write(current_data_row, col_idx, line.get('cost_price', 0),
                            font_size_8_r)  # Cost Price now at col_idx
                current_data_row += 1

        current_wh_data_col_start = product_info_cols  # Correctly starts after 8 product info columns
        for wh_id in ware_house_ids:
            product_lines_for_wh = self.get_lines(self.browse(data['ids']).category_ids, wh_id)
            current_data_row = data_start_row
            for line in product_lines_for_wh:
                col = current_wh_data_col_start
                sheet.write(current_data_row, col, line.get('available', 0),
                            red_mark if line.get('available', 0) < 0 else font_size_8);
                col += 1
                sheet.write(current_data_row, col, line.get('virtual', 0),
                            red_mark if line.get('virtual', 0) < 0 else font_size_8);
                col += 1
                sheet.write(current_data_row, col, line.get('incoming', 0),
                            red_mark if line.get('incoming', 0) < 0 else font_size_8);
                col += 1
                sheet.write(current_data_row, col, line.get('outgoing', 0),
                            red_mark if line.get('outgoing', 0) < 0 else font_size_8);
                col += 1
                sheet.merge_range(current_data_row, col, current_data_row, col + 1, line.get('net_on_hand', 0),
                                  red_mark if line.get('net_on_hand', 0) < 0 else font_size_8);
                col += 2
                sheet.merge_range(current_data_row, col, current_data_row, col + 1, line.get('stock_locations', ''),
                                  font_size_8_l);
                col += 2
                sheet.merge_range(current_data_row, col, current_data_row, col + 1, line.get('sale_value', 0),
                                  red_mark if line.get('sale_value', 0) < 0 else font_size_8);
                col += 2
                sheet.merge_range(current_data_row, col, current_data_row, col + 1, line.get('purchase_value', 0),
                                  red_mark if line.get('purchase_value', 0) < 0 else font_size_8);
                col += 2
                sheet.write(current_data_row, col, line.get('total_value', 0),
                            red_mark if line.get('total_value', 0) < 0 else font_size_8_r)
                current_data_row += 1
            current_wh_data_col_start += cols_per_warehouse

        # Set column widths
        sheet.set_column(0, 0, 10)  # SKU
        sheet.set_column(1, 1, 15)  # Part Number
        sheet.set_column(2, 4, 30)  # Name (merged)
        sheet.set_column(5, 6, 20)  # Category (merged)
        # Removed column width for 'Product Location'
        sheet.set_column(7, 7, 10)  # Cost Price - Now at column index 7

        start_wh_col = product_info_cols  # Now 8
        for _ in ware_house_names:
            sheet.set_column(start_wh_col, start_wh_col, 10)  # Available
            sheet.set_column(start_wh_col + 1, start_wh_col + 1, 10)  # Virtual
            sheet.set_column(start_wh_col + 2, start_wh_col + 2, 10)  # Incoming
            sheet.set_column(start_wh_col + 3, start_wh_col + 3, 10)  # Outgoing
            sheet.set_column(start_wh_col + 4, start_wh_col + 5, 12)  # Net on Hand
            sheet.set_column(start_wh_col + 6, start_wh_col + 7, 25)  # Stock Locations (WH)
            sheet.set_column(start_wh_col + 8, start_wh_col + 9, 12)  # Total Sold
            sheet.set_column(start_wh_col + 10, start_wh_col + 11, 12)  # Total Purchased
            sheet.set_column(start_wh_col + 12, start_wh_col + 12, 12)  # Valuation
            start_wh_col += cols_per_warehouse

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()