from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
from itertools import groupby
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from collections import defaultdict

from odoo.tools.float_utils import float_is_zero


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    purchase_order_id = fields.Many2one(
        'purchase.order', 'Purchase Order', copy=False)
    amount_total_currency = fields.Monetary(
        'Total/Currency', compute='_compute_total_amount',
        store=True, tracking=True)
    partner_id = fields.Many2one("res.partner", "Vendor")
    company_id = fields.Many2one("res.company")

    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")

    mrp_production_ids = fields.Many2many(
        'mrp.production', string='Manufacturing order',
        copy=False, states={'done': [('readonly', True)]},
        groups='stock.group_stock_manager,purchase.group_purchase_user')
    allowed_mrp_production_ids = fields.Many2many(
        'mrp.production', compute='_compute_allowed_mrp_production_ids',
        groups='stock.group_stock_manager,purchase.group_purchase_user')

    payment_line = fields.One2many(comodel_name="account.payment", inverse_name="landed_cost_id")
    payment_state = fields.Selection(related="vendor_bill_id.payment_state"
    )



    def action_advance_payment(self):
        return {
            "name": _("Advance Payment"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "advance.payments.landed.wizard",
            "view_id": self.env.ref("material_request.advance_payments_landed_wizard_form_view").id,
            "type": "ir.actions.act_window",
            "target": "new"
        }

    @api.onchange('purchase_order_id.picking_ids')
    def update_picking(self):
        for rec in self.purchase_order_id.picking_ids:
            if rec.picking_ids in ['done', 'assigned']:
                if rec.picking_ids.picking_type_id.code == 'incoming':
                    rec.picking_ids = rec.purchase_order_id.picking_ids



    def button_validate(self):

        if not self.picking_ids:
            raise UserError(_("Please Enter The Transfers"))


        ######################landed cost####################
        if  self.purchase_order_id.ore_purchased == False:
            for rec in self.picking_ids:

                if rec.state=='assigned':
                    raise UserError(_("Please Validate The Transfer Firstly before validated landed cost"))



        # if self.purchase_order_id.ore_purchased == False:
        if not self.partner_id :
            raise UserError(_("Please write the Transporter"))

        self._check_can_validate()
        cost_without_adjusment_lines = self.filtered(lambda c: not c.valuation_adjustment_lines)
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

        for cost in self:
            cost = cost.with_company(cost.company_id)
            move = self.env['account.move']
            move_vals = {
                'journal_id': cost.account_journal_id.id,
                'date': cost.date,
                'ref': cost.name,
                'line_ids': [],
                'move_type': 'entry',
            }

            valuation_layer_ids = []
            cost_to_add_byproduct = defaultdict(lambda: 0.0)
            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                remaining_qty = sum(line.move_id.stock_valuation_layer_ids.mapped('remaining_qty'))
                linked_layer = line.move_id.stock_valuation_layer_ids[:1]
                print("#########################################", remaining_qty)

                # Prorate the value at what's still in stock
                cost_to_add = (remaining_qty / line.move_id.product_qty) * line.additional_landed_cost
                if not cost.company_id.currency_id.is_zero(cost_to_add):
                    valuation_layer = self.env['stock.valuation.layer'].create({
                        'value': cost_to_add,
                        'unit_cost': 0,
                        'quantity': 0,
                        'remaining_qty': 0,
                        'stock_valuation_layer_id': linked_layer.id,
                        'description': cost.name,
                        'stock_move_id': line.move_id.id,
                        'product_id': line.move_id.product_id.id,
                        'stock_landed_cost_id': cost.id,
                        'company_id': cost.company_id.id,
                    })
                    linked_layer.remaining_value += cost_to_add
                    valuation_layer_ids.append(valuation_layer.id)
                # Update the AVCO
                product = line.move_id.product_id
                if product.cost_method in ('average', 'last'):
                    cost_to_add_byproduct[product] += cost_to_add
                # Products with manual inventory valuation are ignored because they do not need to create journal entries.
                if product.valuation != "real_time":
                    continue
                # `remaining_qty` is negative if the move is out and delivered proudcts that were not
                # in stock.
                qty_out = 0
                if line.move_id._is_in():
                    qty_out = line.move_id.product_qty - remaining_qty
                elif line.move_id._is_out():
                    qty_out = line.move_id.product_qty
                move_vals['line_ids'] += line._create_accounting_entries(move, qty_out)

            # batch standard price computation avoid recompute quantity_svl at each iteration
            products = self.env['product.product'].browse(p.id for p in cost_to_add_byproduct.keys()).with_company(
                cost.company_id)
            for product in products:  # iterate on recordset to prefetch efficiently quantity_svl
                if not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):

                    ######################landed cost ######3333333333333
                    if product.categ_id.property_cost_method == 'last':
                        for line in cost.valuation_adjustment_lines:
                            if line.product_id.id == product.id:
                                product.with_company(cost.company_id).sudo().with_context(
                                    disable_auto_svl=True).standard_price += cost_to_add_byproduct[
                                                                                 product] / line.quantity
                    else:
                        product.with_company(cost.company_id).sudo().with_context(
                            disable_auto_svl=True).standard_price += cost_to_add_byproduct[
                                                                         product] / product.quantity_svl

            move_vals['stock_valuation_layer_ids'] = [(6, None, valuation_layer_ids)]
            # We will only create the accounting entry when there are defined lines (the lines will be those linked to products of real_time valuation category).
            cost_vals = {'state': 'done'}
            if move_vals.get("line_ids"):
                move = move.sudo().create(move_vals)
                cost_vals.update({'account_move_id': move.id})
            cost.write(cost_vals)
            if cost.account_move_id:
                move.sudo()._post()

            if cost.vendor_bill_id and cost.vendor_bill_id.state == 'posted' and cost.company_id.anglo_saxon_accounting:
                all_amls = cost.vendor_bill_id.line_ids | cost.account_move_id.line_ids
                for product in cost.cost_lines.product_id:
                    accounts = product.product_tmpl_id.get_product_accounts()
                    input_account = accounts['stock_valuation']
                    all_amls.filtered(lambda aml: aml.account_id == input_account and not aml.reconciled).reconcile()

        return True

    def get_valuation_lines(self):

        self.ensure_one()
        lines = []

        for move in self._get_targeted_move_ids():
            # it doesn't make sense to make a landed cost for a product that isn't set as being valuated in real time at real cost
            if move.product_id.cost_method not in (
            'fifo', 'average', 'last') or move.state == 'cancel' or not move.product_qty:
                continue
            vals = {
                'product_id': move.product_id.id,
                'move_id': move.id,
                'quantity': move.product_qty,
                'former_cost': sum(move.stock_valuation_layer_ids.mapped('value')),
                'weight': move.product_id.weight * move.product_qty,
                'volume': move.product_id.volume * move.product_qty
            }
            lines.append(vals)

            print("#############################333", lines)

        if not lines:
            target_model_descriptions = dict(self._fields['target_model']._description_selection(self.env))
            raise UserError(
                _("You cannot apply landed costs on the chosen %s(s). Landed costs can only be applied for products with FIFO or average costing method.",
                  target_model_descriptions[self.target_model]))
        # super(StockLandedCost, self).get_valuation_lines()

        return lines

    def compute_landed_cost(self):
        AdjustementLines = self.env['stock.valuation.adjustment.lines']
        AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()

        towrite_dict = {}
        for cost in self.filtered(lambda cost: cost._get_targeted_move_ids()):
            rounding = cost.currency_id.rounding
            total_qty = 0.0
            total_cost = 0.0
            total_weight = 0.0
            total_volume = 0.0
            total_line = 0.0
            all_val_line_values = cost.get_valuation_lines()
            for val_line_values in all_val_line_values:
                for cost_line in cost.cost_lines:
                    val_line_values.update({'cost_id': cost.id, 'cost_line_id': cost_line.id})
                    self.env['stock.valuation.adjustment.lines'].create(val_line_values)
                total_qty += val_line_values.get('quantity', 0.0)
                total_weight += val_line_values.get('weight', 0.0)
                total_volume += val_line_values.get('volume', 0.0)

                former_cost = val_line_values.get('former_cost', 0.0)
                # round this because former_cost on the valuation lines is also rounded
                total_cost += cost.currency_id.round(former_cost)

                total_line += 1

            for line in cost.cost_lines:
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines:
                    value = 0.0
                    if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                        if line.split_method == 'by_quantity' and total_qty:
                            per_unit = (line.price_unit / total_qty)
                            value = valuation.quantity * per_unit
                        elif line.split_method == 'by_weight' and total_weight:
                            per_unit = (line.price_unit / total_weight)
                            value = valuation.weight * per_unit
                        elif line.split_method == 'by_volume' and total_volume:
                            per_unit = (line.price_unit / total_volume)
                            value = valuation.volume * per_unit
                        elif line.split_method == 'equal':
                            value = (line.price_unit / total_line)
                        elif line.split_method == 'by_current_cost_price' and total_cost:
                            per_unit = (line.price_unit / total_cost)
                            value = valuation.former_cost * per_unit
                        else:
                            value = (line.price_unit / total_line)

                        if rounding:
                            value = tools.float_round(value, precision_rounding=rounding, rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value
        for key, value in towrite_dict.items():
            AdjustementLines.browse(key).write({'additional_landed_cost': value})
        return True

    def _prepare_invoice(self):
        """Prepare the dict of values to create the new invoice for a purchase order.
        """
        self.ensure_one()
        move_type = self._context.get('default_move_type', 'in_invoice')
        # journal = self.env['account.move'].with_context(default_move_type=move_type)._get_default_journal()
        journal = self.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if not journal:
            raise UserError(_('Please define an accounting purchase journal for the company %s (%s).') % (
            self.company_id.name, self.company_id.id))

        partner_invoice_id = self.partner_id.address_get(['invoice'])['invoice']
        partner_bank_id = self.partner_id.bank_ids.filtered_domain(
            ['|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)])[:1]
        invoice_vals = {
            'ref': '',
            'move_type': 'in_invoice',
            'currency_id': self.currency_id.id,
            # 'invoice_user_id': self.user_id and self.user_id.id or self.env.user.id,
            'partner_id': partner_invoice_id,
            # 'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(partner_invoice_id)).id,
            'payment_reference': '',
            'partner_bank_id': partner_bank_id.id,
            'invoice_origin': self.name,
            # 'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }
        return invoice_vals

    def create_transporter_invoices(self):
        """Create the invoice associated to the PO."""
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')



        # 1) Prepare invoice values and clean-up the section lines
        invoice_vals_list = []
        for order in self:
            order = order.with_company(order.company_id)

            # Invoice values
            invoice_vals = order._prepare_invoice()

            # Invoice line values
            for line in order.cost_lines:
                line_vals = line._prepare_account_move_line()

                # Ensure all relational fields are IDs
                if isinstance(line_vals.get('account_id'), models.BaseModel):
                    line_vals['account_id'] = line_vals['account_id'].id
                # line_vals['account_id'] = 3278
                # analytic_account = line.cost_id.weight_id.analytic_account_id
                analytic_account = line.cost_id.analytic_account_id
                if analytic_account:
                    line_vals['analytic_distribution'] = {analytic_account.id: 100.0}
                invoice_vals['invoice_line_ids'].append((0, 0, line_vals))

            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise UserError(
                _('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

        # 2) Group by (company_id, partner_id, currency_id) for batch creation
        new_invoice_vals_list = []
        for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (
                x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
            origins = set()
            payment_refs = set()
            refs = set()
            ref_invoice_vals = None

            for invoice_vals in invoices:
                if not ref_invoice_vals:
                    ref_invoice_vals = invoice_vals
                else:
                    ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                origins.add(invoice_vals['invoice_origin'])
                payment_refs.add(invoice_vals['payment_reference'])
                refs.add(invoice_vals['ref'])
            temp_origins = False
            if origins:
                temp_origins = ', '.join(origins)
            ref_invoice_vals.update({
                'ref': ', '.join(refs)[:2000],
                'invoice_origin': temp_origins,
                'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
            })
            new_invoice_vals_list.append(ref_invoice_vals)
        invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals['company_id']).create(vals)

        # 4) Convert negative moves to refunds
        for move in moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0):
            move.button_draft()
            move.write({'move_type': 'in_refund'})
            move._recompute_dynamic_lines(recompute_all_taxes=True)
            move.action_post()

        # Set vendor bill and landed cost references
        self.vendor_bill_id = moves
        moves.landed_cost_id = self.id

        return self.action_view_invoice(moves)
    def action_view_invoice(self, invoices=False):
        """This function returns an action that display existing vendor bills of
        given purchase order ids. When only one found, show the vendor bill
        immediately.
        """
        if not invoices:
            # Invoice_ids may be filtered depending on the user. To ensure we get all
            # invoices related to the purchase order, we read them in sudo to fill the
            # cache.
            self.sudo()._read(['invoice_ids'])
            invoices = self.invoice_ids

        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        # choose the view_mode accordingly
        if len(invoices) > 1:
            result['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            res = self.env.ref('account.view_move_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = invoices.id
        else:
            result = {'type': 'ir.actions.act_window_close'}

        return result


    @api.depends('cost_lines.price_unit')
    def _compute_total_amount(self):
        res = super(StockLandedCost, self)._compute_total_amount()
        for cost in self:
            cost.amount_total_currency = sum(line.currency_price_unit for line in cost.cost_lines)



class StockLandedCostLines(models.Model):
    _inherit = 'stock.landed.cost.lines'
    product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=False, default=1.0)

    def _prepare_account_move_line(self, move=False):
        self.ensure_one()

        accounts = self.product_id.product_tmpl_id._get_product_accounts()
        aml_currency = move and move.currency_id or self.currency_id
        date = move and move.date or fields.Date.today()
        res = {
            'name': '%s: %s' % (self.cost_id.name, self.name),
            'product_id': self.product_id.id,
            'product_uom_id': self.product_id.uom_id.id,
            'quantity': self.product_qty,
            'is_landed_costs_line': True,
            'price_unit': (self.currency_id._convert(self.currency_price_unit, aml_currency, self.cost_id.company_id,
                                                     date, round=False)) / self.product_qty,
            'account_id': accounts['stock_valuation'],
        }
        if self.cost_id.purchase_order_id.weight_request_id.analytic_account_id:
                res['analytic_distribution'] = {self.cost_id.purchase_order_id.weight_request_id.analytic_account_id.id: 100}
        if not move:
            return res

        if self.currency_id == move.company_id.currency_id:
            currency = False
        else:
            currency = move.currency_id

        res.update({
            'move_id': move.id,
            'currency_id': currency and currency.id or False,
            'date_maturity': move.invoice_date_due,
            'partner_id': move.partner_id.id,
            'move_type': 'in_invoice',
            'invoice_date': move.invoice_date_due,
        })
        return res


class StockWharehouse(models.Model):
    _inherit = "stock.warehouse"

    issuance_location = fields.Many2one('stock.location', "Consumption Location", copy=True)


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    issued = fields.Boolean(string='Issuance', default=False, store=True)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    batch_no = fields.Char("Batch Number")
    average = fields.Float("Average")


class StockMove(models.Model):
    _inherit = "stock.move"

    issuance_line_id = fields.Boolean()
    category_id = fields.Many2one("product.category", string="Product Category")
    # unit_cost=fields.Monetary(related="stock_valuation_layer_ids.unit_cost")
    issuance_request_id = fields.Many2one('issuance.request', 'Issuance Request')
    # partner_id = fields.Many2one(related="picking_id.partner_id", string="Partner")
    batch_no = fields.Char("Batch Number")
    average = fields.Float("Average")

    property_account_payable_id = fields.Many2one('account.account',
                                                  related="picking_id.partner_id.property_account_payable_id",
                                                  company_dependent=True,
                                                  string="Account Payable",
                                                  domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
                                                  help="This account will be used instead of the default one as the payable account for the current partner",
                                                  required=True)

    ####################################override function to  create journal entries with receviable (fuel issuance external)
    ##############################ekhlas code #####################################################################
    def _get_accounting_data_for_valuation(self):
        """ Return the accounts and journal to use to post Journal Entries for
        the real-time valuation of the quant. """
        self.ensure_one()

        # acc_dest=None
        self = self.with_company(self.company_id)
        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()

        acc_src = self._get_src_account(accounts_data)
        if self.picking_type_id.issued == True and self.partner_id:
            acc_dest = self.property_account_payable_id.id
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



    #################the function skip 3/06
    # def _action_done(self, cancel_backorder=False):
    #     res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)

    #     for rec in self:
    #         rec.category_id = rec.product_id.categ_id
    #         stock_valuation_layers = self.env['stock.valuation.layer'].search([('stock_move_id', '=', rec.id)])
    #         for line in stock_valuation_layers:
    #             if line.product_id.categ_id.property_cost_method == 'last':
    #                 line.remaining_qty = line.quantity

    #                 # print (">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",line.remaining_qty,line.quantity)
    #     return res









    def _create_account_move_line2(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id,
                                   cost):
        self.ensure_one()

        # stock_valuation_layer_id = self.env['stock.valuation.layer'].sudo().search([('stock_move_id','=',move.id)])

        # if stock_valuation_layer_id:
        #     for rec in stock_valuation_layer_id:
        #         if rec.unit_cost==0:

        AccountMove = self.env['account.move'].with_context(default_journal_id=journal_id)

        move_lines = self._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id, description)
        if move_lines:
            date = self._context.get('force_period_date', fields.Date.context_today(self))
            new_account_move = AccountMove.sudo().create({
                'journal_id': journal_id,
                'line_ids': move_lines,
                'date': date,
                'ref': description,
                'stock_move_id': self.id,
                'stock_valuation_layer_ids': [(6, None, [svl_id])],
                'move_type': 'entry',
            })
            new_account_move._post()





class AccountMoveLineLine(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.move.line'

    equipment_id = fields.Many2one(comodel_name="maintenance.equipment", string="Equipment", required=False, )


class AccountMove(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.move'

    picking_id = fields.Many2one('stock.picking')

    landed_cost_id = fields.Many2one("stock.landed.cost", "Landed Cost")
    landed_cost_po_id = fields.Many2one("purchase.order", string="Purchase Order",
                                        related="landed_cost_id.purchase_order_id")


class StockPicking(models.Model):
    _inherit = "stock.picking"

    request_id = fields.Many2one('material.request', 'Material Request')
    issuance_request_id = fields.Many2one('issuance.request', 'Issuance Request')
    store_invoice = fields.Many2one(comodel_name='account.move')

    flag = fields.Boolean(default=False)

    def button_validate(self):
        landed_costs = self.env['stock.landed.cost'].search([('picking_ids', 'in', self.id)])

        res = super(StockPicking, self).button_validate()
        # for rec in landed_costs:
        #     if rec:
        #         if rec.state == 'draft' and self.state == 'done':
        #             rec.button_validate()

        return res











