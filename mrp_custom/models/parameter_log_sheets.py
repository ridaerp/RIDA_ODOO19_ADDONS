from odoo import models, fields, api, _
from statistics import mean

from datetime import datetime, timedelta, time
import logging
_logger = logging.getLogger(__name__)


# Flowmeter Model
class Flowmeter(models.Model):
    _name = 'flowmeter.flowmeter'
    _description = 'Flowmeter'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Flowmeter', required=True, tracking=True)
    code = fields.Char(string="Code", required=True)
    serial_number = fields.Char(string='Serial Number', tracking=True)
    assigned_user_id = fields.Many2one('res.users', string='Assigned To')
    location = fields.Char(string='Location', tracking=True)
    active = fields.Boolean(string='Running', default=True, tracking=True)
    parent_id = fields.Many2one("flowmeter.flowmeter", string="Parent Flowmeter")
    child_ids = fields.One2many("flowmeter.flowmeter", "parent_id", string="Child Flowmeters")
    area = fields.Selection([
        ('barren', 'Barren'),
        ('adr_old', 'ADR Old'),
        ('adr_new', 'ADR New'),
        ('cell_old', 'Cell Old'),
        ('cell_new', 'Cell New'),
    ], string="Flow Rate Area", tracking=True)


    equipment_id = fields.Many2one('maintenance.equipment', string='Linked Equipment', tracking=True)
    pump_relation_ids = fields.One2many('flowmeter.pump.relation', 'flowmeter_id', string='Pump Relations',
                                        tracking=True)
    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center', )
    last_total_meter_reading = fields.Float(string="Last  Reading (m³)", store=True)
    total_flow_today = fields.Float(string="Total Flow Today (m³)", store=True)

    flowmeter_reading_sheet = fields.One2many(
        'flowmeter.reading.sheet', 'flowmeter_id', string="Reading Sheets"
    )

    flowmeter_reading_sheet_count = fields.Integer(
        string="Reading Count", compute="_compute_reading_sheet_count"
    )

    @api.depends('flowmeter_reading_sheet')
    def _compute_reading_sheet_count(self):
        for record in self:
            record.flowmeter_reading_sheet_count = len(record.flowmeter_reading_sheet)

    def action_view_flowmeter_readings(self):
        self.ensure_one()
        return {
            'name': 'Flowmeter Readings',
            'type': 'ir.actions.act_window',
            'res_model': 'flowmeter.reading.sheet',
            'view_mode': 'list,form',
            'domain': [('flowmeter_id', '=', self.id)],
            'target': 'current',
        }

    def _update_last_reading(self):
        Reading = self.env['flowmeter.reading']
        for rec in self:

            last_reading = Reading.search([
                ('sheet_id.flowmeter_id', '=', rec.id)
            ], order='timestamp desc', limit=1)

            rec.last_total_meter_reading = last_reading.total_meter_reading if last_reading else 0.0
            rec.total_flow_today = last_reading.daily_flow if last_reading else 0.0


    def action_update_last_reading(self):
        self._update_last_reading()
        return True

    @api.model
    def cron_update_flow_and_workorders(self):
        self.search([])._update_last_reading()

        flowmeters = self.search([])
        workcenters = flowmeters.mapped('workcenter_id')
        workorders = self.env['mrp.workorder'].search([
            ('workcenter_id', 'in', workcenters.ids)
        ])
        workorders._compute_flow()

    # Cron Job to update last reading
    def _cron_update_flowmeters(self):
        all_flowmeters = self.search([])
        for rec in all_flowmeters:
            rec._update_last_reading()


