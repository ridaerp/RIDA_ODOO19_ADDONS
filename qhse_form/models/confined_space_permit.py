# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import  UserError


class ConfinedSpacePermit(models.Model):
    _name = 'confined.space.permit'
    _description = 'تصريح دخول أماكن محصورة / Confined Space Entry Permit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    name = fields.Char(string='رقم التصريح / Permit Number', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError("لا يمكنك حذف هذا التصريح. يمكن حذف السجلات في حالة (مسودة) فقط! / Only DRAFT records can be deleted.")
        return super(ConfinedSpacePermit, self).unlink()

    # تعديل دالة create لتجنب خطأ التكرار (Odoo 19 Standard)
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('confined.space.permit') or '/'
        return super(ConfinedSpacePermit, self).create(vals_list)

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

    # الجزء الأول: تفاصيل الموقع والمهمة
    date_from = fields.Datetime(string='التاريخ / Date', default=fields.Date.context_today)
    date_to = fields.Date(string='التاريخ / Date')
    # company_id = fields.Many2one('res.company', string='الشركة', default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', string='القسم / Department',default=lambda self: self.env.user.employee_id.department_id)
    department_ids = fields.Many2many('hr.department', string='الاقسام المعنية / Departments Involved')
    approved_dept_ids = fields.Many2many('hr.department', 'confined_work_dept_rel', string='الأقسام التي وافقت')
    approval_log = fields.Html(string='سجل اعتمادات الأقسام / Dept Approvals Log', readonly=True)
    space_description = fields.Text(string='وصف المكان / Space Description')
    entry_purpose = fields.Text(string='الغرض من الدخول / Entry Purpose')
    task_description = fields.Text(string='وصف المهمة / Task Description')
    tools_used = fields.Text(string='الأدوات والمعدات / Tools and equipment')
    requester_id = fields.Many2one('res.users', string='Requester / مقدم الطلب', default=lambda self: self.env.user)

    # الجزء الثاني: اختبار الغازات (Gas Testing)
    gas_detector_sn = fields.Char(string='رقم حساس الغاز / Detector S/N')
    calibration_date = fields.Date(string='تاريخ المعايرة / Calibration Date')
    oxygen_level = fields.Float(string='الأكسجين / Oxygen (19.5-23.5%)')
    lel_level = fields.Float(string='غازات قابلة للاشتعال / LEL (< 10%)')
    h2s_level = fields.Float(string='كبريتيد الهيدروجين / H2S (< 10 ppm)')
    co_level = fields.Float(string='أول أكسيد الكربون / CO (< 25 ppm)')

    # الجزء الثالث: ضوابط السلامة (Checklist)
    # تحضير المعدات والاتصال
    PRECAUTION_STATES = [('yes', 'نعم / Yes'), ('no', 'لا / No'), ('na', 'لا ينطبق / N/A')]
    lines_isolated = fields.Selection(PRECAUTION_STATES,string='الخطوط معزولة و/أو تفرغت / أو تجاوزت / Lines Blocked and/or Bleed/ or Bypassed')
    loto_applied = fields.Selection(PRECAUTION_STATES,string='تطبيق إجراءات تأمين/وضع علامات القفل / Lockout/Tag out Procedures Applied')
    line_dic = fields.Selection(PRECAUTION_STATES,string='Lines Disconnected / فصل الخطوط')
    line_liquid = fields.Selection(PRECAUTION_STATES,string='All Liquid Drained / جميع السوائل تم تفريغها')
    ventilation_fan = fields.Selection(PRECAUTION_STATES,string='تهوية ميكانيكية (مضخات هواء) / Ventilation Fan')
    # hot_work_permit = fields.Selection(PRECAUTION_STATES,string='تصريح عمل ساخن مطلوب؟ / Hot Work Permit Required')
    grounding_equipment = fields.Selection(PRECAUTION_STATES,string='تأريض المعدات / Equipment Grounding')

    job_planning_done = fields.Selection(PRECAUTION_STATES,string='تم التخطيط الوظيفي للعمل / تقييم السلامة / Job Planning/JSA done')
    emergency_plan_reviewed = fields.Selection(PRECAUTION_STATES,string='تمت توفير ومراجعة بيانات السلامة للمواد / MSDS Reviewed & available')
    all_personnel = fields.Selection(PRECAUTION_STATES,string='جميع الأفراد مدربين / All Personnel Trained')
    pre_job_meeting = fields.Selection(PRECAUTION_STATES,string='اجتماع سلامة ما قبل المهمة / Pre-task Meeting')
    communication_method = fields.Selection(PRECAUTION_STATES,string='يتوفر طريقة الاتصال / Communication Method')
    hse_notified = fields.Selection(PRECAUTION_STATES,string='تم إخطار ممثل السلامة / HSE Representative Notified')

    rescue_team_on_site = fields.Selection(PRECAUTION_STATES,string='مراجعة خطط الطوارئ / Emergency Plans Reviewed')
    assembly_system = fields.Selection(PRECAUTION_STATES,string='نقاط التجمع محددة / Assembly Points Established')
    rescue_team = fields.Selection(PRECAUTION_STATES,string='فريق الإنقاذ في الموقع / Rescue Team On Site')
    non_rescue = fields.Selection(PRECAUTION_STATES,string='إنقاذ بدون دخول / Non-Entry Rescue')
    retrieval_system = fields.Selection(PRECAUTION_STATES,string='نظام الاسترجاع متاح / Retrieval System Available')
    full_body_harness = fields.Selection(PRECAUTION_STATES,string='يوجد حزام كامل للجسم / Full Body Harness Required')
    emergency_contact = fields.Selection(PRECAUTION_STATES,string='الاتصال بالطوارئ / Emergency Contact')

    # معدات الوقاية الشخصية (PPE)
    ppe_gloves = fields.Selection(PRECAUTION_STATES,string='قفازات / Gloves')
    ppe_hearing = fields.Selection(PRECAUTION_STATES,string='حماية السمع / Hearing Protection')
    ppe_eye = fields.Selection(PRECAUTION_STATES,string='نظارات سلامة / Safety Goggles')
    ppe_face_shield = fields.Selection(PRECAUTION_STATES,string='واقي وجه / Face Shield')
    ppe_respirator_type = fields.Char(string='نوع جهاز التنفس / Respirator Type')
    hazard_movement = fields.Selection(PRECAUTION_STATES,string='Explosion Proof Equipment / معدات مقاومة للانفجار')

    # المخاطر الجسيمة (Hazard Identification)
    hazard_electrical = fields.Selection(PRECAUTION_STATES,string='مخاطر كهربائية / Electrical')
    hazard_engulfment = fields.Selection(PRECAUTION_STATES,string='خطر الغمر / Engulfment')
    hazard_chemical = fields.Selection(PRECAUTION_STATES,string='مواد كيميائية / Chemicals')
    hazard_noise = fields.Selection(PRECAUTION_STATES,string='ضوضاء مفرطة / Excessive Noise')
    hazard_heat_cold = fields.Selection(PRECAUTION_STATES,string='حرارة أو برودة / Heat/Cold')
    hazard_ventilation = fields.Selection(PRECAUTION_STATES,string='التهوية / Ventilation')
    hazard_entrapment = fields.Selection(PRECAUTION_STATES,string='الانحصار / Entrapment')

    # الجزء رقم #02D: ضوابط السلامة الإضافية
    ctrl_explosion_proof = fields.Selection(PRECAUTION_STATES,string='Explosion Proof Equipment / معدات مقاومة للانفجار')
    ctrl_fall_protection = fields.Selection(PRECAUTION_STATES,string='Fall Protection / حماية من السقوط')
    ctrl_fire_extinguisher = fields.Selection(PRECAUTION_STATES,string='Fire Extinguisher / طفاية حريق')
    ctrl_scaffolding = fields.Selection(PRECAUTION_STATES,string='Scaffolding / سقالات')
    ctrl_decontamination = fields.Selection(PRECAUTION_STATES,string='Decontamination facilities (Washing) / مرافق إزالة التلوث')
    ctrl_water_liquids = fields.Selection(PRECAUTION_STATES,string='Available Water/Liquids / المياه أو السوائل المتاحة')

    # الجزء رقم #02E: إجراءات تحكم إضافية (المخاطر الفيزيائية والجوية)
    # ضوابط الموقع
    ctrl_slip_trip = fields.Selection(PRECAUTION_STATES,string='Eliminate slip/trip hazards / القضاء على مخاطر الانزلاق والتعثر')
    ctrl_access_obstruction = fields.Selection(PRECAUTION_STATES,string='Eliminate access obstructions / مخاطر عوائق فتحات الوصول')
    ctrl_sharp_edges = fields.Selection(PRECAUTION_STATES,string='Sharp edges removed/protected / إزالة أو حماية الحواف الحادة')
    ctrl_barriers = fields.Selection(PRECAUTION_STATES,string='Physical barriers/barricades / تركيب الحواجز المادية أو المتاريس')

    # ضوابط المساحات والتهوية
    ctrl_forced_ventilation = fields.Selection(PRECAUTION_STATES,string='Forced ventilation / التهوية القسرية للقضاء على المخاطر الجوية')
    ctrl_contents_removed = fields.Selection(PRECAUTION_STATES,string='Space contents removed / تم إزالة محتويات المساحة')
    ctrl_lines_isolated = fields.Selection(PRECAUTION_STATES,string='Lines/Utilities isolated / عزل الخطوط الكيميائية والمرافق')
    ctrl_loto_tested = fields.Selection(PRECAUTION_STATES,string='LOTO & Try-out performed / تنفيذ إجراءات القفل والوسم والتجربة')

    # فريق العمل
    entry_team_ids = fields.One2many('confined.space.team', 'permit_id', string='طاقم الدخول')
    standby_person = fields.Char(string='شخص التأهب (المراقب) / Standby Person')
    rescue_team_name = fields.Char(string='فريق الإنقاذ / Rescue Team')

    supervisor_id = fields.Many2one('hr.employee', string='المشرف المباشر (المنفذ) / Direct Supervisor Executing')
    authorizer_id = fields.Many2one('hr.employee', string='المصرّح (مشرف/مهندس) / Authorizer (Eng/Sup)')
    safety_officer_id = fields.Many2one('hr.employee', string='المُمْنِح (مسئول السلامة) / Issuer (Safety Officer)')

    # الجزء رقم #04: التمديد والإغلاق
    extension_date_from = fields.Datetime(string='بداية التمديد / Extension From')
    extension_date_to = fields.Datetime(string='نهاية التمديد / Extension To')
    is_need_ptw = fields.Boolean(string='Is Need PTW? / هل يحتاج الي تصريح عمل اخر', default=False)
    type_of_ptw = fields.Selection([
        ('hot_work', 'Hot Work Permit'),
        ('blasting', 'Blasting Space Permit'),
        ('cold_work', 'Cold Work Permit'),
        ('excavation', 'Excavation Work Permit'),
        ('highway', 'High Work Permit'),
        ('lifting', 'Lifting Work Permit'),
        ('loto', 'Loto Work Permit'),
    ], string='Type Of PTW / نوع تصريح العمل الاخر')
    linked_hot_ptw = fields.Many2one('hot.work.permit', string='Related PTW', readonly=True)
    linked_blasting_ptw = fields.Many2one('blasting.work.permit', string='Related PTW', readonly=True)
    linked_cold_ptw = fields.Many2one('cold.work.permit', string='Related PTW', readonly=True)
    linked_excavation_ptw = fields.Many2one('excavation.work.permit', string='Related PTW', readonly=True)
    linked_highway_ptw = fields.Many2one('work.height.permit', string='Related PTW', readonly=True)
    linked_lifting_ptw = fields.Many2one('lifting.work.permit', string='Related PTW', readonly=True)
    linked_loto_ptw = fields.Many2one('loto.work.permit', string='Related PTW', readonly=True)

    linked_ptw_count = fields.Integer(compute='_compute_linked_ptw_count')
    # الحقول الجديدة
    closed_date = fields.Datetime(string='تاريخ الإغلاق / Closing Date', readonly=True)
    work_site = fields.Many2one('work.site', string='موقع العمل / Work site', ondelete='set null', tracking=True)
    duration_display = fields.Char(string='مدة التصريح / Duration', compute='_compute_duration')
    confirmation_check = fields.Boolean(
        string='أقر بأن جميع البيانات صحيحة وموافق على كافة إرشادات السلامة / I confirm that all information is correct and I agree to all safety instructions',
        required=True
    )

    def _compute_linked_ptw_count(self):
        for rec in self:
            # يجمع أي سجل مرتبك في الحقول التي عرفتها أنت
            counts = [rec.linked_hot_ptw, rec.linked_blasting_ptw, rec.linked_cold_ptw,
                      rec.linked_excavation_ptw, rec.linked_highway_ptw, rec.linked_lifting_ptw, rec.linked_loto_ptw]
            rec.linked_ptw_count = len([c for c in counts if c])

    def action_create_related_ptw(self):
        self.ensure_one()
        if not self.type_of_ptw:
            raise UserError("الرجاء اختيار نوع التصريح أولاً / Please select PTW type first")

        # خريطة الربط بين الاختيار واسم الموديل واسم الحقل في موديولك
        ptw_map = {
            'hot_work': {'model': 'hot.work.permit', 'field': 'linked_hot_ptw'},
            'blasting': {'model': 'blasting.work.permit', 'field': 'linked_blasting_ptw'},
            'cold_work': {'model': 'cold.work.permit', 'field': 'linked_cold_ptw'},
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
            'work': 'linked_hot_ptw', 'blasting': 'linked_blasting_ptw', 'cold_work': 'linked_cold_ptw',
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


    def action_submit(self):
        for rec in self:
            if not rec.confirmation_check:
                raise UserError("يجب عليك الموافقة على صحة البيانات أولاً!")
            
            if rec.is_need_ptw:
                related_ptws = [rec.linked_cold_ptw, rec.linked_blasting_ptw, rec.linked_hot_ptw,
                                rec.linked_excavation_ptw, rec.linked_highway_ptw, rec.linked_lifting_ptw,
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
        self.closed_date = fields.Datetime.now()
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


class ConfinedSpaceTeam(models.Model):
    _name = 'confined.space.team'
    _description = 'أعضاء فريق الدخول / Confined Space Team Members'

    permit_id = fields.Many2one('confined.space.permit', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee / الموظف', required=True)
    position = fields.Char(string='Position / الوظيفة')
    signature = fields.Binary(string='Signature / التوقيع')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.position = self.employee_id.job_title or self.employee_id.job_id.name