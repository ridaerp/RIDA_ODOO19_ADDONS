from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.model
    def default_get(self, fields):
        # 1. محاولة جلب المعرف من السياق الافتراضي
        active_id = self.env.context.get('active_id')

        # 2. إذا فشل، نحاول جلبه من الرابط (URL) مباشرة
        if not active_id and self.env.context.get('params'):
            active_id = self.env.context.get('params').get('id')

        # 3. تمرير المعرف الصحيح للدالة الأصلية
        res = super(StockReturnPicking, self.with_context(active_id=active_id)).default_get(fields)

        # 4. تأكيد إضافي: إذا ظلت السطور فارغة، نقوم بتعبئتها يدوياً
        if active_id and not res.get('product_return_moves'):
            picking_id = self.env['stock.picking'].browse(active_id)
            if picking_id:
                return_moves = []
                for move in picking_id.move_ids.filtered(lambda m: m.state == 'done'):
                    return_moves.append((0, 0, {
                        'product_id': move.product_id.id,
                        'quantity': move.quantity,
                        'move_id': move.id,
                        'uom_id': move.product_uom.id,
                    }))
                res.update({'product_return_moves': return_moves})

        return res


class RidaStockPiking(models.Model):
    _inherit = 'stock.picking'

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    inspection_date = fields.Date(string='Date Of Inspection', default=datetime.today())
    security_number = fields.Integer(string='Security Number',copy=False)
    security_number_issuance = fields.Integer(related='issuance_request_id.security_number',copy=False)
    inspector = fields.Many2one(comodel_name='res.partner', string='inspector')
    take_action = fields.Selection(string='Action To Be Taken',
                                   selection=[('repair', 'Repair'), ('return_to_supplier', 'Return To Supplier'), ])
    driver_name = fields.Char(string='Driver Name')
    driver_mobile = fields.Char(string='Driver Mobile')
    truk_no = fields.Char(string='Truk number')
    truk_cap = fields.Char(string='Truk Capacity')
    return_state = fields.Selection(string='Returing Status', selection=[('supervice_manager', 'Supervice Manager'), ('warehouse_manager', 'Warehouse Manager'), ('user_department_manager', 'User Department Manager'), ( 'supply_chain_manager', 'Supply Chain Manager')], default='supervice_manager')
    requirements_sat = fields.Boolean(string='Technical Evaluation Check', default=False, required=True, store=True)
    emp = fields.Many2one('hr.employee', default=lambda self: self.env.user.employee_id, store=True, readonly=True)
    emp_type = fields.Selection(string='Employee type', related="emp.rida_employee_type")
    receipt_id = fields.Many2one('hr.employee', string="Receipt By")

    origin_id=fields.Many2one("stock.picking","Source OUT ",readonly=True)

    def button_validate(self):
        """Creating the internal transfer if it is not created from another picking"""
        res = super(RidaStockPiking, self).button_validate()

        ############################## Update MEDICARE Products ################################

        if self.picking_type_id.code == 'outgoing' and self.issuance_request_id :
            if self.issuance_request_id.security_number:
                if not self.receipt_id:
                    raise UserError('Please fill the Receipt By !!!')
                if self.issuance_request_id.security_number != self.security_number:
                    raise UserError(f'Check The Receipt Confirmation Number Of Issuance Request >> {self.issuance_request_id.name}')

        #############################################################################################

        if  self.purchase_id.weight_request_id:
            landed_cost = self.env['stock.landed.cost'].search([
                ('weight_id', '=', self.purchase_id.weight_request_id.id),
                ('state','=','draft')
            ], limit=1)
            if landed_cost:
                landed_cost.write({
                    'picking_ids': [(4, self.id)]
                })
                landed_cost.sudo().button_validate()
            #############################inspection code section###########################################################
        if self.picking_type_id.code == 'incoming' and self.purchase_id:
            env = self.env(user=1)
            if not self.purchase_id.ore_purchased and self.picking_type_id.code == 'incoming':
                if self.picking_type_id.code == 'incoming' and self.purchase_id:
                    env = self.env(user=1)
                    create_date = self.create_date.date()
                    desired_date = datetime(2025, 1, 29).date()                ############################inspection code section###########################################################
                    if not create_date < desired_date:
                        material_insepection_ids = env['material.inspection'].search(
                            [('purchase_id', '=', self.purchase_id.id)], order='id desc',
                            limit=1)
                        if material_insepection_ids and material_insepection_ids.state != 'closed':
                            raise UserError(
                                f'The Material Inspection Must be Closed First >> {material_insepection_ids.name}')
                        ########## Check Quantity When Validate

                        for rec in material_insepection_ids.inspection_ids:
                            for line in self.move_ids:
                                if rec.product_id.id == line.product_id.product_tmpl_id.id:
                                    if float(format(line.quantity, ".2f")) != float(format(rec.qty_accepted, ".2f")):
                                        raise UserError(
                                            f'The Accepted Qty For Product {line.product_id.product_tmpl_id.name} [ {rec.qty_accepted} ] in >> {material_insepection_ids.name}')

        self._update_sale_order_delivered_qty(self)

        return res

    ########update dropshipping####################################### 
    @api.model
    def _update_sale_order_delivered_qty(self, picking):
        # Loop through each move in the stock picking to update the sales order delivered qty
        for move in picking.move_ids:
            if move.purchase_line_id:
                purchase_order_line = move.purchase_line_id


                sale_order = self.env['sale.order'].search([
                    ('origin', '=', move.origin)] ,limit=1)

                self.sale_id=sale_order.id
                # self.group_id=sale_order.id

                # print ("#############################",purchase_order_line)
                sale_order_line = self.env['sale.order.line'].search([
                    ('product_id', '=', purchase_order_line.product_id.id),
                    ('order_id.state', 'in', ['sale', 'done'])
                ], limit=1)


                # if sale_order_line:
                #     # Update the delivered quantity in the sales order
                #     sale_order_line.qty_delivered += move.product_uom_qty




    @api.constrains('requirements_sat')
    def requirements_satisfaction_chick(self):
        for rec in self:
            if rec.requirements_sat != True and rec.state == 'assigned' and rec.picking_type_id.issued == False:
                raise ValidationError(_("You Must Confirem Technical Evaluation Check First"))

    def button_supervice_manager_approve(self):
        for rec in self:
            rec.write({'return_state': 'warehouse_manager'})

    def button_warehouse_manager_approve(self):
        for rec in self:
            rec.write({'return_state': 'user_department_manager'})

    def button_user_department_manager_approve(self):
        for rec in self:
            rec.write({'return_state': 'supply_chain_manager'})
    # def button_supply_chain_manager_approve(self):

    # #########################ekhlas code###############
    # ################function to update in no entires in finance

