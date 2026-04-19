# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class JobBand(models.Model):
    _name='job.band'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Job Band'
    

    name = fields.Char(string='Band Name' ,required=True )
    sequence = fields.Integer(string='Sequence',required=True, copy=False)
    grade_ids = fields.One2many('hr.grade.configuration', 'band_id', string='grades')
    
    @api.constrains('sequence')
    def _check_sequence(self):
        ids = self.env['job.band'].search([('id','!=',self.id),('sequence','=',self.sequence)])
        if len(ids)>0:
            raise UserError(_('Sequence Should Be Unique!'))

