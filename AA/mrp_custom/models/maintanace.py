from odoo import models, fields

class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    pump_id = fields.Many2one('pump.management', string="Pump")

    workcenter_productivity= fields.Many2one("mrp.workcenter.productivity", string="Workcenter productivity")
    block_time = fields.Float(
        related="workcenter_productivity.loss_duration",
        string="Blocked Time (Minutes)",
        store=True,
        readonly=True,
    )