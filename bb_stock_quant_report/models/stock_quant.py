# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, modules

class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    def view_bb_reserved_quantity(self):
        sml_ids = self.env['stock.move.line'].search([
                ('product_id','=',self.product_id.id),
                ('location_id','=',self.location_id.id),
                ('lot_id','=',self.lot_id.id),
                ('state','not in',['done','cancel']),
                ('product_qty','>',0)
                ])
        return self.view_bb_reserved_quantity_sml(sml_ids)

    def view_bb_reserved_quantity_sml(self, sml_ids):
        context = {'create': False, 'edit': False}
        tree_view_id = self.env.ref('stock.view_move_line_tree').id
        form_view_id = self.env.ref('stock.view_move_line_form').id
        action = {
                'name': 'Reserved',
                # 'view_mode': 'tree',
                'res_model': 'stock.move.line',
                'views': [(tree_view_id, 'tree'),(form_view_id,'form')],
                'view_id': tree_view_id,
                'domain': [('id','in',sml_ids.ids)],
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'current'
            }
        return action

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    
    def view_bb_reserved_quantity_mw(self):
        sml_ids = self.env['stock.move.line'].search([
                ('product_id','in',self.product_variant_ids.ids),
                ('state','not in',['done','cancel']),
                ('product_qty','>',0)
                ])
        return self.env['stock.quant'].view_bb_reserved_quantity_sml(sml_ids)

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    def view_bb_reserved_quantity_mw(self):
        sml_ids = self.env['stock.move.line'].search([
                ('product_id','=',self.id),
                ('state','not in',['done','cancel']),
                ('product_qty','>',0)
                ])
        return self.env['stock.quant'].view_bb_reserved_quantity_sml(sml_ids)
        
            