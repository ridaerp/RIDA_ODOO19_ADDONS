from odoo import api, fields, models, _, SUPERUSER_ID

class TravelZone(models.Model):
    _name = 'travel.zone'
    _description = 'Travel Zone'

    name = fields.Char(required=True, string="Zone")
    country_ids = fields.Many2many('res.country', string="Applicable Countries")
    travel_line_id = fields.One2many('travel.zone.line','travel_id')

class TravelZoneLine(models.Model):
    _name = 'travel.zone.line'

    travel_id = fields.Many2one('travel.zone')
    grade_ids = fields.Many2many('hr.grade.configuration', string='Grade', required=True, ondelete='cascade')
    accommodation = fields.Float(string="Accommodation Amount", help="Default accommodation allowance for this zone.")
    amount = fields.Float(string='Amount')
