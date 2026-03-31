from odoo import models, fields

class StockLocation(models.Model):
    _inherit = 'stock.location'

    exclude_from_onhand = fields.Boolean("Exclude from On Hand", default=False)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    exclude_from_onhand_calc = fields.Boolean(string="Do Not Apply Excluded Locations",
                                              help="If enabled, this product will NOT be affected by excluded location calculations.",
                                              default=False
                                              )

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        res = super()._compute_quantities_dict(lot_id, owner_id, package_id, from_date, to_date)

        excluded_locations = self.env['stock.location'].search([('exclude_from_onhand', '=', True)])
        if excluded_locations:
            for product_id, values in res.items():
                product = self.browse(product_id)
                if not product.exclude_from_onhand_calc:
                    excluded_qty = sum(self.env['stock.quant'].search([
                        ('product_id', '=', product_id),
                        ('location_id', 'in', excluded_locations.ids)
                    ]).mapped('quantity'))
                    values['qty_available'] -= excluded_qty
                    values['free_qty'] -= excluded_qty
                    values['virtual_available'] -= excluded_qty
        return res