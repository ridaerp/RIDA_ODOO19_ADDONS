from odoo import models, fields, api

# Cell Model
class Pond(models.Model):
    _name = 'pond.management'
    _description = 'Pond Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Cell Name', required=True , tracking=True)
    batch_id = fields.Many2one('stock.lot', string='Batch' ,  tracking=True)
    status = fields.Selection([
        ('under_flipping', 'under Flipping'),
        ('under_preparing', 'New Area under Preparing'),
	    ('New_irrigation', 'New Area under Irrigation'),
        ('under_irrigation', 'under irrigation'),
        ('flipped_irrigation', 'Flipped & under irrigation'),
        ('waiting_flipping', 'Waiting Flipping'),
        ('flipped_waiting_irrigation', 'Flipped & waiting irrigation'),
        ('old_area', 'Old Area'),
        ('stacker_area', 'StaDker work area'),
        ('stop_area', 'irrigation stopped for this area'),

    ], string='Status', default='under_flipping', tracking=True)
    start_date = fields.Datetime(string ='First Date' , tracking=True)
    last_checked = fields.Datetime(string='Last Checked' , tracking=True)
    notes = fields.Text(string='Notes' ,  tracking=True)

# Manhole Model
class ManholeSample(models.Model):
    _name = 'manhole.manhole'
    _description = 'Manhole'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    date = fields.Date(string='Sampling Date', default=fields.Date.today)
    mh1 = fields.Float(string='mh1')
    mh2 = fields.Float(string='mh2')
    mh3 = fields.Float(string='mh3')
    mh4 = fields.Float(string='mh4')
    ppo = fields.Float(string='ppo')
    ppn = fields.Float(string='ppn')
    chemical_sample_request_count = fields.Integer(compute="_compute_chemical_sample_request_count",string="Chem-Assays")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sample', 'Sample'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('name', 'New') == 'New':
                val['name'] = self.env['ir.sequence'].next_by_code('manhole.sample.sequence') or 'New'
        return super(ManholeSample, self).create(vals)


    def action_start(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'sample'

    def action_done(self):
        for record in self:
            if record.state == 'sample':
                record.state = 'done'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'

    def _compute_chemical_sample_request_count(self):
        for record in self:
            record.chemical_sample_request_count = self.env['chemical.samples.request'].search_count([
                ('manhole_id', '=', record.id)
            ])


    def action_view_chemical_sample_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chem-Assays',
            'res_model': 'chemical.samples.request',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('manhole_id', '=', self.id)],
        }

    def create_checmical_lab_assy(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'chemical.samples.request',
            'context': {'default_manhole_id': self.id,},

        }

    def action_open_chemical_samples(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chemical Sample Requests',
            'res_model': 'chemical.samples.request',
            'view_mode': 'tree,form',
            'domain': [('manhole_id', '=', self.id)],
            'context': {'default_manhole_id': self.id},
        }




