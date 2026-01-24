import base64
from random import choice
from string import digits

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError
from odoo.modules.module import get_module_resource

class HrEmployeePrivateExt(models.Model):
    _inherit = "hr.employee"

    address_home_id = fields.Many2one(
        'res.partner', 'Address', help='Enter here the private address of the employee, not the one linked to your company.',
        groups="base.group_user", tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")