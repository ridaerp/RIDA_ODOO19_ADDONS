from odoo import models, fields, api, _, exceptions
from odoo.exceptions import  UserError


class LotoWorkPermit(models.Model):
    _name = 'loto.work.permit'
    _description = 'Lockout-Tagout (LOTO) Work Permit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    name = fields.Char(string='Permit Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    department_id = fields.Many2one('hr.department', string='القسم / Department',
                                    default=lambda self: self.env.user.employee_id.department_id)
    department_ids = fields.Many2many('hr.department', string='الاقسام المعنية / Departments Involved')
    approved_dept_ids = fields.Many2many('hr.department', 'hot_work_dept_rel', string='الأقسام التي وافقت')
    state = fields.Selection([
        ('draft', 'مسودة / Draft'),
        ('dept_approval', 'انتظار اعتماد الأقسام / Dept Approval'),
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
    date_from = fields.Datetime(string='من / From')
    date_to = fields.Datetime(string='إلى / To')
    date = fields.Datetime(string='Date / التاريخ')

    # الجزء رقم #01: المعلومات العامة
    plant_site = fields.Char(string='Location / الموقع الدقيق')
    work_site = fields.Many2one('work.site',string='Plant/Site/Area / المصنع أو الموقع',ondelete='set null', tracking=True)
    purpose = fields.Char(string='Purpose / الغرض من العمل')
    task_description = fields.Text(string='Task Description / وصف المهمة')
    loto_justification = fields.Text(string='Justification for LOTO / مبرر استخدام النظام')
    requester_id = fields.Many2one('res.users', string='Requester / مقدم الطلب', default=lambda self: self.env.user)
    requester_signature = fields.Binary(string='Signature / التوقيع')

    # الجزء رقم #02C: التفتيش والتحضير
    # 1. تحضير المعدات (Equipment Preparation)
    prep_power_isolation = fields.Boolean(string='Power Isolation / عزل الطاقة')
    prep_loto_in_place = fields.Boolean(string='LOTO in place / القفل والتوسيم في مكانه')
    prep_keys_custody = fields.Boolean(string='Keys are custody of performer/competent person / المفاتيح في عهدة المنفذ')
    prep_suitable_tools = fields.Boolean(string='Suitable tools/equipment / الأدوات والمعدات المناسبة')
    prep_escape_route = fields.Boolean(string='Escape route / طرق الإخلاء')
    prep_warning = fields.Boolean(string='warning system  / نظام التحزير')

    # 2. التواصل والتدريب (Communication)
    prep_jsa_done = fields.Boolean(string='Job Planning/JSA done / تخطيط العمل/تحليل السلامة')
    prep_trained_personnel = fields.Boolean(string='All Personnel Trained / تدريب جميع الأفراد')
    prep_safety_meeting = fields.Boolean(string='Pre-Task Safety Meeting / اجتماع السلامة قبل المهمة')
    prep_method_reviewed = fields.Boolean(string='Work Method reviewed / مراجعة طريقة العمل')
    prep_comm_method = fields.Boolean(string='Communication Method / طريقة الاتصال')
    prep_emergency = fields.Boolean(string='emergency response plan / خطة الاستجابة للطوارئ')

    # 3. معدات الوقاية الشخصية (PPE Preparation)
    ppe_helmet = fields.Boolean(string='Helmet / خوذة')
    ppe_foot_protection = fields.Boolean(string='Foot protection / أحذية السلامة')
    ppe_hi_vis = fields.Boolean(string='Hi-Visible jacket / سترة عالية الوضوح')
    ppe_goggles = fields.Boolean(string='Safety Goggles / نظارات السلامة')
    ppe_dust_masks = fields.Boolean(string='Dust Masks / كمامات الغبار')
    prep_ear = fields.Boolean(string='Ear protection  / حماية الأذن')

    # الجزء رقم #02أ: المخاطر
    hazard_fluid = fields.Boolean(string='Fluid Flow / تدفق السوائل')
    hazard_drowning = fields.Boolean(string='Drowning / خطر الغرق')
    hazard_electrical = fields.Boolean(string='Electrical / خطر كهربائي')
    hazard_physical = fields.Boolean(string='Physical / مخاطر جسدية')
    hazard_mechanical = fields.Boolean(string='Mechanical / خطر ميكانيكي')
    hazard_traffic = fields.Boolean(string='Traffic / مخاطر مرورية')
    hazard_chemical = fields.Boolean(string='Chemical / خطر كيميائي')
    hazard_movement = fields.Boolean(string='Sudden Movement / حركة مفاجئة للمعدات / الآلات')
    hazard_fire = fields.Boolean(string='Fire/Explosion / خطر الحريق / الانفجار')
    hazard_other = fields.Char(string='Other')

    # الجزء رقم #02ب: الاحتياطات
    prec_jsa_attached = fields.Selection([('yes', 'Yes'), ('no', 'No'), ('na', 'N/A')], string='Job Safety Analysis (JSA) and/or Safe Work Procedure (SWP) has been reviewed and attached to this ‘work permit’ / تمت مراجعة وإرفاق تحليل السلامة الوظيفي و/أو إجراءات العمل الآمن بهذا التصريح.')
    prec_sources_identified = fields.Selection([('yes', 'Yes'), ('no', 'No'), ('na', 'N/A')],
                                               string='Clearly identify the location of all power sources control? / هل تم تحديد موقع جميع مصادر الطاقة والتحكم بها بوضوح؟')
    prec_locked_tagged = fields.Selection([('yes', 'Yes'), ('no', 'No'), ('na', 'N/A')], string='Have all possible source of power been identified, locked and properly tagged? / هل تم تحديد جميع مصادر الطاقة المحتملة، وعزلها، ووضع علامات القفل والتوسيم عليها بشكل صحيح؟')

    # تفاصيل القواطع
    cutter_switch = fields.Boolean(string='On/Off Switch / مفتاح التشغيل/الإيقاف')
    cutter_valve = fields.Boolean(string='Valves / الصمامات')
    cutter_lever = fields.Boolean(string='Levers / الروافع')
    cutter_gate = fields.Boolean(string='Gate / البوابات')
    cutter_other = fields.Char(string='Others / أخرى')
    other = fields.Char(string='Others')

    prec_indications = fields.Selection([('yes', 'Yes'), ('no', 'No'), ('na', 'N/A')], string='Are there any indication for power isolation/de-energize? / هل توجد مؤشرات على عزل الطاقة أو إزالة تنشيطها؟')
    prec_performer_loto = fields.Selection([('yes', 'Yes'), ('no', 'No'), ('na', 'N/A')],
                                           string='Are the LOTO kits installed and in place by performer? / هل تم تركيب معدات القفل والتوسيم في أماكنها من قبل المنفذ؟')
    prec_external_loto = fields.Selection([('yes', 'Yes'), ('no', 'No'), ('na', 'N/A')], string='Are the LOTO kits installed and in place by other competent person? such as 3rd party / هل تم تركيب معدات القفل والتوسيم في أماكنها من قبل شخص مؤهل آخر مثل جهة معتمدة خارجية؟')
    prec_ppe_available = fields.Selection([('yes', 'Yes'), ('no', 'No'), ('na', 'N/A')], string='Suitable PPE are provided and worn? / هل تم توفير معدات الوقاية الشخصية المطلوبة والتأكد من استخدامها؟')

    additional_controls = fields.Text(string='Additional Controls / إجراءات التحكم الإضافية المطلوبة')

    # الجزء رقم #03: نقاط العزل
    isolation_ids = fields.One2many('loto.isolation.line', 'permit_id', string='Isolation Details')

    # حقول الاعتماد
    relevant_party_1 = fields.Char(string='Relevant Party / الجهات ذات الصله')
    relevant_party_1_sig = fields.Binary(string='Sig 1')
    relevant_party_1_date = fields.Datetime(string='Date / التاريخ')
    relevant_party_2 = fields.Char(string='Relevant Party 2')
    relevant_party_2_sig = fields.Binary(string='Sig 2')
    relevant_party_2_date = fields.Datetime(string='Date 2')

    authorizer_id = fields.Many2one('hr.employee', string='Authorizer / المصرّح (مشرف أو مهندس)')
    authorizer_sig = fields.Binary(string='Auth Sig')
    authorizer_date = fields.Datetime(string='Auth Date / التاريخ')

    issuer_id = fields.Many2one('hr.employee', string='Issuer / المُمْنِح (مسئول السلامة بالموقع)')
    issuer_sig = fields.Binary(string='Issuer Sig')
    issuer_date = fields.Datetime(string='Issuer Date / التاريخ')

    # الجزء رقم #04: التمديد والإغلاق
    ext_valid_from = fields.Datetime(string='Ext. From')
    ext_valid_to = fields.Datetime(string='Ext. To')
    close_observation = fields.Text(string='Observations')
    close_men_withdrawn = fields.Boolean(string='Men withdrawn')
    close_loto_removed = fields.Boolean(string='LOTO Removed')


    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError("لا يمكنك حذف هذا التصريح. يمكن حذف السجلات في حالة (مسودة) فقط! / Only DRAFT records can be deleted.")
        return super(LotoWorkPermit, self).unlink()

    # تعديل دالة create لتجنب خطأ التكرار (Odoo 19 Standard)
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('loto.work.permit') or '/'
        return super(LotoWorkPermit, self).create(vals_list)


    is_need_ptw = fields.Boolean(string='Is Need PTW? / هل يحتاج الي تصريح عمل اخر', default=False)
    type_of_ptw = fields.Selection([
        ('hot_work', 'Hot Work Permit'),
        ('blasting', 'Blasting Space Permit'),
        ('cold_work', 'Cold Work Permit'),
        ('excavation', 'Excavation Work Permit'),
        ('confined', 'Confined Space Permit'),
        ('lifting', 'Lifting Work Permit'),
        ('highway', 'High Work Permit'),
    ], string='Type Of PTW / نوع تصريح العمل')
    linked_hot_ptw = fields.Many2one('hot.work.permit', string='Related PTW', readonly=True)
    linked_blasting_ptw = fields.Many2one('blasting.work.permit', string='Related PTW', readonly=True)
    linked_cold_ptw = fields.Many2one('cold.work.permit', string='Related PTW', readonly=True)
    linked_confined_ptw = fields.Many2one('confined.space.permit', string='Related PTW', readonly=True)
    linked_excavation_ptw = fields.Many2one('excavation.work.permit', string='Related PTW', readonly=True)
    linked_lifting_ptw = fields.Many2one('lifting.work.permit', string='Related PTW', readonly=True)
    linked_highway_ptw = fields.Many2one('work.height.permit', string='Related PTW', readonly=True)

    linked_ptw_count = fields.Integer(compute='_compute_linked_ptw_count')
    # الحقول الجديدة
    closed_date = fields.Datetime(string='تاريخ الإغلاق / Closing Date', readonly=True)
    duration_display = fields.Char(string='مدة التصريح / Duration', compute='_compute_duration')
    confirmation_check = fields.Boolean(
        string='أقر بأن جميع البيانات صحيحة وموافق على كافة إرشادات السلامة / I confirm that all information is correct and I agree to all safety instructions',
        required=True
    )

    def _compute_linked_ptw_count(self):
        for rec in self:
            # يجمع أي سجل مرتبك في الحقول التي عرفتها أنت
            counts = [rec.linked_hot_ptw, rec.linked_blasting_ptw, rec.linked_cold_ptw,
                      rec.linked_confined_ptw, rec.linked_excavation_ptw, rec.linked_lifting_ptw, rec.linked_highway_ptw]
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
            'lifting': {'model': 'lifting.work.permit', 'field': 'linked_lifting_ptw'},
            'highway': {'model': 'work.height.permit', 'field': 'linked_highway_ptw'},
        }

        # منع التكرار
        target = ptw_map.get(self.type_of_ptw)
        if target and getattr(self, target['field']):
            raise UserError("تم إنشاء هذا التصريح مسبقاً / This permit is already created")

        # إنشاء السجل في الموديول المستهدف
        new_record = self.env[target['model']].create({
            'work_site': self.work_site.id,
            'task_description': f"مرتبط بتصريح العمل العزل رقم: {self.name}",
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
            'lifting': 'linked_lifting_ptw', 'excavation': 'linked_excavation_ptw'
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
                                rec.linked_excavation_ptw, rec.linked_excavation_ptw, rec.linked_lifting_ptw,
                                rec.linked_highway_ptw]

                for ptw in related_ptws:
                    if ptw and ptw.state not in ['issued']:
                        raise UserError(f"لا يمكن الاعتماد! التصريح المرتبط ({ptw.name}) لا يزال في حالة {ptw.state}")
            
            if rec.department_ids:
                # إذا وجد أقسام، ننتقل لحالة اعتماد الأقسام
                rec.state = 'dept_approval'
                rec._notify_department_managers() # إرسال التنبيهات التي قمت ببرمجتها سابقاً
            else:
                # إذا لم توجد أقسام، يذهب مباشرة لمسؤول السلامة
                rec.state = 'submitted'
                rec.action_update_activities()

    def action_dept_approve(self):
        for rec in self:
            # التأكد أن المستخدم الحالي هو مدير لأحد الأقسام المعنية
            user_employee = self.env.user.employee_id
            managed_depts = self.env['hr.department'].search([('manager_id', '=', user_employee.id)])
            
            # تقاطع الأقسام التي يديرها المستخدم مع الأقسام المطلوبة في التصريح
            depts_to_approve = rec.department_ids.filtered(lambda d: d.id in managed_depts.ids)
            
            if not depts_to_approve:
                raise UserError("عذراً، أنت لست مديراً لأي من الأقسام المعنية بهذا التصريح.")

            # إضافة القسم للقائمة التي وافقت
            rec.approved_dept_ids |= depts_to_approve
            
            # التحقق: هل وافقت كل الأقسام المطلوبة؟
            if all(dept in rec.approved_dept_ids for dept in rec.department_ids):
                rec.state = 'submitted' # الانتقال لمسؤول السلامة
                rec.message_post(body="تم اعتماد جميع الأقسام المعنية. الطلب الآن بانتظار مسؤول السلامة.")
                rec.action_update_activities() # تنبيه مسؤولي السلامة
            else:
                rec.message_post(body=f"تم الاعتماد من قبل قسم {depts_to_approve.mapped('name')}. بانتظار بقية الأقسام.")

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

    def action_close(self):
        if not self.close_loto_removed:
            raise exceptions.UserError(_("يجب تأكيد إزالة القفل والعزل قبل إغلاق التصريح!"))
        self.write({
            'state': 'closed',
            'issuer_date': fields.Datetime.now()
        })
        self.action_update_activities()



class LotoIsolationLine(models.Model):
    _name = 'loto.isolation.line'
    _description = 'LOTO Isolation Points'

    # استخدام ondelete='cascade' هنا فقط لأنه حقل Many2one
    permit_id = fields.Many2one('loto.work.permit', ondelete='cascade')
    control_id = fields.Char(string='ID(switch/valve/lever/other) / رقم (القاطع/الصمام/الرافعة/أخرى)')
    control_location = fields.Char(string='location of control / موقع وحدة التحكم')
    isolation_method = fields.Char(string='Isolation Method / طريقة العزل')
    isolation_indication = fields.Char(string='indication of isolation / إشارة العزل')
    lock_type = fields.Char(string='Lock Type / نوع القفل')
    lock_no = fields.Char(string='Lock No / الرقم')
    tag_type = fields.Char(string='Tag Type / نوع التوسيم')
    tag_no = fields.Char(string='Tag No / الرقم')
    competent_person = fields.Char(string='Competent person / الشخص المؤهل')
    date_time = fields.Datetime(string='Date/Time / التاريخ والوقت')
    note_sig = fields.Text(string='Note / ملاحظة')