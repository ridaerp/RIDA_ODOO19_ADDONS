from odoo import models, fields, api, _

class WorkSite(models.Model):
    _name = 'work.site'
    _description = 'Work Site'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Work Site', tracking=True)