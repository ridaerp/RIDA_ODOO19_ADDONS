from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError



class HrDepartment(models.Model):
    _inherit = 'hr.department'

    dep_type = fields.Selection(selection=[
            ('department', 'Department'),
            ('division', 'Division'),
            ('section', 'Section'),
            ('unit', 'Unit'),
        ], string='Type', required=True, readonly=True, copy=False, tracking=True,
        default='department')

    location_id = fields.Many2one('rida.location')
    parent_id = fields.Many2one('hr.department', string='Division', index=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('dep_type','=','division')]")
    div_parent_id = fields.Many2one('hr.department', string='Department', index=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('dep_type','=','department')]")
    section_parent_id = fields.Many2one('hr.department', string="Section", index=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id),('dep_type', '=', 'section')]")

    div_manager = fields.Many2one('hr.employee', string="Division Manager" ,domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    section_head = fields.Many2one('hr.employee', string="Section Head" ,domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    rig_manager = fields.Many2one('hr.employee', string="Rig Manager",domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    director_id= fields.Many2one('res.users', string="Director")
    c_level_id= fields.Many2one('res.users', string="C Level")
    # field_hq = fields.Selection([('hq','HQ'),('field','Field')],string="HQ/Field",required=True)

    @api.onchange('div_parent_id')
    def get_dep_parent_id(self):
        if self.div_parent_id:
            self.parent_id=self.div_parent_id

    @api.depends('name', 'section_parent_id.complete_name', 'div_parent_id.complete_name')
    def _compute_complete_name(self):
        for department in self:
            if department.section_parent_id:
                department.complete_name = '%s / %s' % (department.section_parent_id.complete_name, department.name)
            elif department.div_parent_id:
                department.complete_name = '%s / %s' % (department.div_parent_id.complete_name, department.name)
            elif department.parent_id:
                department.complete_name = '%s / %s' % (department.parent_id.complete_name, department.name)
            else:
                department.complete_name = department.name


    @api.onchange('section_parent_id')
    def get_section_parent_id(self):
        if self.section_parent_id:
            self.parent_id=self.section_parent_id



    @api.onchange('div_manager','section_head','rig_manager')
    def get_manager(self):
        if self.div_manager:
            self.manager_id = self.div_manager.id
        if self.section_head:
            self.manager_id = self.section_head.id
        if self.rig_manager:
            self.manager_id = self.rig_manager.id
