from odoo import models, fields, tools,api,_

class WeightBatchAvgGrade(models.Model):
    _name = 'weight.batch.avg.grade'
    _description = 'Batch Avg Grade Report'
    _auto = False
    _rec_name = 'lot_id'

    lot_id = fields.Many2one('stock.lot', string='Lot / Batch', readonly=True)
    total_qty = fields.Float(string='Tonnage', readonly=True)
    total_metal_content = fields.Float(string='Metal Content', readonly=True)
    avg_grade = fields.Float(string='Average Grade', digits=(16, 8), readonly=True)
    process_type = fields.Selection(
        [
            ('cic', 'CIC'),
            ('cil', 'CIL'),
        ],
        string='CIC/CIL Plant',
        readonly=True
    )


    request_month = fields.Char(string="Request Month", readonly=True)


    @api.depends('date_request')
    def _compute_request_month(self):
        for rec in self:
            if rec.date_request:
                rec.request_month = rec.date_request.strftime('%Y-%m')
            else:
                rec.request_month = False

    # def init(self):
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #     self.env.cr.execute("""
    #         CREATE OR REPLACE VIEW %s AS (
    #             SELECT
    #                 wr.lot_id AS id,
    #                 wr.lot_id,
    #                 CASE
    #                     WHEN sl.name ILIKE '%%H%%' THEN 'cic'
    #                     WHEN sl.name ILIKE '%%D%%' THEN 'cil'
    #                     ELSE NULL
    #                 END AS process_type,
    #                 SUM(wr.quantity) AS total_qty,
    #                 SUM(wr.qy_average) AS total_metal_content,
    #                 SUM(wr.qy_average) / NULLIF(SUM(wr.quantity), 0) AS avg_grade
    #             FROM weight_request wr
    #             JOIN stock_lot sl ON sl.id = wr.lot_id
    #             WHERE wr.lot_id IS NOT NULL
    #             GROUP BY wr.lot_id, sl.name
    #         )
    #     """ % self._table)

    #######################PER WEEK 
    # def init(self):
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #     self.env.cr.execute(f"""
    #         CREATE OR REPLACE VIEW {self._table} AS (
    #             SELECT
    #                 MIN(wr.id) AS id,
    #                 wr.lot_id,
    #                 TO_CHAR(DATE_TRUNC('week', wr.date_request), 'IYYY-IW') AS request_week,
    #                 CASE
    #                     WHEN sl.name ILIKE '%%H%%' THEN 'cic'
    #                     WHEN sl.name ILIKE '%%D%%' THEN 'cil'
    #                     ELSE NULL
    #                 END AS process_type,
    #                 SUM(wr.quantity) AS total_qty,
    #                 SUM(wr.qy_average) AS total_metal_content,
    #                 SUM(wr.qy_average) / NULLIF(SUM(wr.quantity), 0) AS avg_grade
    #             FROM weight_request wr
    #             JOIN stock_lot sl ON sl.id = wr.lot_id
    #             WHERE wr.lot_id IS NOT NULL
    #             GROUP BY
    #                 wr.lot_id,
    #                 sl.name,
    #                 DATE_TRUNC('week', wr.date_request)
    #         )
    #     """)


    ##################### PER MONTH
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    MIN(wr.id) AS id,
                    wr.lot_id,
                    TO_CHAR(wr.date_request, 'YYYY-MM') AS request_month,
                    CASE
                        WHEN sl.name ILIKE '%%H%%' THEN 'cic'
                        WHEN sl.name ILIKE '%%D%%' THEN 'cil'
                        ELSE NULL
                    END AS process_type,
                    SUM(wr.quantity) AS total_qty,
                    SUM(wr.qy_average) AS total_metal_content,
                    SUM(wr.qy_average) / NULLIF(SUM(wr.quantity), 0) AS avg_grade
                FROM weight_request wr
                JOIN stock_lot sl ON sl.id = wr.lot_id
                WHERE wr.lot_id IS NOT NULL
                    AND wr.state = 'done'  -- <-- Only records in Purchase Order state
                GROUP BY wr.lot_id, sl.name, TO_CHAR(wr.date_request, 'YYYY-MM')
            )
        """)