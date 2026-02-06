# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
# from odoo.tools import float_compare
from odoo.exceptions import UserError


# class StockRequestCount(models.TransientModel):
#     _inherit = 'stock.request.count'
    

#     # def _get_values_to_write(self):
#     #     # Get original Odoo values
#     #     values = super()._get_values_to_write()

#     #     # Enforce state reset
#     #     values['state'] = 'draft'

#     #     # Keep inventory date (optional if already set by Odoo)
#     #     values['inventory_date'] = self.inventory_date

#     #     # Set user correctly (NO comma)
#     #     if self.user_id:
#     #         values['user_id'] = self.user_id.id

#     #     return values






class AdjustmentStock(models.Model):
    _inherit = 'stock.quant'

    note = fields.Text(string='Note')

    # state = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('warehouse_confirmed', 'Warehouse Manager'),
    #     ('supplychain_approved', 'Supply Chain Director'),
    #     ('ccso_approval', 'COO'),
    #     ('applied' , 'Applied')

    # ], default='draft', string="Status", tracking=True)


    # def submit(self):
    #     for rec in self:
    #         rec.write({
    #             'state': 'warehouse_confirmed'
    #         })


    # def warehouse_manager_approval(self):
    #     if self.filtered(lambda l: not l.state) = warehouse_confirmed
    #         raise UserError("Only Warehouse Approval Can Approve")
    #     self.write({'state': 'supplychain_approved'})

    # def warehouse_manager_approval(self):
    #     # Check that ALL records are in warehouse_confirmed
    #     invalid = self.filtered(lambda l: l.state != 'warehouse_confirmed')
    #     if invalid:
    #         raise UserError(_("Only Warehouse Confirmed records can be approved."))

    #     self.write({'state': 'supplychain_approved'})




    # def supplychain_director_approval(self):
    #     self.state = 'ccso_approval'




    # def action_apply_inventory(self):
    #     # for rec in self:
    #     #     if rec.state!='ccso_approval':
    #     #         raise UserError("Only CCSO Approval Can Apply")

    #     self.write({'state': 'applied'})

    #     return super().action_apply_inventory()






