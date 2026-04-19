from odoo import fields , api , models , _



class hrLeaveType(models.Model):
    _inherit = 'hr.leave.type'


    expense_account_id = fields.Many2one('account.account', string='Expense Account')
    journal_id = fields.Many2one('account.journal', string='Journal')

    attachment_required = fields.Boolean(string='Required Attachment')
    exclude_weekend = fields.Boolean("Exclude Weekend")
    exclude_public = fields.Boolean("Exclude Public Holidays")
    leave_maximum  = fields.Boolean(string='Maximum')
    leave_maximum_number  = fields.Float(string='Maximum Number')
    year = fields.Char(string='Year')
    leave_type  = fields.Selection([
        ('annual', 'Annual Leave'),
        ('unpaid', 'Unpaid Leave'),
        ('sick', 'Sick Leave'),
        ('compassionate', 'Compassionate Leave'),
        ('maternaty', 'Maternaty Leave'),
        ('paternaty', 'Paternaty Leave'),
        ('emergancy', 'Emergancy Leave'),
        ('examination', 'Examination Leave'),
        ('haj', 'Haj Leave'),
        ('marriage', 'Marriage Leave'),
        ('comensatory', 'Comensatory Days'),
        ('permisssion', 'Permisssion'),
        ('other', 'Other'),
        ], string='Leave Type',required=True, )

class Employee(models.Model):
    _inherit = "hr.employee"
    current_leave_state = fields.Selection(compute='_compute_leave_status', string="Current Time Off Status",
        selection=[
            ('draft', 'New'),
            ('confirm', 'To Approve'),
            ('refuse', 'Refused'),
            ('validate1', 'HR Manager Approve'),
            ('line_manager', 'Line Manager'),
            ('hr_officer', ' HR officer'),
            ('ccso', 'COO'),
            ('validate', 'Approved'),
            ('cancel', 'Cancelled')
        ])