# Pump Model
class Pump(models.Model):
    _name = 'pump.management'
    _description = 'Pump'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Pump ", required=True, tracking=True)
    code = fields.Char(string="Code", required=True)
    location = fields.Char(string="Location", tracking=True)
    serial_number = fields.Char(string='Serial Number')
    assigned_user_id = fields.Many2one('res.users', string='Assigned To')
    lot_ids = fields.Many2many('stock.lot', 'pump_lot_rel', 'pump_id', 'lot_id', string='Heap Area', tracking=True)
    equipment_id = fields.Many2one('maintenance.equipment', string='Linked Equipment',
                                   help='The equipment this pump is connected to.')
    flowmeter_relation_ids = fields.One2many('flowmeter.pump.relation', 'pump_id', string='Flowmeter Relations',
                                             tracking=True)
    maintenance_request_ids = fields.One2many('maintenance.request', 'pump_id', string="Maintenance Requests",
                                              tracking=True)

    # Create Maintenance Request from Pump Form
    def action_create_maintenance_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request',
            'view_mode': 'form',
            'context': {
                'default_name': f'Maintenance for {self.name}',
                'default_pump_id': self.id,
                'default_equipment_id': self.equipment_id.id,
            },
            'target': 'current',
        }


# Relation Model Between Flowmeter model  and Pump Model for track pump productivity
class FlowmeterPumpRelation(models.Model):
    _name = 'flowmeter.pump.relation'
    _description = 'Pump-Flowmeter Relation'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    pump_id = fields.Many2one('pump.management', string='Pump', required=True)
    flowmeter_id = fields.Many2one('flowmeter.flowmeter', string='Flowmeter', required=True)

    is_running = fields.Boolean(string="Running", default=False, )
    start_time = fields.Datetime(string="Start Time")
    total_time = fields.Float(string="Total Time (m)", digits=(16, 2), readonly=True)
    today_time = fields.Float(string="Today's Time (m)", digits=(16, 2), readonly=True)
    last_logged_date = fields.Date(string="Last Logged Date")

    # Start Pump
    def action_start_pump(self):
        for record in self:
            if not record.is_running:
                record.start_time = fields.Datetime.now()
                record.is_running = True

    # Stop Pump
    def action_stop_pump(self):
        for record in self:
            if record.is_running and record.start_time:
                stop_time = fields.Datetime.now()
                duration = (stop_time - record.start_time).total_seconds() / 60
                record.total_time += duration

                # Calculate Today Time
                today = fields.Date.today()
                if record.last_logged_date == today:
                    record.today_time += duration
                else:
                    record.today_time = duration
                    record.last_logged_date = today

                record.is_running = False
                record.start_time = False


