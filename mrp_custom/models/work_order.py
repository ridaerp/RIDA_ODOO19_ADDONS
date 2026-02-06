from tokenize import String
from odoo import models, fields, api, _



import datetime
from odoo.exceptions import UserError, ValidationError, AccessError
# from dateutil.relativedelta import relativedelta
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta, datetime
from dateutil import relativedelta
import logging

_logger = logging.getLogger(__name__)


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    default_capacity = fields.Float()

    @api.model
    def write(self, vals):
        if 'code' in vals and not self.env.user.has_group('base_rida.rida_group_master_data_manager'):
            raise AccessError("You do not have permission to edit the Work Center Code.")
        return super().write(vals)

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    dry_crushed = fields.Float(string="Dry Tonnes Crushed", compute="_compute_dry_crushed")
    achieved = fields.Float(string="Achieved (%)", compute='_compute_achieved')
    metal_content = fields.Float(string="Metal Content", compute="_compute_metal_content", store=True)

    # adr_log = fields.One2many('adr.log.sheet', string="ADR Logs")

    crusher_log = fields.Integer(compute='_compute_log_counts', string="Crusher Logs")
    adr_log_count = fields.Integer(compute='_compute_log_counts', string="ADR Logs")
    stripping_log_count = fields.Integer(compute='_compute_log_counts', string="Stripping Logs")
    belt_log_count = fields.Integer(compute='_compute_log_counts', string="Belt Logs")

    pregnant_result_id = fields.Many2one('pregnant.sample.result', string="Pregnant Result")
    pregnant_result_count = fields.Integer(compute='_compute_log_counts', string="Pregnant Sample Result")

    def _compute_log_counts(self):
        for record in self:
            record.adr_log_count = self.env['adr.log.sheet'].search_count([('production_id', '=', record.id)])
            record.stripping_log_count = self.env['stripping.log.sheet'].search_count(
                [('production_id', '=', record.id)])
            record.crusher_log = self.env['crusher.log.sheet'].search_count([('production_id', '=', record.id)])
            record.belt_log_count = self.env['belt.scale.log'].search_count(
                [('production_id', '=', record.id)])
            record.pregnant_result_count = self.env['pregnant.sample.result'].search_count(
                [('production_id', '=', record.id)])

    def action_generate_serial(self):
        for production in self:
            product = production.product_id
            if product.name and 'Gold 21' in product.name:
                sequence_name = self.env['ir.sequence'].next_by_code('gold_21_serial_mrp')
            else:
                sequence_name = self.env['ir.sequence'].next_by_code('default_lot_sequence')
            if not sequence_name:
                raise UserError("لم يتم العثور على تسلسل صالح! الرجاء التأكد من إعداد التسلسل في الإعدادات.")

               
            lot = self.env['stock.lot'].create({
                'name': sequence_name,
                'product_id': product.id,
                'company_id': production.company_id.id,
            })

            production.lot_producing_id = lot.id

    def action_create_Pregnant_sample(self):
        self.ensure_one()
        return {
            'name': 'Pregnant Result',
            'type': 'ir.actions.act_window',
            'res_model': 'pregnant.sample.result',
            'view_mode': 'form',
            'target': 'new',
            'domain': [('production_id', '=', self.id)],
            'context': {
                'default_production_id': [(6, 0, [self.id])],
            }
        }

    def action_create_Belt_reading(self):
        self.ensure_one()
        workcenter_code = self.workorder_ids[:1].workcenter_id.code

        if workcenter_code == 'WC-CIC-CRSH':
            return {
                'name': 'Crusher Belt Sheet',
                'type': 'ir.actions.act_window',
                'res_model': 'belt.scale.log',
                'view_mode': 'form',
                'target': 'new',
                'domain': [('production_id', '=', self.id)],
                'context': {
                    'default_production_id': self.id,
                    'default_form_type': 'crusher',

                }
            }
        elif workcenter_code == 'WC-CIC-STKR':
            return {
                'name': 'Stacker Belt Sheet',
                'type': 'ir.actions.act_window',
                'res_model': 'belt.scale.log',
                'view_mode': 'form',
                'target': 'new',
                'domain': [('production_id', '=', self.id)],
                'context': {
                    'default_production_id': self.id,
                    'default_form_type': 'stacker',

                }
            }
        else:
            return False

    def action_create_log(self):
        self.ensure_one()
        workcenter_code = self.workorder_ids[:1].workcenter_id.code

        if workcenter_code == 'WC-CIC-LECH':
            return {
                'name': 'ADR Log Sheet',
                'type': 'ir.actions.act_window',
                'res_model': 'adr.log.sheet',
                'view_mode': 'form',
                'target': 'new',
                'domain': [('production_id', '=', self.id)],
                'context': {
                    'default_production_id': self.id,

                }
            }
        elif workcenter_code == 'WC-CIC-CELLO':
            return {
                'name': 'Stripping Log Sheet',
                'type': 'ir.actions.act_window',
                'res_model': 'stripping.log.sheet',
                'view_mode': 'form',
                'target': 'new',
                'domain': [('production_id', '=', self.id)],
                'context': {
                    'default_production_id': self.id,
                    'default_stripping_unit': 'old',
                }
            }
        elif workcenter_code == 'WC-CIC-CELN':
            return {
                'name': 'Stripping Log Sheet',
                'type': 'ir.actions.act_window',
                'res_model': 'stripping.log.sheet',
                'view_mode': 'form',
                'target': 'new',
                'domain': [('production_id', '=', self.id)],
                'context': {
                    'default_production_id': self.id,
                    'default_stripping_unit': 'new',
                }
            }
        elif workcenter_code == 'WC-CIC-CRSH':
            return {
                'name': 'Crusher Log Sheet',
                'type': 'ir.actions.act_window',
                'res_model': 'crusher.log.sheet',
                'view_mode': 'form',
                'target': 'new',
                'domain': [('production_id', '=', self.id)],
                'context': {
                    'default_production_id': self.id,
                    'default_form_type': 'crusher',

                }
            }
        elif workcenter_code == 'WC-CIC-STKR':
            return {
                'name': 'Crusher Log Sheet',
                'type': 'ir.actions.act_window',
                'res_model': 'crusher.log.sheet',
                'view_mode': 'form',
                'target': 'new',
                'domain': [('production_id', '=', self.id)],
                'context': {
                    'default_production_id': self.id,
                    'default_form_type': 'stacker',

                }
            }
        else:
            return False

    # Dry Crushed Function
    @api.depends('qty_producing', 'workorder_ids')
    def _compute_dry_crushed(self):
        for rec in self:
            if rec.workorder_ids:
                first_workorder = rec.workorder_ids[0]
                moisture = first_workorder.moisture_ or 0
                rec.dry_crushed = rec.qty_producing * ((100 - moisture) / 100)
            else:
                rec.dry_crushed = 0

    # Acheieved
    @api.depends('dry_crushed', 'product_qty')
    def _compute_achieved(self):
        for rec in self:
            if rec.product_qty and rec.dry_crushed != 0:
                rec.achieved = (rec.dry_crushed / rec.product_qty) * 100
            else:
                rec.achieved = 0.0

    # Metl Contant
    @api.depends('qty_producing', 'workorder_ids')
    def _compute_metal_content(self):
        for rec in self:
            if rec.workorder_ids:
                first_workorder = rec.workorder_ids[0]
                averg_grade = first_workorder.grade_control or 0
                rec.metal_content = rec.qty_producing * averg_grade
            else:
                rec.metal_content = 0.0

    loss_count = fields.Integer(compute='_compute_loss_count')
    chemical_sample_request_count = fields.Integer(
        compute="_compute_chemical_sample_request_count",
        string="Chem-Assays"
    )

    quality_check_count = fields.Integer(
        compute="_compute_quality_check_count",
        string="Quality Checks"
    )

    metalab_sample_request_count = fields.Integer(
        compute="_compute_metalab_sample_request_count",
        string="Metallurgical Test"
    )

    blocked_time = fields.Float(string="Total Blocked Time (hrs)", store=True)

    def button_metalab_request_req(self):
        self.ensure_one()
        return {
            'name': _('New Metallurgical request'),
            'view_mode': 'form',
            'res_model': 'metallurgical.request',
            'type': 'ir.actions.act_window',
            'context': {
                'default_company_id': self.company_id.id,
                'default_production_id': self.id,
                'shop_floor': True,  # <-- add this flag here

            },
            'domain': [('production_id', '=', self.id)],
        }



    def _compute_loss_count(self):
        for record in self:
            record.loss_count = self.env['mrp.workcenter.productivity'].search_count([
                ('workorder_id', 'in', record.workorder_ids.ids)
            ])

    def _compute_chemical_sample_request_count(self):
        for record in self:
            record.chemical_sample_request_count = self.env['chemical.samples.request'].search_count([
                ('production_id', '=', record.id)
            ])

    def _compute_quality_check_count(self):
        for record in self:
            record.quality_check_count = self.env['quality.check'].search_count([
                ('production_id', '=', record.id)
            ])

    def action_view_quality_check(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quantity Check',
            'res_model': 'quality.check',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('production_id', '=', self.id)],
        }

    def action_view_chemical_sample_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chem-Assays',
            'res_model': 'chemical.samples.request',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('production_id', '=', self.id)],
        }

    def create_checmical_lab_assy(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'chemical.samples.request',
            'context': {'default_production_id': self.id,
                        'default_workorder_id': self.id,

                        'default_company_id': self.company_id.id},
        }

    def _compute_metalab_sample_request_count(self):
        for record in self:
            record.metalab_sample_request_count = self.env['metallurgical.request'].search_count([
                ('production_id', '=', record.id)
            ])

    def action_view_metalab_sample_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chem-Assays',
            'res_model': 'metallurgical.request',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('production_id', '=', self.id)],
        }

    def create_metalab_lab_test(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'metallurgical.request',
            'context': {'default_production_id': self.id, 'default_company_id': self.company_id.id},
        }

    @api.model
    def create_daily_auto_mo(self):
        product_templates = self.env['product.template'].search([('automatuact', '=', True)])

        for tmpl in product_templates:
            for product in tmpl.product_variant_ids:

                bom = self.env['mrp.bom'].search([
                    '|',
                    ('product_id', '=', product.id),
                    ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ], limit=1)

                if not bom:
                    continue

                self.create({
                    'product_id': product.id,
                    'product_qty': bom.product_qty,
                    'product_uom_id': product.uom_id.id,
                    'bom_id': bom.id,
                    'picking_type_id': bom.picking_type_id.id,
                    'date_start': fields.Datetime.now(),
                })


