from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)

class AccountAsset(models.Model):
    _inherit = 'account.asset'

    asset_code = fields.Char('Asset Code')
    description = fields.Text('Asset Description')
    asset_tags_ids = fields.Many2many(
        'asset.tag', 
        string='Asset Tags',
        help='Tags to categorize the asset'
    )

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts',
        compute='_compute_analytic_accounts',
        search='_search_analytic_accounts',  # 🔹 مهم للبحث
        store=False  # يمكن جعله True إذا أردت تخزينه
    )

    @api.depends('analytic_distribution')
    def _compute_analytic_accounts(self):
        for rec in self:
            account_ids = []
            if rec.analytic_distribution:
                try:
                    distribution = rec.analytic_distribution
                    if isinstance(distribution, str):
                        distribution = json.loads(distribution)

                    account_ids = [int(k) for k in distribution.keys() if k.isdigit()]
                except Exception as e:
                    _logger.error("Error computing analytic accounts: %s", e)
                    account_ids = []

            # استخدام set لتجنب التكرار
            rec.analytic_account_ids = [(6, 0, list(set(account_ids)))]

    def _search_analytic_accounts(self, operator, value):
        """تمكين البحث في الحقل المحسوب"""
        # يمكنك تنفيذ منطق البحث المناسب هنا
        return []

class AssetTag(models.Model):
    _name = 'asset.tag'
    _description = 'Asset Tag'

    name = fields.Char(string='Tag Name', required=True)
    asset_ids = fields.Many2many(
        'account.asset', 
        string='Assets',
        help='Assets associated with this tag'
    )