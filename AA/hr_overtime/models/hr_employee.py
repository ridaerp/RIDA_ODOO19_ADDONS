# -*- coding: utf-8 -*-

from odoo import models, fields, api
import datetime
from odoo.exceptions import UserError


class HrEmployee(models.Model):
	_inherit= "hr.employee"

	overtime_count = fields.Integer('Overtime',compute="compute_overtime")
	cross_employee = fields.Many2one(comodel_name='hr.employee', string='Cross Employee')


    

	def action_view_overtime(self):
		for rec in self:
			return{
			'name':"Overtime",
			'type':'ir.actions.act_window',
			'res_model':'hr.over.time',
			'view_id':False,
			'view_mode':'tree,form',
			'view_type':'form',
			'target':'current',
			'domain':[('employee_id','=',self.id)]
			} 

	
	def compute_overtime(self):
		self.overtime_count = self.sudo().env['hr.over.time'].search_count([('employee_id','=',self.id)])
	