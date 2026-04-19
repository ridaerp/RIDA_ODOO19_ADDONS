from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError



class Location(models.Model):
	_name = 'rida.location'

	name = fields.Char("Name")
