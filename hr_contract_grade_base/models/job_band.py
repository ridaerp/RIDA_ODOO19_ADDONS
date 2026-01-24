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


class JobBandEmployee(models.Model):
    _inherit = 'hr.employee'

    band_id = fields.Many2one(comodel_name='job.band', string='Job Band', related='grade_id.band_id')
    grade_id = fields.Many2one('hr.grade.configuration', string="Grade", related='contract_id.grade_id')
    is_worker = fields.Boolean(string='Is Worker')
    is_section_head = fields.Boolean(string='Is Section head')

