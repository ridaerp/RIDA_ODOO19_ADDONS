# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import  UserError


class ColdWorkPermit(models.Model):
    _name = 'cold.work.permit'
    _description = 'تصريح عمل بارد / Cold Work Permit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    name = fields.Char(string='رقم التصريح / Permit Number', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))

    def unlink(self):
        if self.state != 'draft':
            raise UserError("You cannot delete this Cold Work Permit. Only DRAFT records can be deleted.")
        return super(ColdWorkPermit, self).unlink()

    # الحالات - تم توحيدها مع الأزرار
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

    # الجزء الأول: بيانات العمل
    date_from = fields.Datetime(string='من / From' , tracking=True)
    date_to = fields.Datetime(string='إلى / To' , tracking=True)
    shift = fields.Selection([('day', 'نهارية / Day'), ('night', 'ليلية / Night')], string='الوردية / Shift')
    work_site = fields.Many2one('work.site',string='موقع العمل / Work Site' ,ondelete='set null', tracking=True)
    sub_location = fields.Char(string='الموقع الفرعي / Sub Location', tracking=True)
    workers_count = fields.Integer(string='عدد العاملين / No. of Workers')
    date_request = fields.Datetime(
        string='Request Date',
        readonly=True,
        default=lambda self: fields.Datetime.now()
    )
    department_id = fields.Many2one('hr.department', string='القسم / Department',
                                    default=lambda self: self.env.user.employee_id.department_id)
    department_ids = fields.Many2many('hr.department', string='الاقسام المعنية / Departments Involved')
    work_nature = fields.Selection([
        ('mechanical', 'صيانة ميكانيكية / Mechanical Maintenance'),
        ('electrical', 'صيانة كهربائية / Electrical Maintenance'),
        ('mech_elec', 'صيانة كهربائية / صيانة ميكانيكية'),
        ('other', 'أخرى / Other')
    ], string='طبيعة العمل / Work Nature')
    other_work_description = fields.Char(string='توضيح أخرى / Other Explanation')
    task_description = fields.Text(string='وصف المهمة / Task Description')
    tools_used = fields.Text(string='المعدات المستخدمة / Tools Used')

    # الجزء الثاني: التحكم بالمخاطر (تم تصحيح التكرار والأسماء)
    PRECAUTION_STATES = [('yes', 'نعم / Yes'), ('no', 'لا / No'), ('na', 'لا ينطبق / N/A')]
    crew_introduced = fields.Selection(PRECAUTION_STATES,string='تعريف الطاقم بالمسئوليات؟ / Crew Briefed on Roles?')
    hazards_explained = fields.Selection(PRECAUTION_STATES,string='شرح المخاطر والوقاية؟ / Hazards & Prevention Explained?')
    emergency_explained = fields.Selection(PRECAUTION_STATES,string='شرح إجراءات الطوارئ؟ / Emergency Procedures Explained?')
    energy_isolated = fields.Selection(PRECAUTION_STATES,string='عزل مصادر الطاقة؟ / Energy Sources Isolated?')
    area_cleaned = fields.Selection(PRECAUTION_STATES,string='نظافة وسلامة المنطقة؟ / Area Reviewed & Cleaned?')
    safety_tools_available = fields.Selection(PRECAUTION_STATES,string='توفر أدوات السلامة؟ / Safety Tools Available?')
    warning_signs_placed = fields.Selection(PRECAUTION_STATES,string='وضع العلامات التحذيرية؟ / Warning Signs Placed?')
    assistant_assigned = fields.Selection(PRECAUTION_STATES,string='تحديد شخص مساعد؟ / Assistant Person Assigned?')
    weather_suitable = fields.Selection(PRECAUTION_STATES,string='الأحوال الجوية ملائمة؟ / Weather Suitable?')

    checked = fields.Boolean(string='تم التحقق من كافة البنود المذكورة أعلاه بغرض تقليل المخاطر المرتبطة بالمهمة / All the above items have been checked in order to minimize the risks associated with the mission')

    # حقول التمديد
    extension_date_from = fields.Datetime(string='بداية التمديد / Extension From')
    extension_date_to = fields.Datetime(string='نهاية التمديد / Extension To')

    # أدوات السلامة الشخصية (PPE)
    ppe_mask_count = fields.Integer(string='قناع واقي / Protective Mask')
    ppe_ear_count = fields.Integer(string='سدادة أذن / Ear Safety')
    ppe_gloves_count = fields.Integer(string='قفازات سلامة / Safety Gloves')
    ppe_belt_count = fields.Integer(string='حزام سلامة / Safety Belt')

    # الاعتمادات
    requester_id = fields.Many2one('res.users', string='مقدم التصريح / Requester', default=lambda self: self.env.user)
    supervisor_id = fields.Many2one('hr.employee', string='المشرف المباشر / Direct Supervisor')
    authorizer_id = fields.Many2one('hr.employee', string='المصرّح / Authorizer')
    issuer_id = fields.Many2one('hr.employee', string='المُمْنِح (مسؤول السلامة) / Issuer')

    is_need_ptw = fields.Boolean(string='Is Need PTW? / هل يحتاج الي تصريح عمل اخر', default=False)
    type_of_ptw = fields.Selection([
        ('hot_work', 'Hot Work Permit'),
        ('blasting', 'Blasting Space Permit'),
        ('confined', 'Confined Space Permit'),
        ('excavation', 'Excavation Work Permit'),
        ('highway', 'High Work Permit'),
        ('lifting', 'Lifting Work Permit'),
        ('loto', 'Loto Work Permit'),
    ], string='Type Of PTW / نوع تصريح العمل')
    linked_hot_ptw = fields.Many2one('hot.work.permit', string='Related PTW', readonly=True)
    linked_blasting_ptw = fields.Many2one('blasting.work.permit', string='Related PTW', readonly=True)
    linked_confined_ptw = fields.Many2one('confined.space.permit', string='Related PTW', readonly=True)
    linked_excavation_ptw = fields.Many2one('excavation.work.permit', string='Related PTW', readonly=True)
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

    def _compute_linked_ptw_count(self):
        for rec in self:
            # يجمع أي سجل مرتبك في الحقول التي عرفتها أنت
            counts = [rec.linked_hot_ptw, rec.linked_blasting_ptw, rec.linked_confined_ptw,
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
            'work': 'linked_hot_ptw', 'blasting': 'linked_blasting_ptw', 'confined': 'linked_confined_ptw',
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
            val['name'] = self.env['ir.sequence'].next_by_code('cold.work.permit') or ' '

        return super(ColdWorkPermit, self).create(vals)

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

    def action_done(self):
        for rec in self:
            rec.state = 'pending_close'

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