class WorkOrder(models.Model):
    _inherit = 'mrp.workorder'

    # # CRUCHER 
    # moisture = fields.Float(string='Mositure')
    # cr_ph  = fields.Float(string='PH')
    # cement_loaded = fields.Float(string='Cement Loaded)')
    # sieving= fields.Float(string='sieving(+2.36)')
    # grade_control = fields.Float(string='Grade Control ')

    pregnant_result_id = fields.Many2one('pregnant.sample.result', string="Pregnant Result")

    # CRUCHER Prameters

    # moisture = fields.Float(string='Moisture Content', compute='_compute_quality_fields', store=True)
    moisture_ = fields.Float(string='Moisture Crusher', store=True)
    moisture_stockpile = fields.Float(string='Moisture StockPile', store=True)
    moisture_agglomeration = fields.Float(string='Moisture Agglomeration', store=True)


    # cr_ph = fields.Float(string='PH', compute='_compute_quality_fields', store=True)
    cru_ph= fields.Float(string='PH', store=True)

    cement_loaded = fields.Float(string='Cement Loaded', compute='_compute_quality_fields', store=True)
    cement_loaded_= fields.Float(string='Cement Loaded', store=True)


    sieving = fields.Float(string='Sieving (+2.36)', compute='_compute_quality_fields', store=True)
    sieving_ = fields.Float(string='Sieving (+2.36)', store=True)

    grade_control = fields.Float(string='Grade Control')

    # LEACHING
    barren_cyanide = fields.Float(string='Barren Cyanide', compute='_compute_sheet_data')
    Pregnant_cyanide = fields.Float(string='Pregnant Cyanide', compute='_compute_sheet_data')
    ph_Outlet = fields.Float(string='Pregnant PH', compute='_compute_sheet_data')
    oxygen = fields.Float(string='Oxygen', compute='_compute_sheet_data')
    oxygen_pregnant = fields.Float(string='Pregnant Oxygen', compute='_compute_sheet_data')

    grade_pregnant = fields.Float()
    grade_barren = fields.Float()

    # ADR
    au_Inlet = fields.Float(string='Inlet AU')
    au_Outlet = fields.Float(string='Outlet AU')
    unit_Outlet = fields.Float(string='Unit Outlet AU')
    carbon_eff = fields.Float(string="Carbon Efficiency", compute='_compute_carbon_efficiency', store=True)

    au = fields.Float(string="Au", compute='_compute_au', store=True)
    unit_au = fields.Float(string="Unit Au", compute='_compute_au', store=True)
    flow = fields.Float(string="Flow", compute="_compute_flow", store=True , readonly=False)

    flowmeter_ids = fields.One2many('flowmeter.flowmeter', 'workcenter_id', string="Flow Meters")
    # flowmeter_reading_sheet = fields.Many2one('flowmeter.reading.sheet' , 'Flowmeter Sheet')

    # Cell
    temperature = fields.Float(string='Temperature', compute='_compute_sheet_data')
    volt = fields.Float(string='Volt', compute='_compute_sheet_data' )
    ampere = fields.Float(string='Ampere', compute='_compute_sheet_data' )
    recovery_percentage = fields.Float(string='Recovery Percentage', )
    total_metal_recovery = fields.Float(string='Total Metal Recovery (g)')

    # AU Calculation
    @api.depends('au_Inlet', 'au_Outlet', 'unit_Outlet', 'flow')
    def _compute_au(self):
        for record in self:

            if record.workcenter_id.id not in [7, 8, 9, 11]:
                continue

            record.au = record.flow * (record.au_Inlet - record.au_Outlet)
            # record.production_id.qty_producing = record.au
            if record.unit_Outlet:
                record.unit_au = record.flow * (record.au_Inlet - record.unit_Outlet)
            else:
                record.unit_Outlet = 0.0

    # def action_transfer_cr_ph(self):
    #     # تأكدي إنك في سياق واحد فقط (self هو سجل واحد أو مجموعة)
    #     query = """
    #             UPDATE mrp_workorder
    #             SET
    #                 cru_ph = cr_ph,
    #                 moisture_ = moisture,
    #                 cement_loaded_ = cement_loaded,
    #                 sieving_ = sieving
    #             WHERE
    #                 cr_ph IS NOT NULL AND
    #                 moisture IS NOT NULL AND
    #                 cement_loaded IS NOT NULL AND
    #                 sieving IS NOT NULL
    #
    #         """
    #     self.env.cr.execute(query)

    def _compute_sheet_data(self):
        for rec in self:
            rec.barren_cyanide = 0.0
            rec.Pregnant_cyanide = 0.0
            rec.ph_Outlet = 0.0
            rec.oxygen = 0.0
            rec.oxygen_pregnant = 0.0
            rec.temperature = 0.0
            rec.ampere = 0.0
            rec.volt = 0.0
            rec.recovery_percentage = 0.0
            rec.total_metal_recovery = 0.0
            rec.cru_ph = 0.0
            rec.moisture_ = 0.0
            rec.cement_loaded_ = 0.0
            rec.sieving_ = 0.0
            rec.moisture_stockpile = 0.0
            rec.moisture_agglomeration = 0.0

            if rec.production_id:

                crusher_log = self.env['crusher.log.sheet'].search([
                    ('production_id', '=', rec.production_id.id)
                ], order='date desc', limit=1)

                adr_log = self.env['adr.log.sheet'].search([
                    ('production_id', '=', rec.production_id.id)
                ], order='date desc', limit=1)

                stripping_log = self.env['stripping.log.sheet'].search([
                    ('production_id', '=', rec.production_id.id)
                ], order='date desc', limit=1)

                if adr_log:

                    rec.barren_cyanide = adr_log.avg_barren_cn
                    rec.Pregnant_cyanide = adr_log.avg_preg_cn
                    rec.ph_Outlet = adr_log.avg_preg_ph
                    rec.oxygen = adr_log.avg_barren_oxygen
                    rec.oxygen_pregnant = adr_log.avg_preg_oxygen
                    rec.cru_ph = adr_log.avg_barren_ph

                elif stripping_log:

                    rec.temperature = stripping_log.avg_temperature
                    rec.volt = stripping_log.avg_volt
                    rec.ampere = stripping_log.avg_ampere
                    rec.recovery_percentage = stripping_log.recovery_percentage
                    rec.total_metal_recovery = stripping_log.total_metal_recovery

                elif crusher_log:
                    rec.cru_ph = crusher_log.avg_ph
                    rec.moisture_ = crusher_log.avg_moisture
                    rec.moisture_stockpile = crusher_log.avg_under_crusher_moisture
                    rec.moisture_agglomeration = crusher_log.avg_agg_moisture
                    rec.sieving_ = crusher_log.avg_seiving
                    rec.cement_loaded_ = crusher_log.cement_load



    # Compute Flow in workorder from flowmeter
    @api.depends('workcenter_id', 'flowmeter_ids.total_flow_today', 'state')
    def _compute_flow(self):
        for record in self:
            if record.flow > 0:
                continue
            flow_value = 0.0

            if record.production_id and record.production_id.state in ['confirmed', 'in_progress', 'to_close']:
                if record.workcenter_id:
                    flowmeters = self.env['flowmeter.flowmeter'].search([
                        ('workcenter_id', '=', record.workcenter_id.id)
                    ])
                    total_flow = sum(flowmeter.total_flow_today for flowmeter in flowmeters)

                    if record.workcenter_id.code in ['WC-CIC-ADRO', 'WC-CIC-ADRN']:
                        inprogress_count = record.workcenter_id.inprogress_workorder_count
                        if inprogress_count > 0:
                            flow_value = total_flow / inprogress_count
                        else:
                            flow_value = total_flow  # fallback
                    else:
                        flow_value = total_flow

            record.flow = flow_value

    @api.depends('au_Inlet', 'unit_Outlet')
    def _compute_carbon_efficiency(self):
        for record in self:
            if record.au_Inlet and record.unit_Outlet:
                record.carbon_eff = 1 - (record.unit_Outlet / record.au_Inlet)
            else:
                record.carbon_eff = 0.0

    # Crucher Parameters
    availability_percent = fields.Integer(string='Availability (%)', compute='_compute_availability', store=True)
    utilization_percent = fields.Integer(string='Utilization (%)', compute='_compute_utilization_value', store=True)
    feed_rate = fields.Integer(string='Feed Rate', compute='_compute_feed_rate_value', store=True)
    production_target = fields.Integer(string='Production Target', compute='_compute_production_target', store=True)

    # Downtime crusher
    cleaning_operation = fields.Float(string='Cleaning Operation', compute='_compute_losses', store=True)
    over_load = fields.Float(string='Due Over Load', compute='_compute_losses', store=True)
    equipment_stuck_jcr = fields.Float(string='Stuck (J-CR)', compute='_compute_losses', store=True)
    equipment_stuck_cr = fields.Float(string='Stuck (C-CR)', compute='_compute_losses', store=True)
    stockpile_full = fields.Float(string='Stockpile Full', compute='_compute_losses', store=True)
    overflow_stuck_cr = fields.Float(string='O.Flow (C-CR)', compute='_compute_losses', store=True)
    bad_weather = fields.Float(string='Bad Weather')
    m_operation = fields.Float(string='Operation', compute='_compute_losses', store=True)
    no_trucks = fields.Float(string='No Trucks', compute='_compute_losses', store=True)
    e_operation = fields.Float(string='Equip Operation', compute='_compute_losses', store=True)
    no_equipment = fields.Float(string='No Equipment', compute='_compute_losses', store=True)
    mechanical_loss = fields.Float(string='Mechanical Loss', compute='_compute_losses', store=True)
    electrical_loss = fields.Float(string='Electrical Loss', compute='_compute_losses', store=True)
    generation_loss = fields.Float(string='Generation Loss', compute='_compute_losses', store=True)
    other_loss = fields.Float(string='Other Loss', compute='_compute_losses', store=True)

    maintenance_loss = fields.Float(string='Maintenance DownTime', compute='_compute_total_loss', store=True)

    total_loss_per_minute = fields.Float(string='Total Loss/Min', compute='_compute_total_loss', store=True)
    explanation_for_other = fields.Text(string='Explanation for Other')

    total_loss = fields.Float(string='Total Losses', compute='_compute_availability', store=True)
    total_time = fields.Float(string='Total Time', compute='_compute_availability', store=True)

    # time_lose_ids = fields.One2many(
    #     'mrp.workcenter.productivity', 'workorder_ref_id', copy=False)

    @api.depends('state')
    def _compute_losses(self):
        # Map codes to field names for easy looping
        code_to_field = {
            'cleaning_operation': 'cleaning_operation',
            'due_over_load': 'over_load',
            'stuck_jcr': 'equipment_stuck_jcr',
            'stuck_cr': 'equipment_stuck_cr',
            'stockpile_full': 'stockpile_full',
            'overflow_stuck_cr': 'overflow_stuck_cr',
            # 'bad_weather': 'bad_weather',
            'm_operation': 'm_operation',
            'no_trucks': 'no_trucks',
            'e_operation': 'e_operation',
            'no_equipment': 'no_equipment',
            'mechanical': 'mechanical_loss',
            'electrical': 'electrical_loss',
            'generation': 'generation_loss',
            'other': 'other_loss',
        }

        for workorder in self:
            # Initialize all fields to 0.0
            for field in code_to_field.values():
                setattr(workorder, field, 0.0)

            time_obj_ids = ids = self.env['mrp.workcenter.productivity'].search([
                ('workorder_ref_id', '=', workorder.id)])

            # Sum durations by loss_detail_id.code
            for time in time_obj_ids:
                code = time.loss_detail_id.code
                duration = time.loss_duration or 0.0

                # Normalize code for mapping (example: if you want 'due_over_load' for code 'due_over_load')
                # Make sure your codes exactly match keys in code_to_field dict or adapt here

                if code in code_to_field:
                    current = getattr(workorder, code_to_field[code])
                    setattr(workorder, code_to_field[code], current + duration)

    @api.depends('cleaning_operation', 'over_load', 'equipment_stuck_jcr', 'equipment_stuck_cr',
                 'stockpile_full', 'overflow_stuck_cr', 'm_operation', 'no_trucks',
                 'no_equipment', 'e_operation', 'mechanical_loss', 'electrical_loss', 'generation_loss',
                 'other_loss')
    def _compute_total_loss(self):
        for record in self:
            record.total_loss_per_minute = (
                    record.cleaning_operation +
                    record.over_load +
                    record.equipment_stuck_jcr +
                    record.equipment_stuck_cr +
                    record.stockpile_full +
                    record.overflow_stuck_cr +
                    record.m_operation +
                    record.no_trucks +
                    record.e_operation +
                    record.no_equipment +
                    record.mechanical_loss +
                    record.electrical_loss +
                    record.generation_loss +
                    record.other_loss
            )
            record.maintenance_loss = record.mechanical_loss + record.electrical_loss + record.generation_loss

    qty_producing = fields.Float(
        related='production_id.qty_producing',
        string='Quantity Producing',
        readonly=True,
        store=True
    )

    # Invisible Workcenter 

    workcenter_code = fields.Char(related='workcenter_id.code', string="Workcenter Code", store=True)

    is_crusher_staker = fields.Boolean(compute='_compute_workcenter_flags', store=True)
    is_heap = fields.Boolean(compute='_compute_workcenter_flags', store=True)
    is_adr = fields.Boolean(compute='_compute_workcenter_flags', store=True)
    is_strip = fields.Boolean(compute='_compute_workcenter_flags', store=True)
    is_smelt = fields.Boolean(compute='_compute_workcenter_flags', store=True)

    # is_lab = fields.Boolean(compute='_compute_workcenter_flags', store=True)

    @api.depends('workcenter_code')
    def _compute_workcenter_flags(self):
        for rec in self:
            code = (rec.workcenter_code or '').strip().upper()  # ← Correct way to reference the field

            rec.is_crusher_staker = code in ['WC-CIC-STKR', 'WC-CIC-CRSH']

            rec.is_heap = code == 'WC-CIC-LECH'
            rec.is_adr = code in ['WC-CIC-ADRO', 'WC-CIC-ADRN']
            rec.is_strip = code in ['WC-CIC-CELN', 'WC-CIC-CELLO']
            rec.is_smelt = code == 'WC-CIC-SML'

    # FEED READ
    @api.depends('qty_producing', 'duration', 'state')
    def _compute_feed_rate_value(self):
        for record in self:
            if record.state == 'done' and record.duration:
                if record.duration > 0:
                    record.feed_rate = record.qty_producing / (record.duration / 60)
            else:
                record.feed_rate = 0

                # UTILIZATION

    @api.depends('duration', 'state')
    def _compute_utilization_value(self):
        for record in self:
            if record.state == 'done' and record.duration:
                record.utilization_percent = (record.duration / (record.total_time - record.maintenance_loss)) * 100
            else:
                record.utilization_percent = 0

    # Availability
    @api.depends('duration', 'state')
    def _compute_availability(self):

        ############add code by ekhlas to calculate 

        for record in self:
            time_obj_ids = ids = self.env['mrp.workcenter.productivity'].search([
                ('workorder_ref_id', '=', record.id)])

            # for time in time_obj_ids:
            #     total_loss_duration  += time.loss_duration or 0.0   

            record.total_loss = sum(time.loss_duration or 0.0 for time in time_obj_ids)

            record.total_time = record.total_loss + record.duration

            if record.state == 'done' and record.duration:
                # record.availability_percent = (record.duration / 1440) * 100

                ############add code by ekhlas to calculate 
                total_time = record.duration + record.total_loss
                record.availability_percent = (1 - (record.maintenance_loss / total_time)) * 100



            else:
                record.availability_percent = "0"

    # PRODUCTION TARGET
    @api.depends('workcenter_id.default_capacity', 'duration', 'state')
    def _compute_production_target(self):
        for record in self:
            if record.state == 'done' and record.duration:
                production_per_hour = record.workcenter_id.default_capacity if record.workcenter_id else 0
                record.production_target = production_per_hour * (record.duration / 60)
            else:
                record.production_target = "0"

    def button_chemical_assay_req(self):
        self.ensure_one()
        return {
            'name': _('New Chemical Assay'),
            'view_mode': 'form',
            'views': [(self.env.ref('material_request.view_chemical_request_form').id, 'form')],
            'res_model': 'chemical.samples.request',
            'type': 'ir.actions.act_window',
            'context': {
                'default_company_id': self.company_id.id,
                'default_workorder_id': self.id,
                'default_production_id': self.production_id.id,
                'discard_on_footer_button': True,
                'shop_floor': True,  # <-- add this flag here

            },
            'target': 'new',
            'domain': [('workorder_id', '=', self.id)]
        }




    def action_create_Pregnant_sample(self):
        self.ensure_one()
        return {
            'name': _('New PS AND BS Sample'),
            'view_mode': 'form',
            'views': [(self.env.ref('mrp_custom.view_pregnant_sample_result_form').id, 'form')],
             'res_model': 'pregnant.sample.result',
            'type': 'ir.actions.act_window',
            'context': {
                # 'default_company_id': self.company_id.id,
                'default_workorder_id': self.id,
                'default_production_id': [(6, 0, [self.production_id.id])],
                'discard_on_footer_button': True,
                'shop_floor': True,  # <-- add this flag here

            },
            'target': 'new',
            'domain': [('workorder_id', '=', self.id)]
        }


    def button_metalab_request_req(self):
        self.ensure_one()
        return {
            'name': _('New Metallurgical request'),
            'view_mode': 'form',
            'views': [(self.env.ref('material_request.metallurgical_request_form').id, 'form')],
            'res_model': 'metallurgical.request',
            'type': 'ir.actions.act_window',
            'context': {
                'default_company_id': self.company_id.id,
                'default_workorder_id': self.id,
                'default_production_id': self.production_id.id,
                'discard_on_footer_button': True,
                'shop_floor': True,  # <-- add this flag here

            },
            'target': 'new',
            'domain': [('workorder_id', '=', self.id)]
        }

    # @api.depends('production_id', 'state')
    # def _compute_quality_fields(self):
    #     worksheet_models = [
    #         'x_quality_check_worksheet_template_1',
    #         'x_quality_check_worksheet_template_2',
    #         'x_quality_check_worksheet_template_3',
    #         'x_quality_check_worksheet_template_4',
    #         'x_quality_check_worksheet_template_5',
    #         # 'x_quality_check_worksheet_template_7',
    #         # 'x_quality_check_worksheet_template_8',
    #         # 'x_quality_check_worksheet_template_9',
    #         # 'x_quality_check_worksheet_template_10',
    #         # 'x_quality_check_worksheet_template_11',
    #         # 'x_quality_check_worksheet_template_12',
    #         # 'x_quality_check_worksheet_template_13',
    #         # 'x_quality_check_worksheet_template_14',
    #         # 'x_quality_check_worksheet_template_15',
    #         # 'x_quality_check_worksheet_template_16',
    #         # 'x_quality_check_worksheet_template_17',
    #         # 'x_quality_check_worksheet_template_18',
    #         # 'x_quality_check_worksheet_template_19',
    #
    #     ]
    #     for wo in self:
    #         # Reset values
    #         wo.cr_ph = 0.0
    #         wo.moisture = 0.0
    #         wo.cement_loaded = 0.0
    #         wo.sieving = 0.0
    #         wo.grade_control = 0.0
    #         # wo.barren_cyanide = 0.0
    #         # wo.Pregnant_cyanide = 0.0
    #         # wo.ph_Outlet = 0.0
    #         # wo.oxygen = 0.0
    #         # wo.temperature = 0.0
    #         # wo.volt = 0.0
    #         # wo.ampere = 0.0
    #
    #         if not wo.production_id:
    #             continue
    #
    #         # ✅ Get latest quality check for the same production order (not workorder)
    #         check = self.env['quality.check'].search([
    #             ('production_id', '=', wo.production_id.id),
    #             ('test_type', '=', 'worksheet'),  # Adjust if test_type is a selection
    #         ], order='id desc', limit=1)
    #
    #         if not check:
    #             continue
    #
    #         # Try each worksheet model
    #         for model_name in worksheet_models:
    #             Worksheet = self.env[model_name]
    #             worksheet = Worksheet.search([('x_quality_check_id', '=', check.id)], limit=1)
    #
    #             if worksheet:
    #                 # ✅ Assign latest values directly (no list needed)
    #                 # wo.cr_ph = worksheet.x_studio_ph
    #                 # wo.moisture = worksheet.x_studio_moisture_content
    #
    #                 # Use getattr to safely access only existing fields
    #                 wo.cr_ph = getattr(worksheet, 'x_studio_ph', 0.0) or 0.0
    #                 wo.moisture = getattr(worksheet, 'x_studio_moisture_content', 0.0) or 0.0
    #                 wo.cement_loaded = getattr(worksheet, 'x_studio_cement_loaded', 0.0) or 0.0
    #                 wo.sieving = getattr(worksheet, 'x_studio_sieving', 0.0) or 0.0
    #                 # wo.grade_control = getattr(worksheet, 'x_studio_grade_control', 0.0) or 0.0
    #
    #                 # wo.barren_cyanide = getattr(worksheet, 'x_studio_barren_cyanide', 0.0) or 0.0
    #                 # wo.Pregnant_cyanide = getattr(worksheet, 'x_studio_pregnant_cyanide', 0.0) or 0.0
    #                 # wo.ph_Outlet = getattr(worksheet, 'x_studio_pregnant_ph', 0.0) or 0.0
    #                 # wo.oxygen = getattr(worksheet, 'x_studio_oxygen', 0.0) or 0.0
    #                 # wo.temperature = getattr(worksheet, 'x_studio_temperature', 0.0) or 0.0
    #                 # wo.volt = getattr(worksheet, 'x_studio_volt', 0.0) or 0.0
    #                 # wo.ampere = getattr(worksheet, 'x_studio_ampere', 0.0) or 0.0
    #                 break  # Stop after finding first valid worksheet

    # @api.depends('production_id')
    # def _compute_quality_fields(self):
    #     for wo in self:
    #         wo.cr_ph = 0.0
    #         wo.cement_loaded = 0.0
    #         wo.sieving = 0.0
    #         wo.grade_control = 0.0

    #         checks = self.env['quality.check'].search([
    #             ('production_id', '=', wo.production_id.id),
    #             ('test_type_id', '=', 'worksheet'),  # If using worksheet
    #         ],limit=1)

    #         values = {
    #             'ph': [],
    #             'cement_loaded': [],
    #             'sieving': [],
    #             'grade_control': [],
    #         }

    #         for qc in checks:
    #             worksheet = qc.x_quality_check_worksheet_template_1  # or .worksheet_id if Studio used default

    #             if worksheet:
    #                 if hasattr(worksheet, 'x_ph') and worksheet.x_ph:
    #                     values['ph'].append(worksheet.x_ph)
    #                 if hasattr(worksheet, 'x_cement_loaded') and worksheet.x_cement_loaded:
    #                     values['cement_loaded'].append(worksheet.x_cement_loaded)
    #                 if hasattr(worksheet, 'x_sieving') and worksheet.x_sieving:
    #                     values['sieving'].append(worksheet.x_sieving)
    #                 if hasattr(worksheet, 'x_grade_control') and worksheet.x_grade_control:
    #                     values['grade_control'].append(worksheet.x_grade_control)

    # Use average or sum depending on your business logic
    # wo.cr_ph = sum(values['ph']) / len(values['ph']) if values['ph'] else 0.0
    # wo.cement_loaded = sum(values['cement_loaded']) / len(values['cement_loaded']) if values['cement_loaded'] else 0.0
    # wo.sieving = sum(values['sieving']) / len(values['sieving']) if values['sieving'] else 0.0
    # wo.grade_control = sum(values['grade_control']) / len(values['grade_control']) if values['grade_control'] else 0.0

