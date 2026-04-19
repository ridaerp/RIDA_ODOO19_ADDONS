from odoo import models, fields, api, _
from odoo.exceptions import  UserError


class LiftingWorkPermit(models.Model):
    _name = 'lifting.work.permit'
    _description = 'Lifting and Crane Work Permit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    def unlink(self):
        if self.state != 'draft':
            raise UserError("You cannot delete this Lifting Work Permit. Only DRAFT records can be deleted.")
        return super(LiftingWorkPermit, self).unlink()

    department_id = fields.Many2one('hr.department', string='القسم / Department',
                                    default=lambda self: self.env.user.employee_id.department_id)
    department_ids = fields.Many2many('hr.department', string='الاقسام المعنية / Departments Involved')

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

    # الجزء الأول: معلومات عامة والحمولة
    date = fields.Date(string='Date / التاريخ', default=fields.Date.context_today)
    date_from = fields.Datetime(string='Valid From / من')
    date_to = fields.Datetime(string='Valid To / إلى')
    # الجزء رقم #01: التفاصيل العامة
    plant_site = fields.Char(string='Plant/Site/Area / الموقع أو المصنع')
    sub_location_1 = fields.Char(string='Location #01 / الموقع 1')
    sub_location_2 = fields.Char(string='Location #02 / الموقع 2')
    weather_condition = fields.Char(string='Weather Condition / حالة الطقس')
    work_purpose = fields.Char(string='Purpose of Work / الغرض من العمل')
    task_description = fields.Text(string='Task Description / وصف المهمة')

    # تفاصيل الحمولة (Load Details)
    load_weight = fields.Float(string='Weight / الوزن')
    load_dimensions = fields.Char(string='Dimensions / الأبعاد')
    load_quantity = fields.Integer(string='Quantity / الكميات')
    load_price = fields.Float(string='Price $ / السعر')

    # معدات الرفع (Lifting Equipment)
    equip_excavator = fields.Boolean(string='Excavator / حفار')
    equip_crane = fields.Boolean(string='Crane / كرين')
    equip_forklift = fields.Boolean(string='Forklift / شوكة')
    equip_manlift = fields.Boolean(string='Man-lift / رافعة أفراد')
    equip_hiab = fields.Boolean(string='Hiab (High Crane) / كرين عالي/هياب')

    # تفاصيل معدات الرفع
    equip_sn = fields.Char(string='S/N / الرقم التسلسلي')
    equip_inspection = fields.Date(string='Inspection Date / تاريخ الفحص')
    equip_swl = fields.Char(string='Safe Working Load (SWL) / سعة الحمولة الآمنة')

    # بيانات إضافية
    other_tools = fields.Text(string='Other Tools / أدوات أخرى')
    workers_count = fields.Integer(string='Number of Workers / عدد العمال')
    # الجزء رقم #02أ: المخاطر المرتبطة بعمليات الرفع والمعدات
    hazard_tipping_over = fields.Boolean(string='Tipping Over/Rollover / انقلاب أو تدهور')
    hazard_suspended_load = fields.Boolean(string='Suspended Load / حمولة معلقة')
    hazard_strong_wind_rain = fields.Boolean(string='Strong Wind/Rain / رياح قوية أو أمطار')

    hazard_falling_objects_lift = fields.Boolean(string='Falling Objects / سقوط أجسام')
    hazard_overloading = fields.Boolean(string='Overloading / تحميل زائد')
    hazard_overhead_lines = fields.Boolean(string='Near Overhead Power Lines / بالقرب من خطوط الكهرباء العلوية')

    hazard_crushing = fields.Boolean(string='Crushing / سحق')
    hazard_collapse = fields.Boolean(string='Collapse / انهيار')
    hazard_structural_failure = fields.Boolean(string='Structural Failure / انهيار هيكلي')

    hazard_unfavorable_weather = fields.Boolean(string='Unfavorable Weather / ظروف جوية غير ملائمة')
    hazard_energized_equip = fields.Boolean(string='Near Energized Equipment / بالقرب من معدات موصلة بالكهرباء')
    hazard_traffic_noise = fields.Boolean(string='Traffic/Noise / حركة المرور أو الضوضاء')

    hazard_other_specify = fields.Char(string='Other Hazards (Specify) / مخاطر أخرى (تحديد)')
    # الجزء رقم #02ب: التدابير الوقائية لعمليات الرفع
    # سنستخدم نفس متغير PRECAUTION_STATES المعرف سابقاً (نعم/لا/لا ينطبق)
    PRECAUTION_STATES = [('yes', 'نعم / Yes'), ('no', 'لا / No'), ('na', 'لا ينطبق / N/A')]

    prec_lift_plan_attached = fields.Selection(PRECAUTION_STATES, string='Work Method/Lift Plan Attached')
    prec_lift_equip_inspected = fields.Selection(PRECAUTION_STATES, string='Lifting Equipment Inspected')

    # ملحقات الرفع
    prec_lift_accessories_ok = fields.Selection(PRECAUTION_STATES, string='Lifting Accessories OK')
    prec_accessories_types = fields.Char(string='Accessories Details', help='Wire ropes, Shackles, Hooks, etc.')

    prec_load_within_capacity = fields.Selection(PRECAUTION_STATES, string='Load Within Safe Capacity')
    prec_wind_speed_limit = fields.Selection(PRECAUTION_STATES, string='Wind Speed Within Limits')

    # بيانات المشغل (Operator Details)
    prec_operator_certified = fields.Selection(PRECAUTION_STATES, string='Operator Certified')
    operator_cert_type = fields.Char(string='Certificate Type / نوع الشهادة')
    operator_cert_no = fields.Char(string='Certificate No / رقم الشهادة')
    operator_cert_validity = fields.Date(string='Validity / مدة الصلاحية')

    prec_barriers_placed = fields.Selection(PRECAUTION_STATES, string='Physical Barriers Placed')
    prec_team_qualified = fields.Selection(PRECAUTION_STATES, string='Team Qualified/Trained')

    # تدابير إضافية
    prec_additional_controls = fields.Text(string='Additional Control Measures / تدابير التحكم الإضافية')
    # الجزء رقم #02ج: الفحص والتحضير (عمليات الرفع)

    # 1. إعداد المعدات (Equipment Setup)
    prep_ground_condition = fields.Boolean(string='Ground Condition / حالة الأرض')
    prep_outriggers_pads = fields.Boolean(string='Outriggers/Pads / الدعامات والوسائد')
    prep_weight_indicators = fields.Boolean(string='Weight Indicators / مؤشرات الوزن')
    prep_pulleys_lines = fields.Boolean(string='Pulleys & Lines / البكرات وخط الرفع')
    prep_safety_devices = fields.Boolean(string='Safety Devices / جهاز السلامة الخاص بالرفع')
    prep_signal_man = fields.Boolean(string='Signal Man / مسؤول الإشارات')

    # 2. الاتصالات (Communications)
    prep_lift_jsa = fields.Boolean(string='JSA Planning / تخطيط العمل')
    prep_lift_training = fields.Boolean(string='Personnel Training / تدريب الأفراد')
    prep_lift_toolbox = fields.Boolean(string='Pre-task Meeting / اجتماع السلامة')
    prep_lift_method_review = fields.Boolean(string='Method Review / مراجعة طريقة العمل')
    prep_lift_comm_method = fields.Boolean(string='Communication Method / طريقة الاتصال')
    prep_lift_emergency = fields.Boolean(string='Emergency Plan / خطة الطوارئ')

    # 3. معدات الوقاية الشخصية (PPE)
    prep_lift_helmet = fields.Boolean(string='Helmet w/ Chinstrap / خوذة بحزام ذقن')
    prep_lift_shoes = fields.Boolean(string='Non-slip Shoes / أحذية مقاومة للانزلاق')
    prep_lift_hi_vis = fields.Boolean(string='Hi-Vis Vest / سترة عالية الوضوح')
    prep_lift_goggles = fields.Boolean(string='Safety Goggles / نظارات السلامة')
    prep_lift_masks = fields.Boolean(string='Dust Masks / كمامات الغبار')
    prep_lift_ear_prot = fields.Boolean(string='Ear Protection / حماية الأذن')

    # تفاصيل معدات الرفع
    lifting_equipment_type = fields.Selection([
        ('crane', 'Crane / كرين'),
        ('forklift', 'Forklift / شوكة'),
        ('picker', 'Picker / رافعة'),
        ('head_crane', 'Overhead Crane / كرين عالي'),
        ('excavator', 'Excavator / حفار')
    ], string='Equipment Type')
    equipment_sn = fields.Char(string='Serial Number (S/N)')
    safe_working_load = fields.Float(string='Safe Working Load (SWL)')
    last_inspection_date = fields.Date(string='Inspection Date / تاريخ الفحص')

    # الجزء الثاني: المخاطر المرتبطة
    hazard_toppling = fields.Boolean(string='Toppling / انقلاب')
    hazard_overload = fields.Boolean(string='Overload / تحميل زائد')
    # الجزء رقم #03: التصريح والتفويض (عمليات الرفع)

    # 1. إقرار مشغل معدات الرفع
    operator_ack_text = fields.Text(string='Operator Statement',
                                    default='أُقرُّ بأنني قد قرأت وراجعت تصريح العمل هذا، وأنا على دراية بالمخاطر...')
    operator_sign_id = fields.Many2one('hr.employee', string='Lifting Operator / مشغل معدات الرفع')
    operator_signature = fields.Binary(string='Operator Signature / توقيع المشغل')
    operator_sign_time = fields.Datetime(string='Time / الوقت', default=fields.Datetime.now)

    # 2. الأطراف ذات الصلة (Concerned Parties) - 3 أطراف كما في النموذج
    related_party_1 = fields.Many2one('hr.employee', string='Concerned Party 1')
    related_party_1_sign = fields.Binary(string='Signature 1')
    related_party_1_time = fields.Datetime(string='Time 1')

    related_party_2 = fields.Many2one('hr.employee', string='Concerned Party 2')
    related_party_2_sign = fields.Binary(string='Signature 2')
    related_party_2_time = fields.Datetime(string='Time 2')

    related_party_3 = fields.Many2one('hr.employee', string='Concerned Party 3')
    related_party_3_sign = fields.Binary(string='Signature 3')
    related_party_3_time = fields.Datetime(string='Time 3')

    # 3. المُصرِّح (المهندس/المشرف)
    approver_ack_text = fields.Text(string='Approver Statement',
                                    default='أقرُّ بأنني قد راجعت قائمة التحقق وفحصت ظروف العمل...')
    approver_id = fields.Many2one('hr.employee', string='Authorizer (Eng/Sup) / المُصرِّح')
    approver_signature = fields.Binary(string='Authorizer Signature / توقيع المصرح')
    approver_sign_time = fields.Datetime(string='Time / الوقت')

    # 4. المُصدر (ضابط السلامة)
    safety_issuer_ack_text = fields.Text(string='Safety Statement',
                                         default='أُقرُّ بأنني قد راجعت هذا التصريح، وتم تنفيذ جميع تدابير التحكم...')
    safety_issuer_id = fields.Many2one('hr.employee', string='Safety Officer / ضابط السلامة')
    extension_line_ids = fields.One2many('lifting.permit.extension', 'permit_id', string='Extensions / التمديدات')
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
            val['name'] = self.env['ir.sequence'].next_by_code('lifting.work.permit') or ' '

        return super(LiftingWorkPermit, self).create(vals)

    is_need_ptw = fields.Boolean(string='Is Need PTW? / هل يحتاج الي تصريح عمل اخر', default=False)
    type_of_ptw = fields.Selection([
        ('hot_work', 'Hot Work Permit'),
        ('blasting', 'Blasting Space Permit'),
        ('cold_work', 'Cold Work Permit'),
        ('excavation', 'Excavation Work Permit'),
        ('confined', 'Confined Space Permit'),
        ('highway', 'High Work Permit'),
        ('loto', 'Loto Work Permit'),
    ], string='Type Of PTW / نوع تصريح العمل')
    linked_hot_ptw = fields.Many2one('hot.work.permit', string='Related PTW', readonly=True)
    linked_blasting_ptw = fields.Many2one('blasting.work.permit', string='Related PTW', readonly=True)
    linked_cold_ptw = fields.Many2one('cold.work.permit', string='Related PTW', readonly=True)
    linked_confined_ptw = fields.Many2one('confined.space.permit', string='Related PTW', readonly=True)
    linked_excavation_ptw = fields.Many2one('excavation.work.permit', string='Related PTW', readonly=True)
    linked_highway_ptw = fields.Many2one('work.height.permit', string='Related PTW', readonly=True)
    linked_loto_ptw = fields.Many2one('loto.work.permit', string='Related PTW', readonly=True)

    linked_ptw_count = fields.Integer(compute='_compute_linked_ptw_count')

    def _compute_linked_ptw_count(self):
        for rec in self:
            # يجمع أي سجل مرتبك في الحقول التي عرفتها أنت
            counts = [rec.linked_hot_ptw, rec.linked_blasting_ptw, rec.linked_cold_ptw,
                      rec.linked_confined_ptw, rec.linked_excavation_ptw, rec.linked_highway_ptw, rec.linked_loto_ptw]
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
            'excavation': {'model': 'excavation.work.permit', 'field': 'linked_excavation_ptw'},
            'highway': {'model': 'work.height.permit', 'field': 'linked_highway_ptw'},
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
            'excavation': 'linked_excavation_ptw', 'loto': 'linked_loto_ptw'
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
                                rec.linked_excavation_ptw, rec.linked_cold_ptw, rec.linked_highway_ptw,
                                rec.linked_loto_ptw]

                for ptw in related_ptws:
                    if ptw and ptw.state not in ['issued']:
                        raise UserError(f"لا يمكن الاعتماد! التصريح المرتبط ({ptw.name}) لا يزال في حالة {ptw.state}")

            # التعديل هنا: نغير الحالة أولاً ثم نستدعي الأنشطة
            rec.state = 'submitted'
            rec.action_update_activities()
            if rec.department_ids:
                rec._notify_department_managers()

    def _notify_department_managers(self):
        """دالة لإرسال الإشعارات لمدراء الأقسام المعنية"""
        for record in self:
            # جلب المستخدمين المرتبطين بمدراء الأقسام (تجنب التكرار)
            managers = record.department_ids.mapped('manager_id.user_id')
            
            # فلترة المدراء الذين لديهم مستخدم نشط في النظام
            active_managers = managers.filtered(lambda m: m.id)
            
            if active_managers:
                # 1. إرسال رسالة في الـ Chatter ومنشن (Mention) للمدراء
                body = _("لقد تم تحديد قسمكم كقسم معني في تصريح العمل رقم: <b>%s</b>. يرجى المراجعة.") % record.name
                record.message_post(
                    body=body,
                    partner_ids=active_managers.partner_id.ids,
                    subtype_xmlid='mail.mt_comment',
                    message_type='notification'
                )

                # 2. (اختياري) إنشاء نشاط (Activity) لكل مدير ليظهر في قائمة المهام لديهم
                for manager in active_managers:
                    record.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=manager.id,
                        summary=_('مراجعة تصريح عمل: أقسام معنية'),
                        note=_('تمت إضافتكم كقسم معني في التصريح %s') % record.name
                    )

    # تعديل دالة action_authorize لتسجيل الشخص الذي اعتمد الطلب
    def action_authorize(self):
        for rec in self:
            # البحث عن الموظف المرتبط بالمستخدم الحالي الذي ضغط على الزر
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

    class LiftingPermitExtension(models.Model):
        _name = 'lifting.permit.extension'
        _description = 'Permit Extension Record'

        permit_id = fields.Many2one('confined.space.permit', string='Permit Reference')
        date = fields.Date(string='Date / التاريخ', default=fields.Date.context_today)
        time_from = fields.Float(string='From / من')
        time_to = fields.Float(string='To / إلى')

        # المسؤولون عن الاعتماد
        executor_supervisor_id = fields.Many2one('hr.employee', string='Execution Supervisor / مشرف المنفذ')
        authorizer_id = fields.Many2one('hr.employee', string='Authorizer (Eng/Sup) / المصرّح')
        related_party_id = fields.Many2one('hr.employee', string='Concerned Party / الجهات ذات الصلة')
        safety_officer_id = fields.Many2one('hr.employee', string='Safety Officer / المُمْنِح')

        # التوقيعات (اختياري لتوثيق التمديد)
        signature = fields.Binary(string='Sign / توقيع')