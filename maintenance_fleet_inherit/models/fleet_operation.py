from odoo import models, fields, api, _
from datetime import date, timedelta
from odoo.exceptions import UserError, ValidationError


class FleetOperation(models.Model):
    _name = 'fleet.operation'
    _description = 'Fleet Daily Operation'
    _rec_name = 'date'
    _order = 'date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    date = fields.Date(string='Date', default=lambda self: fields.Date.context_today(self), tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self._get_employee(), tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', default=lambda self: self._get_default_department())

    start_day = fields.Float(string='Start Shift (Day)', tracking=True)
    end_day = fields.Float(string='End Shift (Day)', tracking=True)
    start_night = fields.Float(string='Start Shift (Night)', tracking=True)
    end_night = fields.Float(string='End Shift (Night)', tracking=True)

    odometer_ids = fields.One2many('fleet.vehicle.odometer.line', 'operation_id', string='Odometer Lines')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('closed', 'Closed'),
        ('cancel', 'Canceled'),
    ], string='Status', default='draft', tracking=True)

    def action_draft_fleet(self):
        for record in self:
            record.state = 'draft'

    def action_closed_fleet(self):
        for record in self:
            record._update_vehicle_odometers()
            record.state = 'closed'

    def action_cancel_fleet(self):
        for record in self:
            record.state = 'cancel'

    # ---------- Helper methods ----------
    def _get_employee(self):
        return self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1).id

    def _get_default_department(self):
        emp = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1)
        return emp.department_id.id if emp and emp.department_id else False

    def _get_or_create_vehicle_location(self, location_name):
        if not location_name:
            return False
        location = self.env['vehicle.location'].sudo().search([('name', '=', location_name)], limit=1)
        if not location:
            location = self.env['vehicle.location'].sudo().create({'name': location_name})
        return location.id

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Only draft records can be deleted!")

        return super(FleetOperation, self).unlink()
    # ---------- Default Get ----------
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        today = date.today()
        yesterday = today - timedelta(days=1)

        previous_operations = self.env['fleet.operation'].search([],order='create_date desc', limit=1)
        odometer_lines = []

        if previous_operations:
            # الحالة 1: جلب بيانات الأمس

            # 💡 يتم فرز سجلات الأمس حسب custom_sequence قبل الإضافة
            previous_lines_sorted = previous_operations.odometer_ids.sorted(key=lambda r: r.custom_sequence)

            for line in previous_lines_sorted:
                odometer_lines.append((0, 0, {
                    'vehicle_id': line.equipment_id.vechicle_id.id,
                    'equipment_id': line.equipment_id.id,
                    'location_id': line.location_id.id if line.location_id else False,
                    'type_of': line.type_of or False,
                    'start_value': line.end_value,
                    'day_type': line.day_type,
                    'operation_type': line.operation_type,
                }))
        else:
            # الحالة 2: جلب المعدات الجديدة

            # 💡 يتم جلب المعدات مع الترتيب مباشرةً في الاستعلام
            equipments = self.env['maintenance.equipment'].search(
                [('custom_sequence', '>', 0)],
                order='custom_sequence asc'  # 👈🏻 الترتيب حسب custom_sequence
            )

            odometer_lines = [(0, 0, {
                'equipment_id': eq.id,
                'vehicle_id': eq.vechicle_id.id,
                'location_id': eq.location if hasattr(eq, 'location') else False,
                'type_of': eq.type_of_equipment or False,
                'start_value': 0.0,
                'end_value': 0.0,
                'day_type': 'd_s',
                'operation_type': 'operation',
            }) for eq in equipments]

        res['odometer_ids'] = odometer_lines
        return res

    # ---------- تحديث العدادات ----------
    # def _update_vehicle_odometers(self):
    #     print("\n==== Updating Vehicle Odometers ====\n")
    #     Odometer = self.env['fleet.vehicle.odometer']
    #     for rec in self:
    #         for line in rec.odometer_ids:
    #             print(f"Processing line for equipment: {line.equipment_id.name}, vehicle: {line.vehicle_id.name}")
    #             # تحديد أو إنشاء الموقع
    #             location_id = line.location_id.id or self._get_or_create_vehicle_location(
    #                 getattr(line.vehicle_id, 'location', False)
    #             )

    #             # تحديد مفتاح البحث (المعدة أولًا، ثم المركبة)
    #             domain = [
    #                 ('date', '=', rec.date),
    #                 ('equipment_id', '=', line.equipment_id.id)
    #             ]
    #             if line.vehicle_id:
    #                 domain.append(('vehicle_id', '=', line.vehicle_id.id))



    #             # البحث أو الإنشاء
    #             existing = Odometer.search(domain, limit=1)
    #             print(f"  Found existing odometer? {bool(existing)} domain={domain}")
    #             if vehicle.company_id and vehicle.company_id not in self.env.user.company_ids:
    #                 raise UserError(f"Vehicle {vehicle.name} belongs to another company")
    #             vals = {
    #                 'date': rec.date,
    #                 'vehicle_id': line.vehicle_id.id,
    #                 'equipment_id': line.equipment_id.id,
    #                 'location_id': line.location_id.id,
    #                 'value': line.end_value,
    #                 'start_value': line.start_value,
    #             }

    #             if existing:
    #                 print("  → Updating existing odometer record")
    #                 existing.write(vals)
    #             else:
    #                 print("  → Creating new odometer record")
    #                 Odometer.create(vals)
    def _update_vehicle_odometers(self):
        print("\n==== Updating Vehicle Odometers ====\n")
        Odometer = self.env['fleet.vehicle.odometer']
        for rec in self:
            for line in rec.odometer_ids:
                print(f"Processing line for equipment: {line.equipment_id.name}, vehicle: {line.vehicle_id.name}")
                
                # التحقق من الصلاحيات والشركة باستخدام line.vehicle_id
                if line.vehicle_id:
                    # هنا تم تصحيح الخطأ: استبدال vehicle بـ line.vehicle_id
                    if line.vehicle_id.company_id and line.vehicle_id.company_id not in self.env.user.company_ids:
                        raise UserError(f"Vehicle {line.vehicle_id.name} belongs to another company")

                # تحديد أو إنشاء الموقع
                location_id = line.location_id.id or self._get_or_create_vehicle_location(
                    getattr(line.vehicle_id, 'location', False)
                )

                # تحديد مفتاح البحث (المعدة أولًا، ثم المركبة)
                domain = [
                    ('date', '=', rec.date),
                    ('equipment_id', '=', line.equipment_id.id)
                ]
                if line.vehicle_id:
                    domain.append(('vehicle_id', '=', line.vehicle_id.id))

                # البحث أو الإنشاء
                existing = Odometer.search(domain, limit=1)
                
                vals = {
                    'date': rec.date,
                    'vehicle_id': line.vehicle_id.id,
                    'equipment_id': line.equipment_id.id,
                    'location_id': location_id, # تم استخدام المتغير المحسوب أعلاه
                    'value': line.end_value,
                    'start_value': line.start_value,
                }

                if existing:
                    existing.sudo().write(vals)
                else:
                    Odometer.sudo().create(vals)

    # ---------- تحديث المدد تلقائيًا ----------
    @api.onchange('start_day', 'end_day', 'start_night', 'end_night')
    def _onchange_shift_hours(self):
        """عند تعديل أي من ساعات الورديات، يتم تحديث المدد في جميع السطور"""
        for rec in self:
            for line in rec.odometer_ids:
                line._compute_durations()

    def write(self, vals):
        res = super().write(vals)
        # self._update_vehicle_odometers()
        return res

    def create(self, vals):
        record = super().create(vals)
        # record._update_vehicle_odometers()
        return record


