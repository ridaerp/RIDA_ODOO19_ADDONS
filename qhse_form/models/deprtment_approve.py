from odoo import models, fields, api, _

class HotWorkDeptApproval(models.Model):
    _name = 'work.dept.approval'
    _description = 'Department Approval'

    permit_id = fields.Many2one(
        'hot.work.permit',
        string='Permit',
        ondelete='cascade'
    )
    blasting_id = fields.Many2one(
        'blasting.work.permit',
        string='Permit',
        ondelete='cascade'
    )
    confined_id = fields.Many2one(
        'confined.space.permit',
        string='Permit',
        ondelete='cascade'
    )
    excavation_id = fields.Many2one(
        'excavation.work.permit',
        string='Permit',
        ondelete='cascade'
    )
    height_id = fields.Many2one(
        'work.height.permit',
        string='Permit',
        ondelete='cascade'
    )
    lifting_id = fields.Many2one(
        'lifting.work.permit',
        string='Permit',
        ondelete='cascade'
    )
    loto_id = fields.Many2one(
        'loto.work.permit',
        string='Permit',
        ondelete='cascade'
    )

    cold_id = fields.Many2one(
        'cold.work.permit',
        string='Permit',
        ondelete='cascade'
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True
    )

    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        required=True,
        default=lambda self: self.env.user
    )

    approval_date = fields.Datetime(
        string='Approval Date',
        default=fields.Datetime.now
    )

    note = fields.Text(string='Notes')