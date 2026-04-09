from odoo import models, fields, api, _
from odoo.exceptions import  UserError


class WorkAtHeightPermit(models.Model):
    _name = 'work.height.permit'
    _description = 'Work at Height Permit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'


    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError("لا يمكنك حذف هذا التصريح. يمكن حذف السجلات في حالة (مسودة) فقط! / Only DRAFT records can be deleted.")
        return super(WorkAtHeightPermit, self).unlink()

    # تعديل دالة create لتجنب خطأ التكرار (Odoo 19 Standard)
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('work.height.permit') or '/'
        return super(WorkAtHeightPermit, self).create(vals_list)

    name = fields.Char(string='Permit Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    department_id = fields.Many2one('hr.department', string='القسم / Department',
                                    default=lambda self: self.env.user.employee_id.department_id)
    department_ids = fields.Many2many('hr.department', string='الاقسام المعنية / Departments Involved')
    approved_dept_ids = fields.Many2many('hr.department', 'height_work_dept_rel', string='الأقسام التي وافقت')
    approval_log = fields.Html(string='سجل اعتمادات الأقسام / Dept Approvals Log', readonly=True)
    sub_location = fields.Char(string='الموقع الفرعي / Sub Location', tracking=True)
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

    # الجزء الأول: المعلومات العامة
    date = fields.Date(string='Date / التاريخ', default=fields.Date.context_today)
    date_from = fields.Datetime(string='Valid From / من')
    date_to = fields.Datetime(string='Valid To / إلى')
    work_site = fields.Many2one('work.site',string='Location / الموقع',ondelete='set null', tracking=True)
    closure_date = fields.Date(string='Clouser Date', tracking=True)

    # نوع العمل على الارتفاع
    work_at_height_type = fields.Selection([
        ('scaffold', 'Scaffold / سقالة'),
        ('roof', 'Roof Work / عمل على السطح'),
        ('basket', 'Basket / سلة معلقة'),
        ('other', 'Other / أخرى')
    ], string='Type of Work at Height')

    task_description = fields.Text(string='Task Description / وصف المهمة')
    equipment_used = fields.Char(string='Equipment/Tools / المعدات والأدوات')
    number_of_workers = fields.Integer(string='Number of Workers / عدد العمال')
    requester_id = fields.Many2one('res.users', string='Requester / مقدم الطلب', default=lambda self: self.env.user)

    # الجزء الثاني: تحديد المخاطر (Boolean Fields)
    PRECAUTION_STATES = [('yes', 'نعم / Yes'), ('no', 'لا / No'), ('na', 'لا ينطبق / N/A')]
    hazard_fall_height = fields.Selection(PRECAUTION_STATES,string='Fall from height / السقوط من ارتفاع')
    hazard_flying_particles = fields.Selection(PRECAUTION_STATES,string='Flying particles / جسيمات متطايرة')
    hazard_moving_vehicles = fields.Selection(PRECAUTION_STATES,string='Moving vehicles/equipment / مركبات أو معدات متحركة')

    hazard_falling_objects_height = fields.Selection(PRECAUTION_STATES,string='Falling objects/equipment / سقوط الأجسام أو المعدات')
    hazard_trip_slip = fields.Selection(PRECAUTION_STATES,string='Trip/Slip / التعثر أو الانزلاق')
    hazard_damaged_equipment = fields.Selection(PRECAUTION_STATES,string='Damaged equipment/materials / معدات أو مواد تالفة')

    hazard_fragile_surfaces = fields.Selection(PRECAUTION_STATES,string='Fragile surfaces/roofs / الأسطح أو الأسقف الهشة')
    hazard_overhead_power = fields.Selection(PRECAUTION_STATES,string='Near overhead power lines / بالقرب من خطوط كهربائية علوية')
    hazard_mobile_scaffold = fields.Selection(PRECAUTION_STATES,string='Mobile scaffold / سقالة متحركة')

    hazard_working_below = fields.Selection(PRECAUTION_STATES,string='Working below elevated site / العمل أسفل موقع مرتفع')
    hazard_energized_equipment = fields.Selection(PRECAUTION_STATES,string='Near energized equipment / بالقرب من معدات موصولة بالطاقة')
    hazard_weather_conditions = fields.Selection(PRECAUTION_STATES,string='Unfavorable weather / ظروف جوية غير ملائمة')

    hazard_height_other = fields.Char(string='Other Hazards / مخاطر أخرى (تحديد)')

    # الجزء رقم #02ب: الاحتياطات المطلوبة للعمل في المرتفعات


    prec_height_ms_jsa = fields.Selection(PRECAUTION_STATES, string='Method Statement/JSA attached')
    prec_height_fall_measures = fields.Selection(PRECAUTION_STATES, string='Fall control measures applied')
    prec_height_inspection = fields.Selection(PRECAUTION_STATES, string='Measures inspected & good condition')
    prec_height_access_egress = fields.Selection(PRECAUTION_STATES, string='Safe access/egress provided')

    # حقل سرعة الرياح مع منطق تحذيري
    prec_height_wind_speed = fields.Selection(PRECAUTION_STATES, string='Wind speed exceeds 32 km/h')

    prec_height_floor_openings = fields.Selection(PRECAUTION_STATES, string='Floor openings covered/protected')
    prec_height_scaffold_inspected = fields.Selection(PRECAUTION_STATES, string='Scaffold installed & inspected')
    prec_height_loto_required = fields.Selection(PRECAUTION_STATES, string='LOTO required & applied')
    prec_height_barriers = fields.Selection(PRECAUTION_STATES, string='Physical barriers required')
    prec_height_team_qualified = fields.Selection(PRECAUTION_STATES, string='Team qualified/authorized')
    prec_height_scope_communicated = fields.Selection(PRECAUTION_STATES, string='Scope communicated to team')
    prec_height_additional_ctrl = fields.Text(string='Additional Controls / إجراءات التحكم الإضافية')
    # الجزء رقم #02ج: الفحص والتحضير
    # 1. تحضير المعدات (Equipment Preparation)
    prep_warning_signs = fields.Selection(PRECAUTION_STATES,string='Warning/Danger Signs / علامات التحذير')
    prep_lighting = fields.Selection(PRECAUTION_STATES,string='Lighting / الإضاءة')
    prep_safety_barriers = fields.Selection(PRECAUTION_STATES,string='Safety Barriers / حواجز السلامة')
    prep_fall_protection_net = fields.Selection(PRECAUTION_STATES,string='Fall Protection (Net) / الحماية من السقوط')
    prep_fall_arrester = fields.Selection(PRECAUTION_STATES,string='Fall Arrester / مانع السقوط')
    prep_safety_harness_hooks = fields.Selection(PRECAUTION_STATES,string='Harness with Hooks / حزام الأمان مع خطافات')

    # 2. الاتصال (Communication)
    prep_jsa_planning = fields.Selection(PRECAUTION_STATES,string='JSA Planning / تخطيط العمل')
    prep_personnel_training = fields.Selection(PRECAUTION_STATES,string='Personnel Training / تدريب الأفراد')
    prep_pre_task_meeting = fields.Selection(PRECAUTION_STATES,string='Pre-task Meeting / اجتماع السلامة')
    prep_method_review = fields.Selection(PRECAUTION_STATES,string='Method Review / مراجعة طريقة العمل')
    prep_comm_method = fields.Selection(PRECAUTION_STATES,string='Communication Method / طريقة الاتصال')
    prep_emergency_plan = fields.Selection(PRECAUTION_STATES,string='Emergency Response Plan / خطة الطوارئ')

    # 3. معدات الوقاية الشخصية (PPE Preparation)
    prep_helmet_chinstrap = fields.Selection(PRECAUTION_STATES,string='Helmet with Chinstrap / خوذة مع حزام ذقن')
    prep_non_slip_shoes = fields.Selection(PRECAUTION_STATES,string='Non-slip Shoes / أحذية مقاومة للانزلاق')
    prep_hi_vis_vest = fields.Selection(PRECAUTION_STATES,string='Hi-Vis Vest / سترة عالية الوضوح')
    prep_safety_goggles = fields.Selection(PRECAUTION_STATES,string='Safety Goggles / نظارات السلامة')
    prep_dust_masks = fields.Selection(PRECAUTION_STATES,string='Dust Masks / كمامات الغبار')
    prep_ear_protection = fields.Selection(PRECAUTION_STATES,string='Ear Protection / حماية الأذن')

    # الجزء رقم #03: تصريح واعتماد الدخول

    # 1. المشغل / العامل / المشرف
    worker_statement = fields.Text(string='Worker Statement', default='أُقرُّ بأنني قد قرأت وراجعت تصريح العمل هذا...')
    worker_id = fields.Many2one('hr.employee', string='Operator/Supervisor / المشغل أو المشرف')
    worker_signature = fields.Binary(string='Worker Signature / توقيع العامل')
    worker_date = fields.Datetime(string='Worker Date / التاريخ', default=fields.Datetime.now)

    # 2. الأطراف المعنية (Concerned Parties)
    concerned_party_1_id = fields.Many2one('hr.employee', string='Concerned Party 1 / طرف معني 1')
    concerned_party_1_signature = fields.Binary(string='Signature 1')
    concerned_party_1_date = fields.Datetime(string='Date 1')

    concerned_party_2_id = fields.Many2one('hr.employee', string='Concerned Party 2 / طرف معني 2')
    concerned_party_2_signature = fields.Binary(string='Signature 2')
    concerned_party_2_date = fields.Datetime(string='Date 2')

    # 3. المصرح (المهندس أو المشرف)
    authorizer_statement = fields.Text(string='Authorizer Statement',
                                       default='أُقرُّ بأنني قد راجعت قائمة الفحص وفحصت ظروف العمل...')
    authorizer_id = fields.Many2one('hr.employee', string='Authorizer (Eng/Sup) / المُصرِّح')
    authorizer_signature = fields.Binary(string='Authorizer Signature / توقيع المصرح')
    authorizer_date = fields.Datetime(string='Authorizer Date / التاريخ')

    # 4. المصدر (ضابط السلامة)
    issuer_statement = fields.Text(string='Issuer Statement',
                                   default='أُقرُّ بأنني قد راجعت هذا التصريح، وتم تنفيذ جميع تدابير التحكم...')
    issuer_id = fields.Many2one('hr.employee', string='Issuer (Safety Officer) / المُصدر')
    issuer_signature = fields.Binary(string='Issuer Signature / توقيع المصدر')
    issuer_date = fields.Datetime(string='Issuer Date / التاريخ')
    extension_date_from = fields.Datetime(string='بداية التمديد / Extension From')
    extension_date_to = fields.Datetime(string='نهاية التمديد / Extension To')
    supervisor_id = fields.Many2one('hr.employee', string='المشرف المباشر / Direct Supervisor')

    is_need_ptw = fields.Boolean(string='Is Need PTW? / هل يحتاج الي تصريح عمل اخر', default=False)
    type_of_ptw = fields.Selection([
        ('hot_work', 'Hot Work Permit'),
        ('blasting', 'Blasting Space Permit'),
        ('cold_work', 'Cold Work Permit'),
        ('excavation', 'Excavation Work Permit'),
        ('confined', 'Confined Space Permit'),
        ('lifting', 'Lifting Work Permit'),
        ('loto', 'Loto Work Permit'),
    ], string='Type Of PTW / نوع تصريح العمل')
    linked_hot_ptw = fields.Many2one('hot.work.permit', string='Related PTW', readonly=True)
    linked_blasting_ptw = fields.Many2one('blasting.work.permit', string='Related PTW', readonly=True)
    linked_cold_ptw = fields.Many2one('cold.work.permit', string='Related PTW', readonly=True)
    linked_confined_ptw = fields.Many2one('confined.space.permit', string='Related PTW', readonly=True)
    linked_excavation_ptw = fields.Many2one('excavation.work.permit', string='Related PTW', readonly=True)
    linked_lifting_ptw = fields.Many2one('lifting.work.permit', string='Related PTW', readonly=True)
    linked_loto_ptw = fields.Many2one('loto.work.permit', string='Related PTW', readonly=True)

    linked_ptw_count = fields.Integer(compute='_compute_linked_ptw_count')

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
                      rec.linked_confined_ptw, rec.linked_excavation_ptw, rec.linked_lifting_ptw, rec.linked_loto_ptw]
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
            'loto': {'model': 'loto.work.permit', 'field': 'linked_loto_ptw'},
        }

        # منع التكرار
        target = ptw_map.get(self.type_of_ptw)
        if target and getattr(self, target['field']):
            raise UserError("تم إنشاء هذا التصريح مسبقاً / This permit is already created")

        # إنشاء السجل في الموديول المستهدف
        new_record = self.env[target['model']].create({
            'work_site': self.work_site.id,
            'task_description': f"مرتبط بتصريح العمل علي الارتفاعات رقم: {self.name}",
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
            'cold_work': 'linked_cold_ptw', 'excavation': 'linked_excavation_ptw',
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
                                rec.linked_excavation_ptw, rec.linked_cold_ptw, rec.linked_lifting_ptw,
                                rec.linked_loto_ptw]

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

    # def action_dept_approve(self):
    #     for rec in self:
    #         # التأكد أن المستخدم الحالي هو مدير لأحد الأقسام المعنية
    #         user_employee = self.env.user.employee_id
    #         managed_depts = self.env['hr.department'].search([('manager_id', '=', user_employee.id)])
            
    #         # تقاطع الأقسام التي يديرها المستخدم مع الأقسام المطلوبة في التصريح
    #         depts_to_approve = rec.department_ids.filtered(lambda d: d.id in managed_depts.ids)
            
    #         if not depts_to_approve:
    #             raise UserError("عذراً، أنت لست مديراً لأي من الأقسام المعنية بهذا التصريح.")

    #         # إضافة القسم للقائمة التي وافقت
    #         rec.approved_dept_ids |= depts_to_approve
            
    #         # التحقق: هل وافقت كل الأقسام المطلوبة؟
    #         if all(dept in rec.approved_dept_ids for dept in rec.department_ids):
    #             rec.state = 'submitted' # الانتقال لمسؤول السلامة
    #             rec.message_post(body="تم اعتماد جميع الأقسام المعنية. الطلب الآن بانتظار مسؤول السلامة.")
    #             rec.action_update_activities() # تنبيه مسؤولي السلامة
    #         else:
    #             rec.message_post(body=f"تم الاعتماد من قبل قسم {depts_to_approve.mapped('name')}. بانتظار بقية الأقسام.")
    def action_dept_approve(self):
        for rec in self:
            # التأكد أن المستخدم الحالي هو مدير لأحد الأقسام المعنية
            user_employee = self.env.user.employee_id
            managed_depts = self.env['hr.department'].search([('manager_id', '=', user_employee.id)])
            
            # تحسين: نفلتر الأقسام التي يديرها المستخدم "ولم توافق بعد" لتجنب التكرار
            depts_to_approve = rec.department_ids.filtered(
                lambda d: d.id in managed_depts.ids and d.id not in rec.approved_dept_ids.ids
            )
            
            if not depts_to_approve:
                # رسالة تنبيه إذا كان قد وافق مسبقاً أو ليس مديراً
                raise UserError("عذراً، لا توجد أقسام معنية تحتاج لاعتمادك حالياً أو تم الاعتماد مسبقاً.")

            # تجهيز الأسطر الجديدة
            new_lines = ""
            current_time = fields.Datetime.now().strftime('%Y-%m-%d %H:%M')
            for dept in depts_to_approve:
                new_lines += f"<li><b>{dept.name}:</b> تم الاعتماد بواسطة {self.env.user.name} بتاريخ {current_time}</li>"

            # تحديث السجل النصي (HTML)
            existing_log = rec.approval_log or ""
            rec.approval_log = f"{existing_log}<ul style='list-style-type: circle; margin: 0;'>{new_lines}</ul>"

            # إضافة القسم لقائمة الموافقين (Many2many)
            rec.approved_dept_ids |= depts_to_approve
            
            # التحقق من اكتمال كافة الموافقات
            if all(dept in rec.approved_dept_ids for dept in rec.department_ids):
                rec.state = 'submitted'
                rec.message_post(body="تم اعتماد جميع الأقسام المعنية. الطلب الآن بانتظار مسؤول السلامة.")
                rec.action_update_activities()
            else:
                rec.message_post(body=f"تم الاعتماد من قبل قسم {depts_to_approve.mapped('name')}. بانتظار بقية الأقسام.")

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


