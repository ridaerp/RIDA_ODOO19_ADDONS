import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class ReassignedSupply(models.TransientModel):
    _name = 'reassigned.supply'
    _description = 'Re-Assigned Supply Employee'

    reassigned_supply = fields.Many2one('res.users', 'Re-Assign To', track_visibility='onchange' , domain= lambda self: [("groups_id", "=", self.env.ref("material_request.group_buyers").id)] )

    def action_validate(self):
        self.ensure_one()
        active_id = self.env.context['active_ids']
        supply = self.env['material.request'].browse(active_id)

        if self.reassigned_supply:
            supply.assigned_to_supply=self.reassigned_supply
            supply.assigned_date=datetime.today()


            
    
class ReassignedEvalutor(models.TransientModel):
    _name = 'reassigned.evaluator'
    _description = 'Re-Assigned Evaulator Employee'

    reassigned_evaluator = fields.Many2one('res.users', 'Assign Evaulator', track_visibility='onchange')



    def action_validate_evaulator(self):
        self.ensure_one()
        active_id = self.env.context['active_ids']
        supply = self.env['weight.scoring.evaluation'].browse(active_id)

        if self.reassigned_evaluator:
            
            supply.additional_evaluator=self.reassigned_evaluator
            supply.assigned_date=datetime.today()

