# Copyright 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# Copyright 2017-2019 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.tools import SQL

class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    discount = fields.Float(
        string="Discount (%)",
        digits="Discount",
        group_operator="avg",
    )

    def _select(self):
        res = super()._select()
        return SQL(
            "%s, %s AS price_unit, l.discount AS discount",
            res,
            self._get_discounted_price_unit_exp(),
        )

    def _group_by(self):
        res = super()._group_by()
        return SQL("%s, l.discount", res)

    def _get_discounted_price_unit_exp(self):
        return SQL(
            "(1.0 - COALESCE(l.discount, 0.0) / 100.0) * l.price_unit"
        )