from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SimCardAvailable(models.Model):
    _name = 'sim.card.available'
    _description = 'Available SIM Card'
    rec_name= 'mobile_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    def get_default_carrier(self):
        carrier = self.env['sim.card.carrier'].search([], limit=1)
        return carrier.id if carrier else False

    def get_default_sim_type(self):
        sim_type = self.env['sim.card.type'].search([], limit=1)
        return sim_type.id if sim_type else False

    name = fields.Char(string='SIM Card Number (ICCID)', index=True, copy=False)
    mobile_number = fields.Char(string='Mobile Number', required=True, index=True, copy=False,tracking=True)
    carrier_id = fields.Many2one('sim.card.carrier', string='Carrier', required=True, default=get_default_carrier)
    sim_type_id = fields.Many2one('sim.card.type', string='SIM Card Type', required=True, default=get_default_sim_type)
    pin = fields.Char(string='PIN Code') # Encrypt this in real-world implementation
    puk = fields.Char(string='PUK Code') # Encrypt this
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('inactive', 'Inactive'), # Renamed from 'available'
        ('assigned', 'Assigned'),
        ('blocked', 'Blocked'), # Added blocked
        ('lost', 'Lost'),       # Added lost
        ('stolen', 'Stolen')     # Added stolen
    ], string='Status', default='inactive', readonly=True, copy=False,tracking=True)
    sim_card_count = fields.Integer(string='SIM Card History', compute='_compute_sim_card_count')
    employee_id = fields.Many2one('hr.employee', string='Employee',readonly=True,compute='employee_sim_card',tracking=True)

    def employee_sim_card(self):
        for rec in self:
            assigned_emp_card = self.env['sim.card'].search(
                [('mobile_number', '=',rec.mobile_number),('it_confirmed', '=', True)],limit=1)
            if assigned_emp_card.employee_id:
                 self.employee_id = assigned_emp_card.employee_id
            else :
                 self.employee_id = False

    def _compute_sim_card_count(self):
        for rec in self:
            rec.sim_card_count = self.env['sim.card'].search_count([('sim_id', '=', self.id)])

    def action_view_sim_card_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'SIM Card History',
            'res_model': 'sim.card',
            'view_mode': 'tree,form',
            'domain': [('sim_id', '=', self.id)],
            'context': {'sim_id': self.id},
        }


    @api.constrains('mobile_number')
    def _check_unique_mobile_number(self):
        for record in self:
            existing_record = self.search([('mobile_number', '=', record.mobile_number), ('id', '!=', record.id)])
            if existing_record:
                raise UserError(_("This Mobile Number already exists!"))

    def action_assign(self):
        self.ensure_one()
        if self.state != 'inactive':
            raise UserError(_("You can only assign SIM cards that are in the Inactive state."))

        # Check if already assigned
        assigned_card = self.env['sim.card'].search([('mobile_number', '=', self.mobile_number),('it_confirmed', '=',True)])
        if assigned_card:
            raise UserError(_("This SIM card is already assigned to an employee."))

        # Create the sim.card record directly
        sim_card_vals = {
            'sim_id': self.id,
        }
        res = self.env['sim.card'].create(sim_card_vals)

        # Return the action to open the newly created record in form view
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sim.card',
            'res_id': res.id,
            'view_id': self.env.ref('rida_forms.sim_card_form_view').id,  # Replace with your view id
            'context': {'form_view_initial_mode': 'edit'},
        }

    def action_mark_blocked(self):
        self.write({'state': 'blocked'})

    def action_mark_lost(self):
        self.write({'state': 'lost'})

    def action_mark_stolen(self):
        self.write({'state': 'stolen'})

    def action_mark_inactive(self):
        self.write({'state': 'inactive'})

    def unlink(self):
        if self.state == 'assigned':
           raise UserError("You cannot delete a sim card that is already assigned")
        return super(SimCardAvailable, self).unlink()