class WorkOrder(models.Model):
    _inherit = 'mrp.workcenter'

    inprogress_workorder_count = fields.Integer(string="In Progress Workorders")

    def update_inprogress_workorder_counts(self):
        Workorder = self.env['mrp.workorder']
        for workcenter in self.search([]):
            count = Workorder.search_count([
                ('workcenter_id', '=', workcenter.id),
                ('state', '=', 'progress')
            ])
            workcenter.inprogress_workorder_count = count

class WorkcenterProductivityLoss(models.Model):
    _inherit = 'mrp.workcenter.productivity'
    _rec_name = "sequence"

    loss_detail_id = fields.Many2one(
        'mrp.workcenter.productivity.loss.detail',
        string="Detail Reason",

    )
    loss_duration = fields.Float(string='Loss duration', compute='_compute_loss', store=True)
    equipment_id = fields.Many2one(comodel_name="maintenance.equipment", )

    workorder_ref_id = fields.Many2one(
        'mrp.workorder',
        string='Source Workorder',
        ondelete='restrict',  # ✅ Fix for ValueError
    )

    production_ref_id = fields.Many2one(
        related='workorder_ref_id.production_id',
        string='Production Order',
        store=True,
        readonly=True,
    )

    @api.depends('date_start', 'date_end')
    def _compute_loss(self):
        for record in self:
            if record.date_start and record.date_end:
                # Calculate duration in hours
                loss_duration = (record.date_end - record.date_start).total_seconds() / 60.0
                record.loss_duration = loss_duration
            else:
                record.duration = 0.0

    sequence = fields.Char(string="Sequence", readonly=True, copy=False)

    @api.model
    def create(self, vals):
        for val in vals:
            if not val.get("sequence"):
                val["sequence"] = self.env["ir.sequence"].next_by_code("productivity.loss.log")
            res = super().create(vals)
            res.date_end = False
        return res


