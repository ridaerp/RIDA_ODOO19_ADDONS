from odoo import models, fields , api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    automatuact = fields.Boolean(string='Auto MRP Daily')
    is_hidden_from_limited_group = fields.Boolean(string='Hide from Limited Group')
    code = fields.Char(string='Code')
    # gold_scrap = fields.Boolean("Gold Scrap")



class BatchPond(models.Model):
    _inherit = 'stock.lot'

    code = fields.Char(string='Code')
    pond_ids = fields.One2many('pond.management', 'batch_id', string='Ponds')
    pump_id = fields.Many2one('pump.management', string='Pump')

    # @api.model
    # def create(self, vals):
    #     if vals.get('product_id'):
    #         product = self.env['product.product'].browse(vals['product_id'])
    #         if product.default_code == 'Gold':
    #             vals['name'] = self.env['ir.sequence'].next_by_code('gold_21_serial') or '/'
    #     return super().create(vals)



class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    quantity = fields.Float(string="Quantity Before Scrap")
    actual_gold_percentage = fields.Float(string='Actual Gold %',)
    net_gold_weight = fields.Float(string='Net Gold Weight', compute='_compute_gold_details', store=True)
    scrap_qty_ca = fields.Float(string='Gold Scrap Qty', compute='_compute_gold_details', store=True)

    @api.onchange('production_id')
    def _onchange_production_id(self):
        if self.production_id:
            if self.production_id.product_id.x_studio_gold_scrap is True:
                self.product_id = self.production_id.product_id.id
                self.quantity = self.production_id.qty_producing
                self.lot_id = self.production_id.lot_producing_id
            # else:
            #     return super()._onchange_production_id()

    @api.depends('quantity', 'actual_gold_percentage')
    def _compute_gold_details(self):
        for rec in self:
            if rec.quantity and rec.actual_gold_percentage:
                percent = rec.actual_gold_percentage / 100.0
                net_weight = rec.quantity * percent
                rec.net_gold_weight = net_weight
                rec.scrap_qty_ca = rec.quantity - net_weight
                rec.scrap_qty = rec.scrap_qty_ca
