# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import float_compare



class ScrapStock(models.Model):
    _inherit = 'stock.scrap'

    
    state = fields.Selection(string='Status', default='draft' ,selection=[('draft', 'Draft'), ('site_manager', 'Operation Director  approval'),('ccso_approval', 'COO Approval'),('done', 'Validate')])

    
    def submit(self): 
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        available_qty = sum(self.env['stock.quant']._gather(self.product_id,
                                                            self.location_id,
                                                            self.lot_id,
                                                            self.package_id,
                                                            self.owner_id,
                                                            strict=True).mapped('quantity'))
        scrap_qty = self.product_uom_id._compute_quantity(self.scrap_qty, self.product_id.uom_id)
        scrap_qty = self.product_uom_id._compute_quantity(self.scrap_qty, self.product_id.uom_id)
        if float_compare(available_qty, scrap_qty, precision_digits=precision) <= 0:
            ctx = dict(self.env.context)
            ctx.update({
                'default_product_id': self.product_id.id,
                'default_location_id': self.location_id.id,
                'default_scrap_id': self.id,
                'default_quantity': scrap_qty,
                'default_product_uom_name': self.product_id.uom_name
            })
            return {
                'name': self.product_id.display_name + _(': Insufficient Quantity To Scrap'),
                'view_mode': 'form',
                'res_model': 'stock.warn.insufficient.qty.scrap',
                'view_id': self.env.ref('stock.stock_warn_insufficient_qty_scrap_form_view').id,
                'type': 'ir.actions.act_window',
                'context': ctx,
                'target': 'new'
            } 
        self.write({                
        'state': 'site_manager'        })
        

    def site_manager_approval(self):  
        self.write({                
        'state': 'ccso_approval'        })
       