# Flow Meter Model
class FlowmeterReadingSheet(models.Model):
    _name = 'flowmeter.reading.sheet'
    _description = 'Flowmeter Reading Sheet'
    _order = 'date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Reference", required=True, default=lambda self: _('New'))
    flowmeter_id = fields.Many2one('flowmeter.flowmeter', string="Flowmeter", tracking=True)
    date = fields.Datetime(string="Date", default=fields.Datetime.now)
    area = fields.Selection(related='flowmeter_id.area', string="Flow Rate Area")
    reading_ids = fields.One2many('flowmeter.reading', 'sheet_id', string="Flowmeter Readings")
    stripping_id= fields.Many2one('stripping.log.sheet', 'Stripping Log')
    parent_flowmeter_id = fields.Many2one(
        "flowmeter.reading.sheet",
        string="Parent Flowmeter",
        store=True
    )
    child_ids = fields.One2many(
        "flowmeter.reading.sheet",
        "parent_flowmeter_id",
        string="Sub Readings"
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)

    def action_create_sub_reading(self):
        """Open form to create new sub reading"""
        return {
            "type": "ir.actions.act_window",
            "name": "Create Child Reading",
            "res_model": "flowmeter.reading.sheet",
            "view_mode": "form",
            "target": "current",
            "context": {"default_parent_flowmeter_id": self.id},
        }

    def action_open_sub_readings(self):
        """Smart button action to open sub readings"""
        return {
            "type": "ir.actions.act_window",
            "name": "Sub Readings",
            "res_model": "flowmeter.reading.sheet",
            "view_mode": "list,form",
            "domain": [("parent_flowmeter_id", "=", self.id)],
            "context": {"default_parent_flowmeter_id": self.id},
        }

    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('name', 'New') == 'New':
                val['name'] = self.env['ir.sequence'].next_by_code('flowmeter.log.sheet.sequence') or 'New'
        return super(FlowmeterReadingSheet, self).create(vals)

    def action_start(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'running'

    def action_done(self):
        for record in self:
            if record.state == 'running':
                record.state = 'done'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'


# Flow Meter Reading Model
class FlowmeterReading(models.Model):
    _name = 'flowmeter.reading'
    _description = 'Flowmeter Reading'
    _order = 'timestamp asc'

    timestamp = fields.Datetime(string="Times", required=True, default=fields.Datetime.now)
    sheet_id = fields.Many2one('flowmeter.reading.sheet', 'Flow Log')
    total_meter_reading = fields.Float(string="TOTALIZER READING (m³)", required=True, tracking=True)
    rate = fields.Float(string="FLOWRATE M³/Hr", tracking=True)
    hourly_flow = fields.Float(string="Flow since last reading (m³)", compute='_compute_flow_data', store=True)
    daily_flow = fields.Float(string="Total Flow Today (m³)", compute='_compute_flow_data', store=True)

    # Calculate Flow
    @api.depends('timestamp', 'total_meter_reading', 'sheet_id.flowmeter_id')
    def _compute_flow_data(self):
        for rec in self:
            if not rec.timestamp or not rec.sheet_id.flowmeter_id:
                rec.hourly_flow = 0.0
                rec.daily_flow = 0.0
                continue

            # Difference between this reading and the previous reading.
            previous = self.search([
                ('sheet_id.flowmeter_id', '=', rec.sheet_id.flowmeter_id.id),
                ('timestamp', '<', rec.timestamp)
            ], order='timestamp desc', limit=1)

            rec.hourly_flow = rec.total_meter_reading - previous.total_meter_reading if previous else 0.0

            # Daily_flow account modification starts at 6 AM
            timestamp = rec.timestamp

            # If the current time is before 6 AM, we go back to yesterday at 6 AM.
            if timestamp.hour < 4:
                start_of_day = (timestamp - timedelta(days=1)).replace(hour=4, minute=0, second=0, microsecond=0)
            else:
                start_of_day = timestamp.replace(hour=4, minute=0, second=0, microsecond=0)

            readings_today = self.search([
                ('sheet_id.flowmeter_id', '=', rec.sheet_id.flowmeter_id.id),
                ('timestamp', '>=', start_of_day),
                ('timestamp', '<=', rec.timestamp)
            ], order='timestamp asc')

            if readings_today:
                first_today = readings_today[0]
                if rec.id == first_today.id:
                    # First reading after 6 AM => daily_flow = 0
                    rec.daily_flow = 0.0
                else:
                    rec.daily_flow = rec.total_meter_reading - first_today.total_meter_reading
            else:
                rec.daily_flow = 0.0


# ADR log sheet
class AdrLogSheet(models.Model):
    _name = 'adr.log.sheet'
    _description = 'ADR Log Sheet'
    _order = 'date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    date = fields.Date(string="Date", required=True, default=fields.Date.today)
    line_ids = fields.One2many('adr.log.sheet.line', 'sheet_id', string="Readings")
    production_id = fields.Many2one('mrp.production', string="Manufacturing Order")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)

    avg_barren_cn = fields.Float(string="Avg Barren CN ppm")
    avg_barren_ph = fields.Float(string="Avg Barren pH")
    avg_barren_oxygen = fields.Float(string="Avg Barren Oxygen")

    avg_preg_cn = fields.Float(string="Avg Pregnant CN ppm")
    avg_preg_ph = fields.Float(string="Avg Pregnant pH")
    avg_preg_oxygen = fields.Float(string="Avg Pregnant Oxygen")

    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('name', 'New') == 'New':
                val['name'] = self.env['ir.sequence'].next_by_code('adr.log.sequence') or 'New'
        return super(AdrLogSheet, self).create(vals)

    def action_compute_averages(self):
        for sheet in self:
            lines = sheet.line_ids

            def avg(field_name):
                values = [getattr(l, field_name) for l in lines if getattr(l, field_name)]
                return sum(values) / len(values) if values else 0

            sheet.avg_barren_cn = avg('barren_cn')
            sheet.avg_barren_ph = avg('barren_ph')
            sheet.avg_barren_oxygen = avg('barren_oxygen')

            sheet.avg_preg_cn = avg('preg_cn')
            sheet.avg_preg_ph = avg('preg_ph')
            sheet.avg_preg_oxygen = avg('preg_oxygen')

    def action_start(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'running'

    def action_done(self):
        for record in self:
            if record.state == 'running':
                record.state = 'done'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'


# ADR Log Sheet Line
class AdrLogSheetLine(models.Model):
    _name = 'adr.log.sheet.line'
    _description = 'ADR Log Sheet Line'

    sheet_id = fields.Many2one('adr.log.sheet', string="Log Sheet", ondelete="cascade")
    time = fields.Datetime(string="Times", required=True, default=fields.Datetime.now)

    barren_cn = fields.Float(string="Barren CN ppm")
    barren_ph = fields.Float(string="Barren pH")
    barren_oxygen = fields.Float(string="Barren Oxygen")
    preg_cn = fields.Float(string="Pregnant CN ppm")
    preg_ph = fields.Float(string="Pregnant pH")
    preg_oxygen = fields.Float(string="Pregnant Oxygen")
    pond_barren = fields.Selection([('low', 'Low'), ('med', 'Medium'), ('high', 'High')], string="Barren Pond Level")
    pond_preg = fields.Selection([('low', 'Low'), ('med', 'Medium'), ('high', 'High')], string="Pregnant Pond Level")
    remarks = fields.Text(string="Remarks")


# Stripping  log sheet
class StrippingLogSheet(models.Model):
    _name = 'stripping.log.sheet'
    _description = 'Stripping Log Sheet'
    _order = 'date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    stripping_line_ids = fields.One2many('stripping.hourly.line', 'strrip_id', string='Stripping Hourly Data')
    workorder_id = fields.Many2one('mrp.workorder', 'Work Order')
    production_id = fields.Many2one('mrp.production', string="Manufacturing Order")
    date = fields.Date(string="Date", required=True, default=fields.Date.today)
    total_metal_recovery = fields.Float(string='Total Metal Recovery (g)', compute='_compute_total_recovery',store=True)

    avg_temperature = fields.Float(string="Avg temperature")
    avg_volt = fields.Float(string="Avg volt")
    avg_ampere = fields.Float(string="Avg ampere")
    metal_recovery = fields.Float(string="Avg Metal Recovery")
    recovery_percentage = fields.Float(string="Avg Recovery(%)")



    flowmeter_reading = fields.One2many('flowmeter.reading.sheet' , 'stripping_id' , 'Flowmeter Reading')
    flowmeter_count = fields.Integer(compute="_compute_flow_reading_request_count",
                                                   string="Chem-Assays")
    chemical_sample_request_count = fields.Integer(compute="_compute_chemical_sample_request_count",string="Chem-Assays")

    stripping_unit = fields.Selection([
        ('old', 'Old Cell'),
        ('new', 'New Cell')
    ], string="Stripping Unit")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)

    def action_compute_averages(self):
        for sheet in self:
            lines = sheet.stripping_line_ids

            values = [line.recovery_percentage for line in sheet.stripping_line_ids if
                      line.recovery_percentage is not None]
            sheet.recovery_percentage = sum(values) / len(values) if values else 0.0
            def avg(field_name):
                values = [getattr(l, field_name) for l in lines if getattr(l, field_name)]
                return sum(values) / len(values) if values else 0

            sheet.avg_temperature = avg('temperature')
            sheet.avg_volt = avg('volt')
            sheet.avg_ampere = avg('ampere')



    def _compute_chemical_sample_request_count(self):
        for record in self:
            record.chemical_sample_request_count = self.env['chemical.samples.request'].search_count([
                ('stripping_id', '=', record.id)
            ])

    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('name', 'New') == 'New':
                val['name'] = self.env['ir.sequence'].next_by_code('stripping.log.sheet.sequence') or 'New'
        return super(StrippingLogSheet, self).create(vals)



    @api.depends('stripping_line_ids.metal_recovery')
    def _compute_total_recovery(self):
        for record in self:
            record.total_metal_recovery = sum(
                line.metal_recovery for line in record.stripping_line_ids
            )

    def action_start(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'running'

    def action_done(self):
        for record in self:
            if record.state == 'running':
                record.state = 'done'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'


    def _compute_flow_reading_request_count(self):
        for record in self:
            record.flowmeter_count = self.env['flowmeter.reading.sheet'].search_count([
                ('stripping_id', '=', record.id)
            ])

    def create_flowmeter_reading(self):
        self.ensure_one()
        for record in self:
            new_reading = self.env['flowmeter.reading.sheet'].create({
                'stripping_id': record.id,
            })
            return {
                'type': 'ir.actions.act_window',
                'name': 'Flowmeter Reading',
                'res_model': 'flowmeter.reading.sheet',
                'res_id': new_reading.id,
                'view_mode': 'form',
                'context': {
                    'default_stripping_id': self.id,

                },
                'target': 'current',
            }

    def action_view_chemical_sample_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chem-Assays',
            'res_model': 'chemical.samples.request',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('stripping', '=', self.id)],
        }

    def create_checmical_lab_assy(self):
        return {
            'name': 'Chemical Samples',
            'type': 'ir.actions.act_window',
            'res_model': 'chemical.samples.request',
            'view_mode': 'form',
            'target': 'new',
            'domain': [('stripping_id', '=', self.id)],
            'context': {
                'default_stripping_id': self.id,
            },

        }




