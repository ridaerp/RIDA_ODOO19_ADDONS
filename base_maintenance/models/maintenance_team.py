# Copyright 2019 ForgeFlow S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class MaintenanceTeam(models.Model):
    _inherit = "maintenance.team"

    user_id = fields.Many2one(comodel_name="res.users", string="Team Leader")
    description = fields.Text()
    maintenace_task = fields.Text()


class MaintenanceRequestInhert(models.Model):
    _inherit = 'maintenance.request'

    maintenace_task = fields.Text()
    mr_count = fields.Integer(string="Count", compute='compute_mr_count')
    vehicle_request_count = fields.Integer(string="Count", compute='compute_vehicle_request_count')
    issuance_count = fields.Integer(string="Count", compute='compute_issuance_count')

    def compute_issuance_count(self):
        self.issuance_count = self.env['issuance.request'].search_count([('m_request_id', '=', self.id)])


    def compute_mr_count(self):
        self.mr_count = self.env['material.request'].search_count([('m_request_id', '=', self.id)])

    def compute_vehicle_request_count(self):
        self.vehicle_request_count = self.env['vehicle.equipment.request'].search_count(
            [('mainteance_request_id', '=', self.id)])



    def set_vehicle_request(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehicle Equipment Request',
            'view_mode': 'tree,form',
            'res_model': 'vehicle.equipment.request',
            'domain': [('mainteance_request_id', '=', self.id)],
            'context': "{'create': False}"
        }


    def action_view_mr(self):
        return {
            'name': "Material Request",
            'type': 'ir.actions.act_window',
            'res_model': 'material.request',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('m_request_id', '=', self.id)],
        }


    def action_view_issuance(self):
        return {
            'name': "Issuance Request",
            'type': 'ir.actions.act_window',
            'res_model': 'issuance.request',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('m_request_id', '=', self.id)],
        }

