from odoo import models, fields, api, _
from odoo.exceptions import  UserError


class ExcavationWorkPermit(models.Model):
    _name = 'excavation.work.permit'
    _description = 'Digging and Excavation Work Permit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'


    def unlink(self):
        if self.state != 'draft':
            raise UserError("You cannot delete this Excavation Work Permit. Only DRAFT records can be deleted.")
        return super(ExcavationWorkPermit, self).unlink()

    name = fields.Char(string='Permit Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'مسودة / Draft'),
        ('submitted', 'انتظار الاعتماد / Pending Approval'),
        ('authorized', 'تم التصريح / Authorized'),
        ('issued', 'نشط / Issued'),
        ('pending_extension', 'بانتظار موافقة التمديد'),
        ('extended', 'ممدد / Extended'),
        ('suspend', 'تجميد / Suspension'),
        ('revoked', 'ملغى / Revoked'),
        ('pending_close', 'بانتظار موافقة الإغلاق'),
        ('closed', 'مغلق / Closed'),
        ('done', 'تم / Done'),
        ('reject', 'ملغي / Reject')
    ], default='draft', string='الحالة / Status', tracking=True)
    reason_reject = fields.Text(string='Reject Reason', tracking=True)
    extension_reason = fields.Text(string='سبب التمديد / Extension Reason')
    closing_reason = fields.Text(string='التعليق / Comment')
    department_id = fields.Many2one('hr.department', string='القسم / Department',
                                    default=lambda self: self.env.user.employee_id.department_id)
    # الجزء الأول: معلومات عامة وأبعاد الحفر
    date = fields.Datetime(string='Date / التاريخ', default=fields.Date.context_today)
    date_from = fields.Datetime(string='Valid From / صالح من')
    date_to = fields.Datetime(string='Valid To / إلى')
    location = fields.Many2one('work.site',string='Exact Location / الموقع الدقيق',ondelete='set null', tracking=True)
    sub_location = fields.Char(string='الموقع الفرعي / Sub Location', tracking=True)
    task_description = fields.Text(string='Description of Task / وصف المهمة')
    requester_id = fields.Many2one('res.users', string='Requester / مقدم الطلب', default=lambda self: self.env.user)

    # أبعاد الحفر
    exc_length = fields.Float(string='Length / الطول (m)')
    exc_width = fields.Float(string='Width / العرض (m)')
    exc_depth = fields.Float(string='Depth / العمق (m)')
    PRECAUTION_STATES = [('yes', 'نعم / Yes'), ('no', 'لا / No'), ('na', 'لا ينطبق / N/A')]
    # الجزء الثاني: تحديد المخاطر (Boolean Fields)
    # الجزء رقم #20أ: المخاطر المرتبطة بالحفر والتنقيب
    hazard_personnel_fall = fields.Selection(PRECAUTION_STATES,string='Personnel Fall / سقوط الأفراد')
    hazard_underground_utility = fields.Boolean(string='Underground Utility / المرافق تحت الأرض')
    hazard_biological = fields.Selection(PRECAUTION_STATES,string='Biological Hazards / المخاطر البيولوجية')
    hazard_falling_objects = fields.Selection(PRECAUTION_STATES,string='Falling Objects/Equipment / سقوط الأجسام أو المعدات')
    hazard_soil_collapse = fields.Selection(PRECAUTION_STATES,string='Soil Collapse / انهيار التربة')
    hazard_dust = fields.Selection(PRECAUTION_STATES,string='Dust / الغبار')
    hazard_floods = fields.Selection(PRECAUTION_STATES,string='Floods (Water Immersion) / الغمر المائي')
    hazard_structural_damage = fields.Selection(PRECAUTION_STATES,string='Structural Damage / تضرر الهيكل')
    hazard_heat = fields.Selection(PRECAUTION_STATES,string='Heat / الحرارة')
    hazard_vibration = fields.Selection(PRECAUTION_STATES,string='Vibrations / الاهتزازات')
    hazard_traffic = fields.Selection(PRECAUTION_STATES,string='Traffic / حركة المرور')
    hazard_noise_excavation = fields.Selection(PRECAUTION_STATES,string='Noise / الضوضاء')
    hazard_excavation_other = fields.Char(string='Other Excavation Hazards / مخاطر أخرى')

    # طرق الكشف عن المرافق تحت الأرض
    detection_method = fields.Selection([
        ('maps', 'Maps/Drawing / الخرائط والرسومات'),
        ('detector', 'Line Locator/Detector / جهاز الكشف'),
        ('manual', 'Manual Digging / الحفر اليدوي')
    ], string='Underground Detection Method')
    detector_sn = fields.Char(string='Serial/Code / الرقم التسلسلي')
    calibration_date = fields.Date(string='Calibration Date / تاريخ المعايرة')
    # --- الجزء الأول: البيانات الأساسية (تكملة) ---
    performer_id = fields.Many2one('res.partner', string='Performer / المنفذ')
    num_workers = fields.Integer(string='Number of Workers / عدد العمال')  # [cite: 87]
    equipment_type = fields.Char(string='Type of Equipment / نوع المعدة')  # [cite: 87]

    # الجزء رقم #02: الاحتياطات الوقائية المطلوبة لإكمال العمل بأمان
    # تم تعريف الخيارات في متغير خارجي لتسهيل استخدامه


    prec_jsa_attached = fields.Selection(PRECAUTION_STATES, string='JSA prepared/attached / هل تم إعداد وتحليل السلامة الوظيفي (JSA) ومراجعته وإرفاقه؟')
    prec_underground_checked = fields.Selection(
        PRECAUTION_STATES,
        string='Underground Utilities Verification / التحقق من المرافق تحت الأرض',
        help='Are underground utilities checked by detector or drawings (Electric, Telecom, Water, Fuel, etc.) / هل تم التحقق من وجود المرافق تحت الأرض (كهرباء، اتصالات، مياه، وقود، إلخ)'
    )
    prec_loto_effective = fields.Selection(PRECAUTION_STATES, string='Has the LOTO procedures effectively implemented?  / هل تم تنفيذ إجراءات القفل والعزل (LOTO) بشكل فعال؟')
    prec_equipment_certified = fields.Selection(PRECAUTION_STATES, string='Are the equipment’s/machines inspected and valid certifications available for equipment & operator? / هل تم فحص المعدات/الآلات، وهل الشهادات اللازمة للمعدات والمشغلين متاحة وصالحة؟')
    prec_work_obstructions = fields.Selection(PRECAUTION_STATES, string='Are there any obstacles within the working zone? such as overhead cables; structures; mobile or fixed assets, others  / هل هناك أي عوائق داخل منطقة العمل؟')
    prec_physical_barriers = fields.Selection(PRECAUTION_STATES, string='Are the physical barriers in place within at least 3 meters from the excavation? Such as Barricades, traffic cones, others/هل تم وضع الحواجز المادية على بعد 3 أمتار على الأقل من منطقة الحفر؟')
    prec_worker_equipment_interference = fields.Selection(PRECAUTION_STATES, string='Is there any interference between the worker & equipment during the job/task? / هل يوجد أي تداخل بين العمال والمعدات أثناء تنفيذ العمل/المهمة؟')
    prec_other_tasks_required = fields.Selection(PRECAUTION_STATES, string='Is the job/task require any worker to do any job/task in any capacity during or after excavation? / هل يتطلب العمل/المهمة قيام أي عامل بتنفيذ أي مهمة أخرى أثناء أو بعد الحفر؟')
    prec_fall_trip_hazards = fields.Selection(PRECAUTION_STATES, string='Is there any fall and trip hazard within the specified working area? / هل هناك أي مخاطر سقوط أو تعثر داخل منطقة العمل المحددة؟')
    prec_ppe_compliance = fields.Selection(PRECAUTION_STATES, string='necessary PPE made available and committee to use / هل تم توفير معدات الحماية الشخصية (PPE) والتأكد من الالتزام باستخدامها؟')
    prec_fire_extinguisher_ready = fields.Selection(PRECAUTION_STATES, string='هل معدات مكافحة الحرائق مناسبة / متاحة / جاهزة للاستخدام، إن وجدت؟ / fire equipment are suitable / available/ready to use, if any')
    additional_controls = fields.Text(string='Additional Controls / إجراءات التحكم الإضافية المطلوبة')
    # --- الجزء الثالث: المصادقة (Authorization) --- # [cite: 92, 97]
    operator_signature = fields.Binary(string='Operator Signature / توقيع المشغل')
    authorizer_id = fields.Many2one('hr.employee', string='Authorizer (Supervisor)')
    authorizer_sig = fields.Binary(string='Authorizer Signature')
    issuer_id = fields.Many2one('hr.employee', string='Issuer (Safety Officer)')
    issuer_sig = fields.Binary(string='Issuer Signature')

    # --- الجزء الرابع: التمديد والإغلاق (Extension & Closure) --- # [cite: 98, 99]
    close_backfilled = fields.Boolean(string='Trenches backfilled / ردم الخنادق')
    close_withdrawn = fields.Boolean(string='Men/Tools withdrawn / سحب الأفراد والأدوات')
    close_loto_removed = fields.Boolean(string='LOTO Removed / إزالة القفل والعزل')
    closure_date = fields.Datetime(string='Closure Date / تاريخ الإغلاق')

    is_need_ptw = fields.Boolean(string='Is Need PTW? / هل يحتاج الي تصريح عمل اخر', default=False)
    type_of_ptw = fields.Selection([
        ('hot_work', 'Hot Work Permit'),
        ('blasting', 'Blasting Space Permit'),
        ('cold_work', 'Cold Work Permit'),
        ('confined', 'Confined Space Permit'),
        ('highway', 'High Work Permit'),
        ('lifting', 'Lifting Work Permit'),
        ('loto', 'Loto Work Permit'),
    ], string='Type Of PTW / نوع تصريح العمل')
    linked_hot_ptw = fields.Many2one('hot.work.permit', string='Related PTW', readonly=True)
    linked_blasting_ptw = fields.Many2one('blasting.work.permit', string='Related PTW', readonly=True)
    linked_cold_ptw = fields.Many2one('cold.work.permit', string='Related PTW', readonly=True)
    linked_confined_ptw = fields.Many2one('confined.space.permit', string='Related PTW', readonly=True)
    linked_highway_ptw = fields.Many2one('work.height.permit', string='Related PTW', readonly=True)
    linked_lifting_ptw = fields.Many2one('lifting.work.permit', string='Related PTW', readonly=True)
    linked_loto_ptw = fields.Many2one('loto.work.permit', string='Related PTW', readonly=True)

    linked_ptw_count = fields.Integer(compute='_compute_linked_ptw_count')
    # الحقول الجديدة
    closed_date = fields.Datetime(string='تاريخ الإغلاق / Closing Date', readonly=True)
    duration_display = fields.Char(string='مدة التصريح / Duration', compute='_compute_duration')
    confirmation_check = fields.Boolean(
        string='أقر بأن جميع البيانات صحيحة وموافق على كافة إرشادات السلامة / I confirm that all information is correct and I agree to all safety instructions',
        required=True
    )

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('excavation.work.permit') or ' '

        return super(ExcavationWorkPermit, self).create(vals)

    def _compute_linked_ptw_count(self):
        for rec in self:
            # يجمع أي سجل مرتبك في الحقول التي عرفتها أنت
            counts = [rec.linked_hot_ptw, rec.linked_blasting_ptw, rec.linked_cold_ptw,
                      rec.linked_confined_ptw, rec.linked_highway_ptw, rec.linked_lifting_ptw, rec.linked_loto_ptw]
            rec.linked_ptw_count = len([c for c in counts if c])

    def action_create_related_ptw(self):
        self.ensure_one()
        if not self.type_of_ptw:
            raise UserError("الرجاء اختيار نوع التصريح أولاً / Please select PTW type first")

        ptw_map = {
            'hot_work': {'model': 'hot.work.permit', 'field': 'linked_hot_ptw'},
            'blasting': {'model': 'blasting.work.permit', 'field': 'linked_blasting_ptw'},
            'cold_work': {'model': 'cold.work.permit', 'field': 'linked_cold_ptw'},
            'confined': {'model': 'confined.space.permit', 'field': 'linked_confined_ptw'},
            'highway': {'model': 'work.height.permit', 'field': 'linked_highway_ptw'},
            'lifting': {'model': 'lifting.work.permit', 'field': 'linked_lifting_ptw'},
            'loto': {'model': 'loto.work.permit', 'field': 'linked_loto_ptw'},
        }

        # منع التكرار
        target = ptw_map.get(self.type_of_ptw)
        if target and getattr(self, target['field']):
            raise UserError("تم إنشاء هذا التصريح مسبقاً / This permit is already created")

        # إنشاء السجل في الموديول المستهدف
        new_record = self.env[target['model']].create({
            'work_site': self.work_site.id,
            'task_description': f"مرتبط بتصريح العمل الساخن رقم: {self.name}",
            'date_from': self.date_from,
            'date_to': self.date_to,
            'requester_id': self.requester_id.id,
        })

        # ربط السجل الجديد بالسجل الحالي
        self.write({target['field']: new_record.id})

        return {
            'name': 'الفتح التصريح الجديد',
            'type': 'ir.actions.act_window',
            'res_model': target['model'],
            'res_id': new_record.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # دالة الزر الذكي لفتح التصريح المرتبط
    def action_view_linked_ptw(self):
        self.ensure_one()
        ptw_map = {
            'hot_work': 'linked_hot_ptw', 'blasting': 'linked_blasting_ptw', 'confined': 'linked_confined_ptw',
            'cold_work': 'linked_cold_ptw', 'highway': 'linked_highway_ptw',
            'lifting': 'linked_lifting_ptw', 'loto': 'linked_loto_ptw'
        }
        target_field = ptw_map.get(self.type_of_ptw)
        res = getattr(self, target_field)

        return {
            'type': 'ir.actions.act_window',
            'res_model': res._name,
            'res_id': res.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_submit(self):
        for rec in self:
            if not rec.confirmation_check:
                raise UserError(
                    "يجب عليك الموافقة على صحة البيانات وإرشادات السلامة قبل إرسال الطلب! / You must confirm that all information is correct before submitting.")
            if rec.is_need_ptw:
                related_ptws = [rec.linked_hot_ptw, rec.linked_blasting_ptw, rec.linked_confined_ptw,
                                rec.linked_excavation_ptw, rec.linked_highway_ptw, rec.linked_lifting_ptw,
                                rec.linked_loto_ptw]

                for ptw in related_ptws:
                    if ptw and ptw.state not in ['issued']:
                        raise UserError(f"لا يمكن الاعتماد! التصريح المرتبط ({ptw.name}) لا يزال في حالة {ptw.state}")

            # التعديل هنا: نغير الحالة أولاً ثم نستدعي الأنشطة
            rec.state = 'submitted'
            rec.action_update_activities()

    # تعديل دالة action_authorize لتسجيل الشخص الذي اعتمد الطلب
    def action_authorize(self):
        for rec in self:
            employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            if employee:
                rec.issuer_id = employee.id

            rec.state = 'issued'  # أو 'authorized' حسب ما تفضله
            rec.action_update_activities()

    def action_reactivate(self):
        for rec in self:
            rec.state = 'issued'
            rec.action_update_activities()

    def action_close(self):
        self.state = 'closed'
        self.action_update_activities()

    def action_revoked(self):
        self.state = 'revoked'
        self.action_update_activities()

    def action_suspend(self):
        self.state = 'suspend'
        self.action_update_activities()

    def action_extend(self):
        self.state = 'extended'
        self.action_update_activities()

    def action_request_extension(self):
        self.state = 'pending_extension'

    def action_request_close(self):
        self.state = 'pending_close'

    def action_done(self):
        for rec in self:
            rec.state = 'pending_close'

    @api.depends('closed_date', 'create_date')
    def _compute_duration(self):
        for rec in self:
            if rec.closed_date and rec.create_date:
                delta = rec.closed_date - rec.create_date
                # تحويل الفرق إلى أيام وساعات
                days = delta.days
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                rec.duration_display = f"{days} يوم، {hours} ساعة، {minutes} دقيقة"
            else:
                rec.duration_display = "لم يتم الإغلاق بعد"

    def action_update_activities(self):
        for rec in self:
            # 1. جلب المجموعات بشكل منفصل لتجنب الخطأ
            group_officer = self.env.ref('base_rida.rida_group_safety_officer')
            group_senior = self.env.ref('base_rida.rida_group_senior_officer')

            # دمج مستخدمي المجموعتين في قائمة واحدة بدون تكرار
            safety_users = group_officer.user_ids | group_senior.user_ids

            requester_user = rec.requester_id
            to_notify = []

            # حالة: انتظار الاعتماد -> إشعار لمديري السلامة
            if rec.state == 'submitted':
                message = f"تصريح جديد رقم {rec.name} بانتظار موافقتك."
                for user in safety_users:
                    to_notify.append({'user': user, 'note': message})

            # حالة: تم التصريح / ملغى / ممدد -> إشعار للطالب
            elif rec.state in ['issued', 'revoked', 'extended']:
                # الحصول على الاسم العربي للحالة من القائمة
                status_ar = dict(self._fields['state'].selection).get(rec.state)
                message = f"تم تحديث حالة تصريحك رقم {rec.name} إلى: {status_ar}"
                if requester_user:
                    to_notify.append({'user': requester_user, 'note': message})

            # 2. تنفيذ إنشاء الأنشطة
            model_id = self.env.ref('qhse_form.model_cold_work_permit').id
            for item in to_notify:
                # التحقق من عدم وجود نفس النشاط مفتوح لنفس المستخدم
                existing_activity = self.env['mail.activity'].search([
                    ('res_id', '=', rec.id),
                    ('res_model_id', '=', model_id),
                    ('user_id', '=', item['user'].id),
                    ('summary', '=', item['note'])
                ], limit=1)

                if not existing_activity:
                    rec.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=item['user'].id,
                        note=item['note'],
                        summary=item['note']
                    )
        # 3. دالة خاصة بتنبيه الانتهاء (تُستدعى من الـ Cron Job)

    @api.model
    def _notify_expired_permits(self):
        now = fields.Datetime.now()
        # البحث عن التصاريح التي انتهى تاريخها ولم تُغلق بعد
        expired = self.search([
            ('state', 'in', ['issued', 'extended']),
            ('date_to', '<', now)
        ])

        # جلب المجموعات بشكل منفصل لتجنب خطأ الـ ValueError
        group_off = self.env.ref('base_rida.rida_group_safety_officer')
        group_sen = self.env.ref('base_rida.rida_group_senior_officer')

        # دمج مستخدمي المجموعتين (بدون تكرار)
        safety_users = group_off.user_ids | group_sen.user_ids

        model_id = self.env['ir.model']._get_id(self._name)

        for rec in expired:
            message = f"تنبيه: انتهت فترة صلاحية التصريح رقم {rec.name}"

            users_to_notify = list(safety_users)
            if rec.requester_id:
                users_to_notify.append(rec.requester_id)

            for user in users_to_notify:
                existing_activity = self.env['mail.activity'].search([
                    ('res_id', '=', rec.id),
                    ('res_model_id', '=', model_id),
                    ('user_id', '=', user.id),
                    ('summary', '=', "انقضاء وقت التصريح")
                ], limit=1)

                if not existing_activity:
                    rec.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=user.id,
                        note=message,
                        summary="انقضاء وقت التصريح"  # نستخدم summary ثابت للفحص
                    )


