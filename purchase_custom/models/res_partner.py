# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Partner(models.Model):
    _inherit = 'res.partner'
    
    state = fields.Selection([('draft', 'Draft'),
                              ('register', 'Registration'),
                              ('approved', 'Approved'),
                              # ('reject', 'Rejected'),
     ],string="Status", default='draft', readonly=True, track_tracking=True)

    price = fields.Integer(string='Price', default=False,)
    delivery_reliability = fields.Boolean(string='Delivery reliability', default=False,)
    delivery_date_adherence = fields.Boolean(string='Delivery Date Adherence', default=False,)
    item_quality = fields.Boolean(string='Item Quality', default=False,)
    pyment_terms = fields.Boolean(string='Payment Terms', default=False,)
    shipment_place = fields.Boolean(string='Shipment Place', default=False,)




    # Rock Information 
    east = fields.Integer("Easting")
    north = fields.Integer("Northing")
    rock_type = fields.Selection(
        [('qtz', 'QTZ'),
         ('m_vol', 'M.VOL'),
         ('chert', 'CHERT')],
        string='Rock Type'
    )
    rea_ids = fields.Many2many(
        comodel_name='x_area',  # The model to relate to
        relation='partne_area_rel',  # The name of the relation table
        column1='partner_id',  # The column for the current model (res.partner)
        column2='area_id',     # The column for the related model (area)
        string='Areas'
    )
    
 
    def action_approve(self):
        self.write({'state': 'approved'})

    @api.model
    def create(self, values):
        partner = super(Partner, self).create(values)
        # if not values.get('is_account'):
        partner.state = 'register'
        return partner

