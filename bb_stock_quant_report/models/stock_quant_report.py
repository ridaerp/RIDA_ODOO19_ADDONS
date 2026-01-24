# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools

class StockQuantReport(models.Model):
    _name = "stock.quant.report"
    _description = "Stock quant report bb"
    _auto = False
    
    qaunt_id = fields.Many2one('stock.quant', 'Quant',readonly=True)
    product_id = fields.Many2one('product.product', 'Product',readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product template', readonly=True)
    categ_id = fields.Many2one('product.category', 'Category', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', 'Product uom', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    location_id = fields.Many2one('stock.location', 'Location', readonly=True)
    lot_id = fields.Many2one('stock.lot', 'Lot', readonly=True)
    quantity = fields.Float('On hand', readonly=True, digits='Product Unit of Measure')
    reserved_quantity = fields.Float('Reserved', readonly=True, digits='Product Unit of Measure')
    forecast_quantity = fields.Float('Future On hand', readonly=True, digits='Product Unit of Measure')
    tracking = fields.Char(string="Tracking", readonly=True)
    barcode = fields.Char('Barcode', readonly=True)
    default_code = fields.Char('Code', readonly=True)
    

    # currency_id = fields.Many2one(related='product_id.currency_id', groups='stock.group_stock_manager')
    value = fields.Float(string='Unit cost', groups='stock.group_stock_manager', group_operator='avg')
    value_sum = fields.Float(string='Total cost', groups='stock.group_stock_manager')

    zarah_negj_price = fields.Float(string=u'Sale unit price', groups='stock.group_stock_manager')
    zarah_niit_price = fields.Float(string=u'Total sale price', groups='stock.group_stock_manager')
    bohir_ashig = fields.Float(string=u'Gross profit', groups='stock.group_stock_manager')

    def _select(self):
        return """
            SELECT
                sq.id as id,
                sq.id as qaunt_id,
                sq.product_id,
                pp.product_tmpl_id,
                pt.uom_id as product_uom_id,
                sq.company_id,
                sq.location_id,
                sq.lot_id,
                sq.quantity,
                sq.reserved_quantity,
                sq.quantity-sq.reserved_quantity as forecast_quantity,
                pt.tracking,
                pp.barcode,
                pp.default_code,
                pt.categ_id,
                ip.value_float as value
                ,sq.quantity*ip.value_float as value_sum
                ,pt.list_price as zarah_negj_price
                ,sq.quantity*pt.list_price as zarah_niit_price
                ,(sq.quantity*pt.list_price)-(sq.quantity*ip.value_float) as bohir_ashig
        """

    def _from(self):
        return """
            FROM stock_quant AS sq
            LEFT JOIN product_product pp ON (pp.id=sq.product_id)
            LEFT JOIN product_template pt ON (pp.product_tmpl_id=pt.id)
            LEFT JOIN stock_location sl ON (sl.id=sq.location_id)
            LEFT JOIN ir_property as ip on (ip.res_id = 'product.product,'||sq.product_id and ip.name = 'standard_price' and sq.company_id=ip.company_id)
        """

    def _group_by(self):
        return """
            
        """

    def _having(self):
        return """
           
        """

    def _where(self):
        return """"""

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                %s
                %s
                %s
                %s
                %s
            )
        """ % (self._table, self._select(), self._from(), self._where(), self._group_by(),self._having())
        )

    def view_bb_reserved_quantity(self):
        sml_ids = self.env['stock.move.line'].search([
                ('product_id','=',self.product_id.id),
                ('location_id','=',self.location_id.id),
                ('lot_id','=',self.lot_id.id),
                ('state','not in',['done','cancel']),
                ('product_qty','>',0)
                ])
        return self.env['stock.quant'].view_bb_reserved_quantity_sml(sml_ids)