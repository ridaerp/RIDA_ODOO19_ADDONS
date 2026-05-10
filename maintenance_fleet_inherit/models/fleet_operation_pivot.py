# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from collections import defaultdict


class FleetOperationPivot(models.Model):
    _name = 'fleet.operation.pivot'
    _description = 'Fleet Operation Pivot'
    _auto = False
    _rec_name = 'equipment_id'
    _order = 'operation_date desc'

    operation_date = fields.Date(string='Date', readonly=True)

    equipment_id = fields.Many2one(
        'maintenance.equipment',
        string='Equipment',
        readonly=True
    )

    equipment_code = fields.Char(
        string='Code',
        readonly=True
    )

    location_id = fields.Many2one(
        'vehicle.location',
        string='Location',
        readonly=True
    )
    type_of = fields.Char(
        string='Type',
        readonly=True
    )

    day_type = fields.Selection([
        ('d_s', 'Day Shift'),
        ('n_s', 'Night Shift'),
        ('d_n_s', 'Day & Night Shift')
    ], string='Shift Type', readonly=True)

    operation_type = fields.Selection([
        ('operation', 'Operational'),
        ('non_operation', 'Non Operational')
    ], string='Operation Type', readonly=True)

    target_hrs = fields.Float(
        string='Target Hrs',
        readonly=True,
        group_operator='sum'
    )

    actual_hrs = fields.Float(
        string='Actual Hrs',
        readonly=True,
        group_operator='sum'
    )

    downtime_hrs = fields.Float(
        string='Downtime Hrs',
        readonly=True,
        group_operator='sum'
    )

    standby_hrs = fields.Float(
        string='Standby Hrs',
        readonly=True,
        group_operator='sum'
    )

    available_hrs = fields.Float(
        string='Available Hrs',
        readonly=True,
        group_operator='sum'
    )

    fuel_consumption = fields.Float(
        string='Fuel Consumption',
        readonly=True,
        group_operator='sum'
    )

    fuel_per_hr = fields.Float(
        string='Fuel/L-H',
        readonly=True,
        group_operator='avg'
    )

    availability = fields.Float(
        string='Availability %',
        readonly=True,
        group_operator='avg'
    )

    utilization = fields.Float(
        string='Utilization %',
        readonly=True,
        group_operator='avg'
    )

    supposed_fuel = fields.Float(
        string='Standard Fuel',
        readonly=True,
        group_operator='sum'
    )

    def init(self):

        self.env.cr.execute("""
            DROP VIEW IF EXISTS fleet_operation_pivot CASCADE
        """)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW fleet_operation_pivot AS (

                SELECT
                    row_number() OVER () AS id,

                    fo.date AS operation_date,

                    line.equipment_id AS equipment_id,

                    me.code AS equipment_code,

                    line.location_id AS location_id,

                    line.day_type AS day_type,
                            

                    line.operation_type AS operation_type,
                    me.type_of_equipment AS type_of,

                    COALESCE(line.day_duration, 0) AS target_hrs,

                    COALESCE(line.distance, 0) AS actual_hrs,

                    COALESCE(line.downtime_hrs, 0) AS downtime_hrs,

                    COALESCE(line.standby_hrs, 0) AS standby_hrs,

                    COALESCE(line.available_hrs, 0) AS available_hrs,

                    COALESCE(line.fuel_consumption, 0) AS fuel_consumption,

                    COALESCE(line.fuel_per_hr, 0) AS fuel_per_hr,

                    COALESCE(line.availability, 0) AS availability,

                    COALESCE(line.utilization, 0) AS utilization,

                    COALESCE(line.supposed_fuel, 0) AS supposed_fuel

                FROM fleet_vehicle_odometer_line line

                LEFT JOIN fleet_operation fo
                    ON fo.id = line.operation_id

                LEFT JOIN maintenance_equipment me
                    ON me.id = line.equipment_id

            )
        """)