class RidaStockPikingBatch(models.Model):
    _inherit = 'stock.picking.batch'
    inspector = fields.Many2one(comodel_name='res.partner', string='inspector')
    driver_name = fields.Char(string='Driver Name')
    driver_mobile = fields.Char(string='Driver Mobile')
    truk_no = fields.Char(string='Truk number')
    truk_cap = fields.Char(string='Truk Capacity')


class StockMoveInherit(models.Model):
    _inherit = 'stock.move'

    ########################this function to create stock in based on out to update stock valuation layer and create jounrnal entries in finance same as stock out .
    # def _action_done(self, cancel_backorder=False):

    #     res = super(StockMoveInherit, self)._action_done()
    #     valued_moves = {valued_type: self.env['stock.move'] for valued_type in self._get_valued_types()}
    #     for rec in self:
    #         in_stock_valuation_layers = self.env['stock.valuation.layer'].sudo().search(
    #             [('stock_move_id', '=', rec.id)])

    #         if rec.picking_id.origin_id:
    #             for out in rec.picking_id.origin_id:
    #                 for out_line in out.move_lines:
    #                     out_stock_valuation_layers = self.env['stock.valuation.layer'].sudo().search(
    #                         [('stock_move_id', '=', out_line.id)])

    #                 for out_line in out_stock_valuation_layers:
    #                     for in_line in in_stock_valuation_layers:
    #                         in_line.write({
    #                             'unit_cost': out_line.unit_cost,
    #                             'value': out_line.value,
    #                         })


    #             for svl in in_stock_valuation_layers:
    #                 if not svl.product_id.valuation == 'real_time':
    #                     continue
    #                 if svl.currency_id.is_zero(svl.value):
    #                     continue
    #                 if not svl.account_move_id:
    #                     svl.stock_move_id._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)

    #                 in_stock_valuation_layers._check_company()

    #                 # For every in move, run the vacuum for the linked product.
    #                 products_to_vacuum = valued_moves['in'].mapped('product_id')
    #                 company = valued_moves['in'].mapped('company_id') and valued_moves['in'].mapped('company_id')[
    #                     0] or self.env.company
    #                 for product_to_vacuum in products_to_vacuum:
    #                     product_to_vacuum._run_fifo_vacuum(company)

    ####################################override function to  create journal entries with receviable (fuel issuance external)
    ##############################ekhlas code #####################################################################

    ########################## the function to update journal entries related to stock


    def _get_accounting_data_for_valuation(self):
        """ Return the accounts and journal to use to post Journal Entries for
        the real-time valuation of the quant. """
        self.ensure_one()
        # acc_dest=None
        self = self.with_company(self.company_id)

        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()

        # old code  ####################################
        # acc_src = self._get_src_account(accounts_data)
        ######################intercompany Transaction between rida and umdurman internal transfer between warehouses
        if self.picking_id.origin_id and self.partner_id:
            acc_src = self.partner_id.property_account_payable_id.id
        else:
            acc_src = self._get_src_account(accounts_data)

        if self.picking_type_id.issued == True and self.partner_id:
            acc_dest = self.partner_id.property_account_payable_id.id


        elif self.picking_type_id.issued == True and not self.partner_id:
            acc_dest = self.product_id.categ_id.property_account_expense_categ_id.id

        else:
            acc_dest = self._get_dest_account(accounts_data)

        acc_valuation = accounts_data.get('stock_valuation', False)
        if acc_valuation:
            acc_valuation = acc_valuation.id
        if not accounts_data.get('stock_journal', False):
            raise UserError(
                _('You don\'t have any stock journal defined on your product category, check if you have installed a chart of accounts.'))
        if not acc_src:
            raise UserError(
                _('Cannot find a stock input account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (
                    self.product_id.display_name))
        if not acc_dest:
            raise UserError(
                _('Cannot find a stock output account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (
                    self.product_id.display_name))
        if not acc_valuation:
            raise UserError(
                _('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
        journal_id = accounts_data['stock_journal'].id
        return journal_id, acc_src, acc_dest, acc_valuation
