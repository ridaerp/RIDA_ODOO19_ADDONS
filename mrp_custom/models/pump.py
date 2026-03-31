from odoo import models, fields, api
from datetime import timedelta

class Pump(models.Model):
    _name = 'pump.flow.pump'
    _description = 'Water Pump'

    name = fields.Char(string='Pump Name', required=True)
    serial_number = fields.Char(string='Serial Number')
    location = fields.Char(string='Location')
    active = fields.Boolean(string='Running' , default=True)
    equipment_id = fields.Many2one(
        'maintenance.equipment',
        string='Linked Equipment',
        help='pump is linked to.'
    )


class PumpFlowReading(models.Model):
    _name = 'pump.flow.reading'
    _description = 'Pump Flow Reading'
    _order = 'timestamp asc'

    pump_id = fields.Many2one('pump.flow.pump', string="Pump", required=True)
    timestamp = fields.Datetime(string="Timestamp", required=True, default=fields.Datetime.now)
    total_meter_reading = fields.Float(string="Total Meter Reading (m³)", required=True)

    hourly_flow = fields.Float(string="Flow since last reading (m³)", compute='_compute_flow_data', store=True)
    daily_flow = fields.Float(string="Total Flow Today (m³)", compute='_compute_flow_data', store=True)

    @api.depends('timestamp', 'total_meter_reading', 'pump_id')
    def _compute_flow_data(self):
        for rec in self:
            previous = self.search([
                ('pump_id', '=', rec.pump_id.id),
                ('timestamp', '<', rec.timestamp)
            ], order='timestamp desc', limit=1)

            if previous:
                rec.hourly_flow = rec.total_meter_reading - previous.total_meter_reading
            else:
                rec.hourly_flow = 0.0

            start_of_day = rec.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            readings_today = self.search([
                ('pump_id', '=', rec.pump_id.id),
                ('timestamp', '>=', start_of_day),
                ('timestamp', '<=', rec.timestamp)
            ], order='timestamp asc')

            if readings_today:
                first = readings_today[0]
                rec.daily_flow = rec.total_meter_reading - first.total_meter_reading
            else:
                rec.daily_flow = 0.0

