from odoo import models, fields, api


class LabInvestigations(models.Model):
    _name = 'lab.investigations'
    _order = "name"

    name = fields.Char(required=True)
    invest_list_ids = fields.One2many('investigations.list', 'lab_invest_id', string="Investigations List")


class InvestigationsList(models.Model):
    _name = 'investigations.list'

    name = fields.Char(required=True)
    lab_invest_id = fields.Many2one('lab.investigations')
    invest_attributes_ids = fields.One2many('investigations.attributes', 'investigations_list_id',
                                            string='Investigations Attributes')
    price = fields.Float()


class InvestigationsAttributes(models.Model):
    _name = 'investigations.attributes'

    name = fields.Char(required=True)
    normal_range = fields.Char()
    is_selected = fields.Boolean('Is positive/negative')
    investigations_list_id = fields.Many2one('investigations.list')
    price = fields.Float()

class DieasesCategory(models.Model):
    _name = 'dieases.category'

    name = fields.Char(required=True)

class Dieases(models.Model):
    _name = 'dieases'

    name = fields.Char(required=True)
    code = fields.Char()
    dieases_category_id = fields.Many2one('dieases.category',string='Disease Category')
