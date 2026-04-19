# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockCardView(models.TransientModel):
    _name = "stock.card.view"
    _description = "Stock Card View"
    _order = "date"

    date = fields.Datetime()
    product_id = fields.Many2one(comodel_name="product.product")
    product_qty = fields.Float()
    product_uom_qty = fields.Float()
    product_uom = fields.Many2one(comodel_name="uom.uom")
    reference = fields.Char()
    location_id = fields.Many2one(comodel_name="stock.location")
    location_dest_id = fields.Many2one(comodel_name="stock.location")
    is_initial = fields.Boolean()
    product_in = fields.Float()
    product_out = fields.Float()
    picking_id = fields.Many2one(comodel_name="stock.picking")

    def name_get(self):
        result = []
        for rec in self:
            name = rec.reference
            if rec.picking_id.origin:
                name = "{} ({})".format(name, rec.picking_id.origin)
            result.append((rec.id, name))
        return result


class StockCardReport(models.TransientModel):
    _name = "report.stock.card.report"
    _description = "Stock Card Report"

    # Filters fields, used for data computation
    date_from = fields.Date()
    date_to = fields.Date()
    product_ids = fields.Many2many(comodel_name="product.product")
    location_id = fields.Many2one(comodel_name="stock.location")

    # Data fields, used to browse report data
    results = fields.Many2many(
        comodel_name="stock.card.view",
        compute="_compute_results",
        help="Use compute fields, so there is nothing store in database",
    )

    def _column_exists(self, table, column):
        self.env.cr.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
            """,
            (table, column),
        )
        return bool(self.env.cr.fetchone())

    def _get_move_line_qty_column(self):
        # Try the common names in order
        for col in ("qty_done", "quantity_done", "quantity", "qty", "done_qty"):
            if self._column_exists("stock_move_line", col):
                return col
        return None

    def _compute_results(self):
        self.ensure_one()

        date_from = self.date_from or "0001-01-01"
        date_to = self.date_to or fields.Date.context_today(self)

        locations = self.env["stock.location"].search(
            [("id", "child_of", [self.location_id.id])]
        )

        loc_ids = tuple(locations.ids) or (0,)
        prod_ids = tuple(self.product_ids.ids) or (0,)

        qty_col = self._get_move_line_qty_column()
        if not qty_col:
            raise ValueError(
                "Cannot find done quantity column on stock_move_line. "
                "Tried: qty_done, quantity_done, quantity, qty, done_qty"
            )

        qty_expr = f"COALESCE(SUM(ml.{qty_col}), 0.0)"

        cr = self.env.cr
        cr.execute(
            f"""
            SELECT
                m.date,
                m.product_id,
                {qty_expr} AS product_qty,
                m.product_uom_qty,
                m.product_uom,
                m.reference,
                m.location_id,
                m.location_dest_id,
                CASE WHEN m.location_dest_id IN %s THEN {qty_expr} END AS product_in,
                CASE WHEN m.location_id IN %s THEN {qty_expr} END AS product_out,
                CASE WHEN CAST(m.date AS date) < %s THEN TRUE ELSE FALSE END AS is_initial,
                m.picking_id
            FROM stock_move m
            LEFT JOIN stock_move_line ml ON ml.move_id = m.id
            WHERE (m.location_id IN %s OR m.location_dest_id IN %s)
              AND m.state = 'done'
              AND m.product_id IN %s
              AND CAST(m.date AS date) <= %s
            GROUP BY
                m.id, m.date, m.product_id, m.product_uom_qty, m.product_uom,
                m.reference, m.location_id, m.location_dest_id, m.picking_id
            ORDER BY m.date, m.reference
            """,
            (loc_ids, loc_ids, date_from, loc_ids, loc_ids, prod_ids, date_to),
        )

        stock_card_results = cr.dictfetchall()
        self.results = [(5, 0, 0)] + [(0, 0, line) for line in stock_card_results]

    def _get_initial(self, product_line):
        product_input_qty = sum(product_line.mapped("product_in"))
        product_output_qty = sum(product_line.mapped("product_out"))
        return product_input_qty - product_output_qty

    def print_report(self, report_type="qweb"):
        self.ensure_one()
        action = (
            report_type == "xlsx"
            and self.env.ref("stock_card_report.action_stock_card_report_xlsx")
            or self.env.ref("stock_card_report.action_stock_card_report_pdf")
        )
        return action.report_action(self, config=False)

    def _get_html(self):
        result = {}
        rcontext = {}

        report = self.browse(self._context.get("active_id"))
        if report:
            rcontext["o"] = report

            html = self.env["ir.qweb"]._render(
                "stock_card_report.report_stock_card_report_html",  # QWeb template XML ID
                rcontext,
            )

            result["html"] = html

        return result

    @api.model
    def get_html(self, given_context=None):
        return self.with_context(given_context)._get_html()