# Stripping Line
class StrippingHourlyLine(models.Model):
    _name = 'stripping.hourly.line'
    _description = 'Hourly Gold Stripping Reading'

    temperature = fields.Float(string='Temperature')
    volt = fields.Float(string='Volt')
    ampere = fields.Float(string='Ampere')
    strrip_id = fields.Many2one('stripping.log.sheet', string='Strripping Log Sheet', ondelete='cascade')

    time = fields.Datetime(string="Times", required=True, default=fields.Datetime.now)
    sample_number = fields.Integer("Sample No.")
    flow_rate = fields.Float(string='Flow Rate (m³/hr)',store=True)
    assay_barren = fields.Float(string='Assay Barren (g/t Au)', required=True)
    assay_pregnant = fields.Float(string='Assay Pregnant (g/t Au)', required=True)
    reading_id = fields.Many2one('flowmeter.reading', string="Flowmeter Reading")

    metal_recovery = fields.Float(string='Metal Recovery (g)', compute='_compute_metal_recovery', store=True, )
    recovery_percentage = fields.Float(string='Recovery Percentage', compute='_compute_metal_recovery', store=True, )

    @api.onchange('time')  # حقل بيتغير عند الإدخال
    def _onchange_time(self):
        self._set_flow_rate_once()
        
    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._set_flow_rate_once()
        return record

    def _set_flow_rate_once(self):
        for rec in self:
            if not rec.strrip_id:
                return
            sheets = rec.strrip_id.flowmeter_reading.filtered(lambda s: s.id)
            if not sheets:
                return
            latest_sheet = sheets.sorted('id', reverse=True)[0]
            readings = latest_sheet.reading_ids.filtered(lambda r: r.id)
            if not readings:
                return
            latest_reading = readings.sorted('id', reverse=True)[0]
            rec.flow_rate = latest_reading.hourly_flow


    @api.depends('flow_rate', 'assay_barren', 'assay_pregnant')
    def _compute_metal_recovery(self):
        for line in self:
            line.metal_recovery = line.flow_rate * (line.assay_pregnant - line.assay_barren)

            if line.assay_pregnant:
                line.recovery_percentage = ((line.assay_pregnant - line.assay_barren) / line.assay_pregnant) * 100
            else:
                line.recovery_percentage = 0.0

