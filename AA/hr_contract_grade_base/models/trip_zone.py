from email.policy import default

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class TripZone(models.Model):
    _inherit = 'trip.permission'

    zone_id = fields.Many2one('travel.zone', string='zone',help=(
        "Zone (A): Japan, UK, Europe, Canada, and the Americas.\n"
        "Zone (B): China, Australia, Singapore, Malaysia, Hong Kong, South Korea, "
        "Thailand, Brunei, Gulf countries, and South Africa.\n"
        "Zone (C): All other countries.\n\n"
        "Note: Two days travel time with per diem and accommodation allowances "
        "are allowed for all countries."
    ))

class TripZoneLine(models.Model):
    _inherit = 'trip.permission.line'

    accommodation = fields.Float("Accommodation", compute='_compute_total', store=True)

    @api.depends('number_of_days', 'employee_id', 'request_id.zone_id', 'request_id.trip_type')
    def _compute_total(self):
        for rec in self:
            rec.per_diem = 0
            rec.total = 0
            rec.number_of_night = 0

            # Calculate number of nights
            if rec.number_of_days and rec.number_of_days > 1:
                rec.number_of_night = rec.number_of_days - 1

            # INTERNAL TRIP RULE
            if rec.request_id.trip_type == 'internal':
                if rec.gross:
                    per_diem = (rec.gross / 30) * 3
                    rec.per_diem = per_diem if per_diem > 4000 else 4000
                    rec.total = rec.per_diem * rec.number_of_night
                else:
                    rec.per_diem = 0
                    rec.total = 0
                continue

            # EXTERNAL TRIPS
            if rec.request_id.zone_id and rec.employee_id:
                contract = rec.employee_id.contract_id

                if not contract:
                    raise UserError(_("Employee %s does not have an active contract.") %
                                    (rec.employee_id.name))

                grade = contract.grade_id

                if not grade:
                    raise UserError(_("Employee %s does not have grade defined in contract.") %
                                    (rec.employee_id.name))

                zone_line = self.env['travel.zone.line'].search([
                    ('travel_id', '=', rec.request_id.zone_id.id),
                    ('grade_ids', 'in', grade.id),
                ], limit=1)

                if not zone_line:
                    raise UserError(_("No travel configuration found for employee %s (Grade: %s) in Zone %s") %
                                    (rec.employee_id.name, grade.name, rec.request_id.zone_id.name))

                # Set per diem & accommodation
                rec.per_diem = zone_line.amount or 0
                rec.accommodation = zone_line.accommodation or 0

                # Total
                rec.total = (rec.per_diem + rec.accommodation) * rec.number_of_days