class SimCard(models.Model):
    _name = 'sim.card'
    _description = 'Assigned SIM Card'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    rec_name= 'mobile_number'

    name = fields.Char(string='SIM Card Number (ICCID)',index=True, readonly=True,related='sim_id.name') # No longer editable
    sim_id = fields.Many2one('sim.card.available', string='SIM Card Reference')
    employee_id = fields.Many2one('hr.employee', string='Employee',tracking=True)
    receiver_id = fields.Many2one('hr.employee', string='Receiver Employee',tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', related="employee_id.department_id",readonly=True)
    job_id = fields.Many2one("hr.job", "Job Title",related="employee_id.job_id")
    mobile_number = fields.Char(string='Mobile Number',  readonly=True, related='sim_id.mobile_number',tracking=True)
    carrier_id = fields.Many2one('sim.card.carrier', string='Carrier', readonly=True,related='sim_id.carrier_id')
    sim_type_id = fields.Many2one('sim.card.type', string='SIM Card Type', readonly=True, related='sim_id.sim_type_id')
    pin = fields.Char(string='PIN Code', readonly=True, related='sim_id.pin') # Encrypt this in real-world implementation
    puk = fields.Char(string='PUK Code', readonly=True, related='sim_id.puk') # Encrypt this
    activation_date = fields.Date(string='Activation Date')
    deactivation_date = fields.Date(string='Deactivation Date')
    sim_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('blocked', 'Blocked'),
        ('lost', 'Lost'),
        ('stolen', 'Stolen')
    ], string='Status', default='active',tracking=True) # Default to active when assigned
    notes = fields.Text(string='Notes')
    it_confirmed = fields.Boolean(string='IT Confirmed', default=False)  # New field
    sim_card_count = fields.Integer(string='SIM Card Count', compute='_compute_sim_card_count', store=True)

    @api.depends('employee_id')
    def _compute_sim_card_count(self):
        for rec in self:
            rec.sim_card_count = self.env['sim.card'].search_count([('employee_id', '=', rec.employee_id.id)])

    def action_view_sim_card_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'SIM Card History',
            'res_model': 'sim.card',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.employee_id.id)],
            'context': {'default_employee_id': self.employee_id.id},
        }

    @api.constrains('mobile_number','employee_id')
    def _check_unique_mobile_number(self):
        for record in self:
            pass
            # existing_record = self.search([('mobile_number', '=', record.mobile_number), ('id', '!=', record.id)])
            # if existing_record:
            #     raise UserError(_("This Mobile Number already exists!"))


    def action_confirm_it(self):
        self.ensure_one()
        # Check if already assigned
        assigned_card = self.env['sim.card'].search([('mobile_number', '=', self.mobile_number),('it_confirmed', '=',True)])
        if assigned_card:
            raise UserError(_(f"This SIM card is already assigned to an employee. {assigned_card.employee_id.name}"))
        for record in self:
            assigned_emp_card = self.env['sim.card'].search(
                [('employee_id', '=', record.employee_id.id), ('it_confirmed', '=', True),('sim_type_id','=',record.sim_type_id.id)])
            if assigned_emp_card:
                raise UserError(_("The Employee Already Have SIM Card"))

        self.write({'it_confirmed': True, 'sim_status': 'active'}) #Set sim status to active
        available_sim_card = self.env['sim.card.available'].search([('mobile_number', '=', self.mobile_number)], limit=1)
        if available_sim_card:
            available_sim_card.write({'state': 'assigned'})

    def action_reset_it_confirmation(self):
        self.ensure_one()
        self.write({'it_confirmed': False, 'sim_status': 'inactive'})
        available_sim_card = self.env['sim.card.available'].search([('mobile_number', '=', self.mobile_number)], limit=1)
        if available_sim_card:
            available_sim_card.write({'state': 'inactive'})

    @api.model
    def create(self, vals):
        record = super().create(vals)
        available_sim_card = self.env['sim.card.available'].search([('mobile_number', '=', record.mobile_number)], limit=1)

        if available_sim_card:
            available_sim_card.write({'state': 'assigned'})
        return record

    def unlink(self):
        for rec in self:
           available_sim_card = self.env['sim.card.available'].search([('mobile_number', '=', rec.mobile_number)])
           for rec in available_sim_card:
                rec.write({'state': 'inactive'})
           return super(SimCard, self).unlink()

class SimCardCarrier(models.Model):
    _name = 'sim.card.carrier'
    _description = 'SIM Card Carrier'

    name = fields.Char(string='Name', required=True)

class SimCardType(models.Model):
    _name = 'sim.card.type'
    _description = 'SIM Card Type'

    name = fields.Char(string='Name', required=True)