class MrpProductivityLossDetail(models.Model):
    _name = 'mrp.workcenter.productivity.loss.detail'
    _description = 'Workcenter Productivity Loss Detail Reason'

    name = fields.Char(string="Detail Reason", required=True)
    loss_id = fields.Many2one(
        comodel_name='mrp.workcenter.productivity.loss',
        string='Loss Reason',
        required=True,
        ondelete='cascade'
    )
    code = fields.Char(string='Code', required=True, index=True, copy=False)

# class QualityWorksheet4(models.Model):

#     _inherit = 'x_quality_check_worksheet_template_4'


#     def write(self, vals):
#         res = super().write(vals)
#         self._update_related_workorder_quality()
#         return res

#     def _update_related_workorder_quality(self):
#         for record in self:
#             quality_check = record.x_quality_check_id
#             if quality_check and quality_check.production_id:
#                 workorders = self.env['mrp.workorder'].search([
#                     ('production_id', '=', quality_check.production_id.id)
#                 ])
#                 # This will trigger re-calculation and save the new values
#                 workorders._compute_quality_fields()



class ChemicalAssay(models.Model):
    _inherit = "chemical.samples.request"

    manhole_id = fields.Many2one('manhole.manhole', string='Manhole')
    pregnant_result = fields.Many2one('pregnant.sample.result', string='Pregnant Result')
    # pregnant_result_sample = fields.Many2one('pregnant.sample.result', string='Pregnant Result')

    stripping_id = fields.Many2one('stripping.log.sheet', string='Stripping Sheet', ondelete='cascade')