class FleetVehicleOdometerLine(models.Model):
    _name = 'fleet.vehicle.odometer.line'
    _description = 'Fleet Odometer Daily Line'

    operation_id = fields.Many2one('fleet.operation', string='Operation', ondelete='cascade')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Equipment Name')
    equipment_id = fields.Many2one('maintenance.equipment', 'Equipment Type', ondelete="cascade")
    equipment_code = fields.Char(string='Equipment Code', compute='_compute_equipment_code', store=True)
    location_id = fields.Many2one('vehicle.location', string='Location', tracking=True)
    start_value = fields.Float(string='Start Value', tracking=True)
    end_value = fields.Float(string='End Value', tracking=True)
    custom_sequence = fields.Integer("sequence",related='equipment_id.custom_sequence')
    type_of = fields.Char(string='Type', related='equipment_id.type_of_equipment')

    day_type = fields.Selection(
        [('d_s', 'Day Shift'), ('n_s', 'Night Shift'), ('d_n_s', 'Day & Night Shift')],
        string="Type Of Shift", default='d_s', tracking=True
    )
    operation_type = fields.Selection(
        [('operation', 'Operational'), ('non_operation', 'Non Operational')],
        string="Operation Type", default='operation', tracking=True
    )

    day_duration = fields.Float(string='Target.hrs', compute='_compute_durations', store=True)
    distance = fields.Float(string='Actual.hrs', compute='_compute_distance', store=True)

    @api.constrains('start_value', 'end_value')
    def _check_start_end_values(self):
        for rec in self:
            if rec.end_value < rec.start_value:
                raise ValidationError(_("End Value cannot be less than Start Value."))

    @api.depends('equipment_id')
    def _compute_equipment_code(self):
        for rec in self:
            rec.equipment_code = rec.equipment_id.code if rec.equipment_id else ''

    # 🧮 الحقول التحليلية الجديدة
    downtime_hrs = fields.Float(string='Downtime.hrs', compute='_compute_analysis_fields', store=True)
    standby_hrs = fields.Float(string='Standby.hrs', compute='_compute_analysis_fields', store=True)
    available_hrs = fields.Float(string='Available.hrs', compute='_compute_analysis_fields', store=True)
    fuel_consumption = fields.Float(string='Fuel Cons. (L)', compute='_compute_analysis_fields', store=True)
    fuel_per_hr = fields.Float(string='Fuel/L-H', compute='_compute_analysis_fields', store=True)
    availability = fields.Float(string='Availability %', compute='_compute_analysis_fields', store=True)
    utilization = fields.Float(string='Utilization %', compute='_compute_analysis_fields', store=True)
    supposed_fuel = fields.Float(string='Supposed Fuel L/H', compute='_compute_analysis_fields', store=True)

    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):
        for rec in self:
            if rec.equipment_id and hasattr(rec.equipment_id, 'vehicle_id'):
                rec.vehicle_id = rec.equipment_id.vehicle_id.id

    # ==================================================
    # 1️⃣ حساب المسافة (عدد ساعات التشغيل الفعلية)
    # ==================================================
    @api.depends('start_value', 'end_value')
    def _compute_distance(self):
        for rec in self:
            rec.distance = rec.end_value - rec.start_value if rec.end_value and rec.start_value else 0.0

    # ==================================================
    # 2️⃣ حساب عدد الساعات حسب نوع الوردية
    # ==================================================
    @api.depends('day_type', 'operation_id.start_day', 'operation_id.end_day', 'operation_id.start_night', 'operation_id.end_night')
    def _compute_durations(self):
        """حساب المدة بناءً على نوع الوردية"""
        for rec in self:
            op = rec.operation_id
            day_duration = 0.0
            night_duration = 0.0

            if op.start_day and op.end_day:
                duration = op.end_day - op.start_day
                day_duration = duration if duration >= 0 else 24 + duration

            if op.start_night and op.end_night:
                duration = op.end_night - op.start_night
                night_duration = duration if duration >= 0 else 24 + duration

            if rec.day_type == 'd_s':
                rec.day_duration = day_duration
            elif rec.day_type == 'n_s':
                rec.day_duration = night_duration
            elif rec.day_type == 'd_n_s':
                rec.day_duration = day_duration + night_duration
            else:
                rec.day_duration = 0.0

    # ==================================================
    # 3️⃣ الحقول التحليلية (نفس منطق التقرير)
    # ==================================================
    @api.depends('distance', 'day_duration', 'equipment_id')
    def _compute_analysis_fields(self):
        for rec in self:
            target_hrs = rec.day_duration or 11.0
            actual_hrs = rec.distance or 0.0

            # ⏱ Downtime (من maintenance.request)
            downtime_hrs = 0.0
            if rec.equipment_id:
                requests = rec.env['maintenance.request'].search([
                    ('equipment_id', '=', rec.equipment_id.id),
                    ('stage_id.name', 'not in', ['Cancelled', 'Rejected'])
                ])
                for req in requests:
                    if req.request_date_time and req.complete_datetime:
                        delta = req.complete_datetime - req.request_date_time
                        downtime_hrs += delta.total_seconds() / 3600.0

            # 💤 Standby = Target - Actual + Downtime
            standby_hrs = target_hrs - actual_hrs + downtime_hrs
            available_hrs = actual_hrs + standby_hrs

            # ⛽ Fuel Consumption (من issuance.request.line)
            fuel_consumption = 0.0
            if rec.equipment_id:
                fuel_lines = rec.env['issuance.request.line'].search([
                    '|',
                    ('product_id.categ_id.name', 'ilike', 'Gasoline'),
                    ('product_id.categ_id.name', 'ilike', 'General Material / Gasoline'),
                    ('equipment_id', '=', rec.equipment_id.id)
                ])
                fuel_consumption = sum(line.qty_issued for line in fuel_lines)

            fuel_per_hr = fuel_consumption / actual_hrs if actual_hrs else 0.0

            # ⚙ نسب الأداء
            total_time = actual_hrs + downtime_hrs + standby_hrs
            availability = (available_hrs / total_time * 100) if total_time > 0 else 0.0
            utilization = (actual_hrs / (actual_hrs + standby_hrs) * 100) if (actual_hrs + standby_hrs) > 0 else 0.0
            supposed_fuel = actual_hrs * 14

            # تحديث الحقول
            rec.downtime_hrs = downtime_hrs
            rec.standby_hrs = standby_hrs
            rec.available_hrs = available_hrs
            rec.fuel_consumption = fuel_consumption
            rec.fuel_per_hr = fuel_per_hr
            rec.availability = availability
            rec.utilization = utilization
            rec.supposed_fuel = supposed_fuel
