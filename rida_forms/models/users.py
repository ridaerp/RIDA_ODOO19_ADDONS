# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError


class User(models.Model):
    _inherit = "res.users"



    ######################add code by ekhlas ######################################
    user_type = fields.Selection(string='User type', selection=[('hq', 'Corporate Service'),
     ('site', 'Operation'),('fleet','Fleet'),('rohax','Rohax')],required=False,default="hq")
    # line_manager_id = fields.Many2one('res.users', string="Line Manager",
    #      default=lambda self: self.env.user.employee_id.line_manager_id)

    

