from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date, timedelta,datetime
from odoo.exceptions import  UserError,ValidationError


class KpiNonExective(models.Model):
    _name = 'kpi.non.exective'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'name'

    @api.model
    def default_get(self, fields):
        res = super(KpiNonExective, self).default_get(fields)
        if res.get('req_id', False):
            emp = self.env['hr.employee'].sudo().search([('user_id', '=', res['req_id'])],
                                                        limit=1)
            if not res.get('department_id', False):
                res.update({
                    'department_id': emp.department_id.id,
                })
        return res

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    date = fields.Date(default=fields.Date.today())
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True)
    department_id = fields.Many2one('hr.department', string="Department")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    state = fields.Selection(
        [('draft', 'Draft'), ('emp_approve', 'Employee Comment'),
         ('wlm_approve', 'Waiting Line Manager'),
         ('w_director_approve', 'Waiting Director Approve'),
         ('w_c_level_approve', 'Waiting C Level Approve'),
         ('w_hr_m', 'Waiting HR Manager Approve'),
         ('reject', 'reject'),
         ('approved', 'Approved')],
        string='Status', default='draft', track_visibility='onchange')
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    employee_id = fields.Many2one("hr.employee", string="Name")
    job_id = fields.Many2one('hr.job', string="Position Title", related='employee_id.job_id', readonly=True)
    emp_code = fields.Char( readonly=True, string="Staff No", store=True)
    emp_department_id = fields.Many2one(related="employee_id.department_id", string="Division/Department/Section")
    report_emp_id = fields.Many2one("hr.employee", string="Report To", related="employee_id.parent_id", )
    emp_approve_date = fields.Datetime(string='Date Approve', readonly=1)
    date_from = fields.Date(string="From")
    date_to = fields.Date(string="To")
    lmn_comment = fields.Text(string="COMMENTS OF APPRAISER")
    display_name = fields.Char(compute='compute_display_name', string="Name", store=False)
    kpi_no_ids = fields.One2many(comodel_name="kpi.non.line", inverse_name="request_id", copy=1)
    comments = fields.Text(string="Comments & Recommendations:  التعليقات والتوصيات")
    situations_events = fields.Text(
        string="Situations/ Events Describe the situation/ events the Appraise encountered during the Appraisal period. المواقف / الأحداث ، وصف المواقف أو الأحداث التي واجهها الموظف خلال فترة التقييم")
    sign_or_extra = fields.Text(
        string="Significant or Extra Contribution and Efforts  Describe the extra contribution and efforts taken by Appraise to address or overcome the said situation/ events. مساهمات و جهود إضافية ، وصف المساهمات و الجهود الإضافية التي بذلها  الموظف للمعالجة أو التغلب على المواقف / الأحداث المذكورة")
    result_achived = fields.Text(
        string="Results Achieved from the Extra Contributions and Efforts Taken Describe the benefits e.g. cost/ time saving, resource optimization, speedy processing time etc. as a result of the extra contribution and efforts taken by Appraise.                                                 النتائج التي تم تحقيقها من المساهمات الإضافية والجهود المبذولة، وصف الفوائد، على سبيل المثال: توفير التكلفة / الوقت، تحسين  استخدام الموارد، سرعة المعالجة ")
    situations_events_describe = fields.Text(
        string="Situations/ Events Describe the situation/ events the Appraise encountered during the Appraisal period.  المواقف / الأحداث ، وصف المواقف                    أو الأحداث التي واجهها الموظف خلال فترة التقييم")
    poor_performance_record = fields.Text(
        string="Poor Performance Records Describe the poor performance by Appraise to address or overcome the said situation/ events. سجلات الأداء الضعيف، يتم وصف الأداء الضعيف للموظف في الموقف / الأحداث المذكورة")
    result_achived_from_poor = fields.Text(
        string="Results Achieved from the Poor Performance Records  Describe the bad impact e.g. cost/ time wasting, bad resource optimization, as a result of the poor performance or negligence taken by Appraise. النتائج المسببة لحدوث الأداء الضعيف، وصف التأثير السلبي على سبيل المثال: إهدار التكلفة / الوقت ، وسوء استخدام الموارد، الإهمال ")
    answer_qt1 = fields.Integer()
    answer_qt2 = fields.Integer()
    answer_qt3 = fields.Integer()
    answer_qt4 = fields.Integer()
    answer_qt5 = fields.Integer()
    answer_qt6 = fields.Integer()
    answer_qt7 = fields.Integer()
    answer_qt8 = fields.Integer()
    answer_qt9 = fields.Integer()
    answer_qt10 = fields.Integer()
    score_qt1 = fields.Float(compute='_compute_score')
    score_qt2 = fields.Float(compute='_compute_score')
    score_qt3 = fields.Float(compute='_compute_score')
    score_qt4 = fields.Float(compute='_compute_score')
    score_qt5 = fields.Float(compute='_compute_score')
    score_qt6 = fields.Float(compute='_compute_score')
    score_qt7 = fields.Float(compute='_compute_score')
    score_qt8 = fields.Float(compute='_compute_score')
    score_qt9 = fields.Float(compute='_compute_score')
    score_qt10 = fields.Float(compute='_compute_score')
    total_score = fields.Float(string="Total Score", compute='_total_score',group_operator=False)
    review_state = fields.Selection(string="", selection=[('mid_year_review', 'Mid year review'), ('final_year_review', 'Final year review')], required=True,default='mid_year_review' )






    @api.constrains('employee_id', 'review_state', 'create_date')
    def _check_duplicate_review(self):
        for record in self:
            if not record.create_date:
                continue

            year = record.create_date.year

            domain = [
                ('employee_id', '=', record.employee_id.id),
                ('review_state', '=', record.review_state),
                ('create_date', '>=', f'{year}-01-01 00:00:00'),
                ('create_date', '<=', f'{year}-12-31 23:59:59'),
                ('id', '!=', record.id)
            ]
            duplicate = self.search_count(domain)

            if duplicate:
                raise ValidationError('Each employee can only have one Mid-Year and one Final-Year review per year.')

    @api.onchange('review_state')
    def compute_dates(self):
        for record in self:
            if record.review_state:
                if record.review_state == 'mid_year_review':
                    current_year = date.today().year
                    record.date_from =  date(current_year, 1, 1)
                    record.date_to = date(current_year, 6, 30)
                elif record.review_state == 'final_year_review':
                        current_year = date.today().year
                        record.date_from =  date(current_year, 1, 1)
                        record.date_to = date(current_year, 12, 31)
    @api.depends('review_state')
    def _compute_depends_dates(self):
        for record in self:
            if record.review_state:
                if record.review_state == 'mid_year_review':
                    current_year = date.today().year
                    record.date_from =  date(current_year, 1, 1)
                    record.date_to = date(current_year, 6, 30)
                elif record.review_state == 'final_year_review':
                        current_year = date.today().year
                        record.date_from =  date(current_year, 1, 1)
                        record.date_to = date(current_year, 12, 31)

    def _total_score(self):
        for rec in self:
            if rec.score_qt1 or rec.score_qt2 or rec.score_qt3 or rec.score_qt4 or rec.score_qt5 or rec.score_qt6 or rec.score_qt7 or rec.score_qt8 or rec.score_qt9 or rec.score_qt10:
                rec.total_score = rec.score_qt1 + rec.score_qt2 + rec.score_qt3 + rec.score_qt4 + rec.score_qt5 + rec.score_qt6 + rec.score_qt7 + rec.score_qt8 + rec.score_qt9 + rec.score_qt10
            else:
                rec.total_score = 0

    def _compute_score(self):
        for rec in self:
            if rec.answer_qt1:
                rec.score_qt1 = rec.answer_qt1 / 10
            else:
                rec.score_qt1 = 0

            if rec.answer_qt2:
                rec.score_qt2 = rec.answer_qt2 / 10
            else:
                rec.score_qt2 = 0

            if rec.answer_qt3:
                rec.score_qt3 = rec.answer_qt3 / 10
            else:
                rec.score_qt3 = 0

            if rec.answer_qt4:
                rec.score_qt4 = rec.answer_qt4 / 10
            else:
                rec.score_qt4 = 0

            if rec.answer_qt5:
                rec.score_qt5 = rec.answer_qt5 / 10
            else:
                rec.score_qt5 = 0

            if rec.answer_qt6:
                rec.score_qt6 = rec.answer_qt6 / 10
            else:
                rec.score_qt6 = 0

            if rec.answer_qt7:
                rec.score_qt7 = rec.answer_qt7 / 10
            else:
                rec.score_qt7 = 0

            if rec.answer_qt8:
                rec.score_qt8 = rec.answer_qt8 / 10
            else:
                rec.score_qt8 = 0

            if rec.answer_qt9:
                rec.score_qt9 = rec.answer_qt9 / 10
            else:
                rec.score_qt9 = 0

            if rec.answer_qt10:
                rec.score_qt10 = rec.answer_qt10 / 10
            else:
                rec.score_qt10 = 0

    def action_draft(self):
        return self.write({'state': 'draft'})

    def action_submit(self):
        return self.write({'state': 'emp_approve'})

    def action_lmn_approve(self):
        line_manager = False
        try:
            line_manager = self.req_id.line_manager_id
        except:
            line_manager = False

        if not line_manager or line_manager != self.env.user:
            raise UserError("Sorry. You are not authorized to approve this document!")

        # Check if the director exists
        director = self.employee_id.department_id.director_id

        if not director:
            return self.write({'state': 'w_c_level_approve'})
        else:
            return self.write({'state': 'w_director_approve'})

    def action_director_approve(self):
        director = False
        try:
            director = self.employee_id.department_id.director_id
        except:
            director = False
        if not director or director!= self.env.user:
            raise UserError("Sorry. Your are not authorized to approve this document!")
        return self.write({'state': 'w_c_level_approve'})

    def action_c_level_approve(self):
        c_level_id = False
        try:
            c_level_id = self.employee_id.department_id.c_level_id
        except:
            c_level_id = False
        if not c_level_id or c_level_id != self.env.user:
            raise UserError("Sorry. Your are not authorized to approve this document!")
        return self.write({'state': 'w_hr_m'})


    def action_hr_manager_approve(self):
        return self.write({'state': 'approved'})

    def action_emp_approve(self):
        line_manager = False
        try:
            line_manager = self.req_id.line_manager_id
        except:
            line_manager = False
        if not line_manager or line_manager != self.env.user:
            raise UserError("Sorry. Your are not authorized to approve this document!")
        return self.write({'state': 'wlm_approve'})

    @api.depends('date_from', 'date_to')
    def compute_display_name(self):
        for rec in self:
            display_name = ""
            if rec.date_from and rec.date_to:
                display_name = str(rec.date_from) + " -> " + str(rec.date_to)
            rec.display_name = display_name


    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('kpi.non.person.code') or ' '
        res = super(KpiNonExective, self).create(vals)
        return res


    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(KpiNonExective, self).unlink()


class KpiNonLine(models.Model):
    _name = 'kpi.non.line'

    request_id = fields.Many2one("kpi.non.exective", string="Employee")

    no_que = fields.Integer()
    que = fields.Text(string="Questions")
    rating = fields.Selection(string="Answers ( Rating )",
                              selection=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ],
                              required=True, )
    weight = fields.Integer(default=10)
    total_score = fields.Float(string="Total Score", compute='_total_score')

    def _total_score(self):
        for rec in self:
            if rec.rating:
                rec.total_score = int(rec.rating) / rec.weight
            else:
                rec.total_score = 0
