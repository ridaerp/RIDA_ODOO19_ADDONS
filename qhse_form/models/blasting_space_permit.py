from odoo import models, fields, api, _
from odoo.exceptions import  UserError

class BlastingWorkPermit(models.Model):
    _name = 'blasting.work.permit'
    _description = 'Mine Site Blasting Permit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    def unlink(self):
        if self.state != 'draft':
            raise UserError("You cannot delete this Blasting Work Permit. Only DRAFT records can be deleted.")
        return super(BlastingWorkPermit, self).unlink()

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
    confirmation_check = fields.Boolean(
        string='أقر بأن جميع البيانات صحيحة وموافق على كافة إرشادات السلامة / I confirm that all information is correct and I agree to all safety instructions',
        required=True
    )
    department_id = fields.Many2one('hr.department', string='القسم / Department',
                                    default=lambda self: self.env.user.employee_id.department_id)
    closed_date = fields.Datetime(string='تاريخ الإغلاق / Closing Date', readonly=True)
    duration_display = fields.Char(string='مدة التصريح / Duration', compute='_compute_duration')
    # الجزء رقم #1/أ: تفاصيل موقع التفجير
    date_from = fields.Datetime(string='Date / التاريخ', default=fields.Date.context_today)
    date_to = fields.Date(string='Date / التاريخ')
    planned_time = fields.Char(string='Planned Blasting Time / زمن التفجير المخطط')
    mine_name = fields.Char(string='Mine Name / اسم المنجم')
    mine_code = fields.Char(string='Code / الرمز')
    blasting_purpose = fields.Text(string='Purpose of Blasting / سبب التفجير')
    requester_id = fields.Many2one('res.users', string='Requester / مقدم الطلب', default=lambda self: self.env.user)
    task_description = fields.Text(string='وصف المهمة / Task Description')
    # الجزء رقم #1/ب: المعلومات الفنية (Technical Information)
    explosive_type = fields.Char(string='Type of Explosive Materials / نوع المتفجرات')
    used_volume = fields.Float(string='Total Expected Volume / الكمية المتوقعة')
    targeted_holes = fields.Integer(string='Targeted Holes / عدد الحفر المستهدفة')
    drilling_depth = fields.Float(string='Total Drilling Depth / أعماق الحفر الكلية')
    detonator_type = fields.Char(string='Detonators Type / نوع كبسولات الإشعال')
    main_charge = fields.Char(string='Main Charge / نوع الشحنة الأساسية')
    stemming_type = fields.Char(string='Stemming Type / نوع عازل الدفن')
    value_1 = fields.Char(string='قيمة الشحنة النوعية مقابل الكمية / Specific charge Kg/m3')
    value_2 = fields.Char(string='قيمة الشحنة النوعية مقابل الزمن التاخيري / Max. Kg/m3')

    # الجزء رقم #1/ج: معلومات الجهاز والمفجر
    detonating_device = fields.Char(string='Detonating Device / جهاز التفجير')
    device_sn = fields.Char(string='Serial Number / الرقم التسلسلي')
    calibration_date = fields.Date(string='Calibration Date / تاريخ المعايرة')
    responsible_blaster = fields.Char(string='Responsible Blaster / المفجر المسؤول')
    blaster_certificate = fields.Char(string='Certificate No. / رقم الشهادة')
    certificate = fields.Char(string='Certificate / الشهادة')

    # الجزء رقم #02: متطلبات التفجير / إجراءات التحكم
    # تحضير المعدات
    PRECAUTION_STATES = [('yes', 'نعم / Yes'), ('no', 'لا / No'), ('na', 'لا ينطبق / N/A')]
    equipment_transport = fields.Selection(PRECAUTION_STATES,string='Suitable transportation mean for explosive / وسيلة نقل مناسبة')
    equip_explosive_proof = fields.Selection(PRECAUTION_STATES,string='All equipment are explosive proof / معدات مقاومة للانفجار')
    charge_lines_ok = fields.Selection(PRECAUTION_STATES,string='Charge lines in good condition / خطوط الشحن جيدة')
    red_flags = fields.Selection(PRECAUTION_STATES,string='Red flags and Hazard taps / أعلام حمراء وشريط تحذيري')

    # الاتصال
    blasting_notification = fields.Selection(PRECAUTION_STATES,string='Blasting Notification shared / مشاركة إشعار التفجير')
    jsa_done = fields.Selection(PRECAUTION_STATES,string='Job Planning/JSA done / تحليل السلامة الوظيفي')
    safety_meeting = fields.Selection(PRECAUTION_STATES,string='Pre-Task Safety Meeting / اجتماع السلامة قبل المهمة')
    work_method_reviewed = fields.Selection(PRECAUTION_STATES,string='Work Method reviewed / مراجعة طريقة العمل')
    msds_available = fields.Selection(PRECAUTION_STATES,string='MSDS Reviewed & available / توفر صحيفة بيانات السلامة')

    # الاستعداد للطوارئ
    emergency_plans_reviewed = fields.Selection(PRECAUTION_STATES,string='Emergency Plans Reviewed / مراجعة خطط الطوارئ')
    ert_ready = fields.Selection(PRECAUTION_STATES,string='ERT Notified and ready / جاهزية فريق الاستجابة')
    access_secured = fields.Selection(PRECAUTION_STATES,string='Main gates/Roads secured / تأمين المداخل والطرق')
    alarm_tested = fields.Selection(PRECAUTION_STATES,string='Alarm system tested / اختبار نظام الإنذار')

    # الجزء رقم #03: المصادقة (Authorization)
    authorizer_id = fields.Many2one('hr.employee', string='Authorizer (Engineer/Supervisor) / المفوض')
    authorizer_sig = fields.Binary(string='Authorizer Signature / توقيع المفوض')
    authorizer_date = fields.Datetime(string='Authorization Date / تاريخ المصادقة')

    issuer_id = fields.Many2one('hr.employee', string='Issuer (Safety Officer) / الجهة المصدرة')
    issuer_sig = fields.Binary(string='Issuer Signature / توقيع الجهة المصدرة')
    issuer_date = fields.Datetime(string='Issue Date / تاريخ الإصدار')
    # معدات الوقاية الشخصية (PPE)
    ppe_hand = fields.Selection(PRECAUTION_STATES,string='Hand Protection / حماية اليدين')
    ppe_eye = fields.Selection(PRECAUTION_STATES,string='Eye Protection / حماية العينين')
    ppe_hearing = fields.Selection(PRECAUTION_STATES,string='Hearing Protection / حماية السمع')
    ppe_respirator = fields.Char(string='Respirator Type / نوع جهاز التنفس')
    ppe_head = fields.Selection(PRECAUTION_STATES,string='Head Protection / حماية الرأس')
    ppe_body = fields.Selection(PRECAUTION_STATES,string='Body Protection / حماية الجسم')
    ppe_other = fields.Char(string='Other PPE / أخرى')

    # المخاطر الجسيمة (Serious Hazards)
    hazard_fire_explosion = fields.Selection(PRECAUTION_STATES,string='Fire and Explosion / الحريق والانفجار')
    hazard_traffic = fields.Selection(PRECAUTION_STATES,string='Traffic Accident / حادث مروري')
    hazard_fall_height = fields.Selection(PRECAUTION_STATES,string='Fall from Height / السقوط من ارتفاع')
    hazard_trip_fall = fields.Selection(PRECAUTION_STATES,string='Fall/Trip / التعثر أو السقوط')
    hazard_chemical = fields.Selection(PRECAUTION_STATES,string='Chemical / المواد الكيميائية')
    hazard_heat_cold = fields.Selection(PRECAUTION_STATES,string='Heat/Cold / الحرارة أو البرودة')
    hazard_noise = fields.Selection(PRECAUTION_STATES,string='Excessive Noise (>85 dba) / ضوضاء مفرطة')
    hazard_manual_handling = fields.Selection(PRECAUTION_STATES,string='Manual Handling / المناولة اليدوية')

    # إجراءات تحكم إضافية (Additional Controls)
    ctrl_slip_trip = fields.Selection(PRECAUTION_STATES,string='Slip and trip hazards eliminated / القضاء على مخاطر الانزلاق والتعثر')
    ctrl_unauthorized_access = fields.Selection(PRECAUTION_STATES,string='Unauthorized access controlled / التحكم في الدخول غير المصرح به')
    ctrl_barriers = fields.Selection(PRECAUTION_STATES,string='Physical barriers installed / تركيب الحواجز المادية')
    ctrl_traffic_mgmt = fields.Selection(PRECAUTION_STATES,string='Traffic movement controlled / إدارة حركة المرور')
    ctrl_evacuation_dist = fields.Selection(PRECAUTION_STATES,string='Min. evacuation distance 750m/300m / الحد الأدنى لمسافة الإخلاء')
    ctrl_pre_firing_tour = fields.Selection(PRECAUTION_STATES,string='Pre-firing tour conducted / جولة تفقدية قبل التفجير')
    ctrl_alarm_siren = fields.Selection(PRECAUTION_STATES,string='Alarm before 2 min / تفعيل الإنذار قبل دقيقتين')
    instruction_reviewed = fields.Boolean(
        string='I have read and understood the general instructions / قرأت وفهمت التعليمات العامة', default=False)

    is_need_ptw = fields.Boolean(string='Is Need PTW? / هل يحتاج الي تصريح عمل اخر', default=False)
    type_of_ptw = fields.Selection([
        ('hot_work', 'Hot Work Permit'),
        ('cold_work', 'Cold Work Permit'),
        ('confined', 'Confined Space Permit'),
        ('excavation', 'Excavation Work Permit'),
        ('highway', 'High Work Permit'),
        ('lifting', 'Lifting Work Permit'),
        ('loto', 'Loto Work Permit'),
    ], string='Type Of PTW / نوع تصريح العمل')
    linked_hot_ptw = fields.Many2one('hot.work.permit', string='Related PTW', readonly=True)
    linked_cold_ptw = fields.Many2one('cold.work.permit', string='Related PTW', readonly=True)
    linked_confined_ptw = fields.Many2one('confined.space.permit', string='Related PTW', readonly=True)
    linked_excavation_ptw = fields.Many2one('excavation.work.permit', string='Related PTW', readonly=True)
    linked_highway_ptw = fields.Many2one('work.height.permit', string='Related PTW', readonly=True)
    linked_lifting_ptw = fields.Many2one('lifting.work.permit', string='Related PTW', readonly=True)
    linked_loto_ptw = fields.Many2one('loto.work.permit', string='Related PTW', readonly=True)

    linked_ptw_count = fields.Integer(compute='_compute_linked_ptw_count')

    def _compute_linked_ptw_count(self):
        for rec in self:
            # يجمع أي سجل مرتبك في الحقول التي عرفتها أنت
            counts = [rec.linked_hot_ptw, rec.linked_cold_ptw, rec.linked_confined_ptw,
                      rec.linked_excavation_ptw, rec.linked_highway_ptw, rec.linked_lifting_ptw, rec.linked_loto_ptw]
            rec.linked_ptw_count = len([c for c in counts if c])

    def action_create_related_ptw(self):
        self.ensure_one()
        if not self.type_of_ptw:
            raise UserError("الرجاء اختيار نوع التصريح أولاً / Please select PTW type first")

        # خريطة الربط بين الاختيار واسم الموديل واسم الحقل في موديولك
        ptw_map = {
            'hot_work': {'model': 'hot.work.permit', 'field': 'linked_hot_ptw'},
            'blasting': {'model': 'blasting.work.permit', 'field': 'linked_cold_ptw'},
            'confined': {'model': 'confined.space.permit', 'field': 'linked_confined_ptw'},
            'excavation': {'model': 'excavation.work.permit', 'field': 'linked_excavation_ptw'},
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
            'work': 'linked_hot_ptw', 'blasting': 'linked_cold_ptw', 'confined': 'linked_confined_ptw',
            'excavation': 'linked_excavation_ptw', 'highway': 'linked_highway_ptw',
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


    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('blasting.work.permit') or ' '

        return super(BlastingWorkPermit, self).create(vals)

    def action_submit(self):
        for rec in self:
            if not rec.confirmation_check:
                raise UserError(
                    "يجب عليك الموافقة على صحة البيانات وإرشادات السلامة قبل إرسال الطلب! / You must confirm that all information is correct before submitting.")
            if rec.is_need_ptw:
                related_ptws = [rec.linked_cold_ptw, rec.linked_hot_ptw, rec.linked_confined_ptw,
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
            model_id = self.env.ref('qhse_form.model_blasting_work_permit').id
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