class IssuanceRequestInherit(models.Model):
    _inherit = 'issuance.request'

    creacher_log_id = fields.Many2one('crusher.log.sheet')



# Crusher Log Sheet
class CrusherLogSheet(models.Model):
    _name = 'crusher.log.sheet'
    _description = 'Crusher Log Sheet'
    _order = 'date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    date = fields.Date(string="Date", required=True, default=fields.Date.today)
    line_ids = fields.One2many('crusher.log.sheet.line', 'sheet_id', string="Crusher Readings")
    production_id = fields.Many2one('mrp.production', string="Manufacturing Order")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)

    avg_ph = fields.Float(string="Avg pH")
    avg_moisture = fields.Float(string="Avg Crusher Moisture")
    avg_under_crusher_moisture = fields.Float(string="Avg Under Crusher Moisture")
    avg_agg_moisture = fields.Float(string="Avg Agglomeration Moisture")

    avg_seiving = fields.Float(string="Avg Seiving")
    cement_load = fields.Float(string="Cement Load")
    form_type = fields.Selection(
        selection=[
            ('crusher', 'Crusher'),
            ('stacker', 'Stacker'),
        ],
        string='Form Type',
        default='crusher',
    )

    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('form_type') == 'crusher':

                val['name'] = (self.env['ir.sequence'].next_by_code('crusher.log.sequence')
                                or '/')
            elif val.get('form_type') == 'stacker':
                val['name'] = self.env['ir.sequence'].next_by_code('stacker.log.sequence') or '/'
        return super(CrusherLogSheet, self).create(vals)

    def action_compute_averages(self):
        for sheet in self:
            lines = sheet.line_ids

            def avg(field_name):
                values = [getattr(l, field_name) for l in lines if getattr(l, field_name)]
                return sum(values) / len(values) if values else 0

            sheet.avg_ph = avg('ph')
            sheet.avg_moisture = avg('moisture')
            sheet.avg_under_crusher_moisture = avg('pile_moisture')
            sheet.avg_agg_moisture = avg('agg_moisture')


    def action_start(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'running'

    def action_done(self):
        for record in self:
            if record.state == 'running':
                record.state = 'done'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'

    issuance_request_id = fields.Many2one('issuance.request', string='Issuance Request')
    company_id = fields.Many2one('res.company',string='Company',default=lambda self: self.env.company,required=True,index=True)

    def action_create_issuance_request(self):
        for rec in self:
            issuance = self.env['issuance.request'].create({
                'creacher_log_id': rec.id,
                'request_date': fields.Date.today(),
                'company_id': self.env.company.id,

            })
            rec.issuance_request_id = issuance.id

            return {
                'type': 'ir.actions.act_window',
                'name': 'Issuance Request',
                'res_model': 'issuance.request',
                'view_mode': 'form',
                'res_id': issuance.id,
                'target': 'current',
                'context': {
                    'default_company_id': self.env.company.id,
                    'force_company': self.env.company.id,  # مهم أحيانًا لتحديد الشركة بشكل صريح
                },
            }


# Crusher Log  line
class CrusherLogSheetLine(models.Model):
    _name = 'crusher.log.sheet.line'
    _description = 'Crusher Log Sheet Line'

    sheet_id = fields.Many2one('crusher.log.sheet', string="Crusher Sheet", ondelete="cascade")
    time = fields.Datetime(string="Times", required=True, default=fields.Datetime.now)

    ph = fields.Float(string="PH")

    moisture = fields.Float(string="Cru Moisture")
    pile_moisture = fields.Float(string="Stockpile Moisture")
    agg_moisture = fields.Float(string="Agglomeration Moisture")
    cement_rate = fields.Float(string="Cement Rate")

    remarks = fields.Text(string="Remarks")


#BeltScale
class BeltScaleLog(models.Model):
    _name = "belt.scale.log"
    _description = "Belt Scale Log Sheet"
    _order = "date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    date = fields.Date(string="Date", required=True, default=fields.Date.today)
    reading_ids = fields.One2many('belt.reading', 'sheet_id', string="Belt Scale Readings")
    production_id = fields.Many2one('mrp.production', string="Manufacturing Order")


    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)

    form_type = fields.Selection(
        selection=[
            ('crusher', 'Crusher'),
            ('stacker', 'Stacker'),
        ],string='Form Type',default='crusher',
    )

    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('form_type') == 'crusher':
                val['name'] = (self.env['ir.sequence'].next_by_code('crusher.belt.scale.reading') or '/')
            elif val.get('form_type') == 'stacker':
                val['name'] = self.env['ir.sequence'].next_by_code('stacker.belt.scale.reading') or '/'
        return super(BeltScaleLog, self).create(vals)


    def action_start(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'running'

    def action_done(self):
        for record in self:
            if record.state == 'running':
                record.state = 'done'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'


class BelyReading(models.Model):
    _name = 'belt.reading'
    _description = 'BeltE Scaling Reading'
    _order = 'timestamp asc '

    timestamp = fields.Datetime(string="Times", required=True, default=fields.Datetime.now)
    sheet_id = fields.Many2one('belt.scale.log', 'Belt Log')
    total_ton_reading = fields.Float(string="TOTALIZER READING (Ton)", required=True, tracking=True)
    rate = fields.Float(string="RATE Ton/Hr", tracking=True)
    hourly_ton= fields.Float(string="Ton since last reading (Ton)", compute='_compute_ton_diff', store=True)

    # Calculate Flow
    @api.depends('timestamp', 'total_ton_reading')
    def _compute_ton_diff(self):
        for rec in self:
            if not rec.timestamp :
                rec.hourly_ton = 0.0
                continue

            # Difference between this reading and the previous reading.
            previous = self.search([
                ('sheet_id', '=', rec.sheet_id.id),
                ('timestamp', '<', rec.timestamp)
            ], order='timestamp desc', limit=1)

            rec.hourly_ton = rec.total_ton_reading - previous.total_ton_reading if previous else 0.0




# Pregnant sample list Model
class PregnantListSample(models.Model):
    _name = 'pregnant.sample.result'
    _description = 'Pregnant Sample'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    date = fields.Datetime(string='Date', default=fields.Date.today)
    pregnant_sample = fields.Float(string="Pregnant Sample Result")
    barren_sex = fields.Float(string="Barren Sex")

    chemical_sample_result_count = fields.Integer(compute="_compute_chemical_sample_result_count",
                                                   string="Chem-Assays")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)


    production_id = fields.Many2many('mrp.production' , 'pregnant_result_production' , 'pregnant_result_id' , 'production_id' , string="Manufacture Order" , required=True)

    type = fields.Selection([('ps','PS Sample'),('bs','BS6 Sample')], string='Type', default='ps', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        for val in vals:
            if val.get('type') == 'ps':
                val['name'] = (self.env['ir.sequence'].next_by_code('pregnant.result') or '/')
            elif val.get('type') == 'bs':
                val['name'] = (self.env['ir.sequence'].next_by_code('barren.result') or '/')
        return super(PregnantListSample, self).create(vals)

    def _compute_chemical_sample_result_count(self):
        for record in self:
            record.chemical_sample_result_count = self.env['chemical.samples.request'].search_count([
                ('pregnant_result', '=', record.id)
            ])


    def create_checmical_lab_assy(self):
        if self.type == 'ps':
            return {
                'name': 'Chemical Samples',
                'type': 'ir.actions.act_window',
                'res_model': 'chemical.samples.request',
                'view_mode': 'form',
                'target': 'new',
                'domain': [('pregnant_result', '=', self.id)],
                'context': {
                    'default_pregnant_result': self.id,
                    'default_company_id': self.company_id.id,
                    'default_sample_type' : 'cic',
                    'default_cic_samples' : 'factory',
                    'default_cic_sub_samples' : 'pregnant_sample',
                },

            }
        elif self.type == 'bs':
            return {
                'name': 'Chemical Samples',
                'type': 'ir.actions.act_window',
                'res_model': 'chemical.samples.request',
                'view_mode': 'form',
                'target': 'new',
                'domain': [('pregnant_result', '=', self.id)],
                'context': {
                    'default_pregnant_result': self.id,
                    'default_company_id': self.company_id.id,
                    'default_sample_type': 'cic',
                    'default_cic_samples': 'factory',
                    'default_cic_sub_samples': 'bs_6',
                },

            }

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals and vals['state'] == 'done':
            print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>..")
            for rec in self:
                rec._update_workorder()
        return res

    def _update_workorder(self):
        for rec in self:
            for mo in rec.production_id:
                for wo in mo.workorder_ids:
                    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>..")
                    if rec.type in 'ps':
                        wo.write({'au_Inlet': rec.pregnant_sample})
                    elif rec.type in 'bs':
                        wo.write({'au_Outlet': rec.pregnant_sample})

