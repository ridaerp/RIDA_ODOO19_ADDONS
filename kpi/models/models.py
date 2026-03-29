# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, timedelta,datetime
from odoo.exceptions import  UserError,ValidationError


class KpiPerson(models.Model):
    _name = 'kpi.person'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _rec_name = 'name'

    @api.model
    def default_get(self, fields):
        res = super(KpiPerson, self).default_get(fields)
        if res.get('req_id', False):
            emp = self.env['hr.employee'].sudo().search([('user_id', '=', res['req_id'])], limit=1)

            kpi_competency_ids = self.env['kpi.competency'].create([
                {
                    'name': 'BUSINESS ACUMENT \n Has a clear understanding of RIDA Group’s business model and applies business drivers such as revenue, costs, customer needs, people management and market trends to achieve short and long-term objectives.',
                }, {
                    'name': 'RESULTS ORIENTED \n Consistently meet or exceed individual and team objectives; focusing on what needs to be done and making it happen. It is about improving personal performance in order to improve RIDA Group performance.',
                }, {
                    'name': 'EFFECTIVE COMMUNICATIONS \n Convey relevant information to others in a clear and timely way; listen openly to others; use appropriate influencing and conflict resolution methods.',
                }, {
                    'name': 'LEAD & DEVELOP OTHERS \n Engage and lead others regarding the need for best-in-class performance; adapt to changes in RIDA Group direction through constructive feedback and other approaches such as work assignments, coaching, mentoring and able to link learning goals to changing business needs.',
                }, {
                    'name': 'TEAM ORIENTED \n Build effective and productive teams with the right set of diverse skills and talent to achieve organizational results.',
                }, {
                    'name': 'MOTIVATED & COMMITTED \n Identifying and dealing with issues proactively and persistently; seizing opportunities that arise by having initiative to take action. Highly engaged to produce results for RIDA Group, action-oriented and act in the present to create value in the future.',
                },
                {
                    'name': 'PLANNING CULTURE \n This competency structure can serve as the foundation for developing individual performance objectives and training programs. It ensures that planning, scheduling, and implementing activities are aligned across all levels, helping improve both operational efficiency and strategic alignment within the gold mining business.',
                }, {
                    'name': 'EMBRACING NEW TECHNOLOGIES AND SKILLS \n This behavioral competency framework ensures that employees at all levels in the gold mining business are prepared for the challenges of embracing new technologies and skills. It promotes a mindset of continuous improvement, from basic skills at the operational level to strategic leadership in the executive ranks.',
                }, {
                    'name': 'QHSE CULTURE \n This competency structure can be used as a foundation for performance reviews and training programs. It ensures alignment with the company\'s goals while empowering individuals at all levels to contribute to a culture of safety and quality.',
                }
            ])

            if not res.get('department_id', False):
                res.update({
                    'department_id': emp.department_id.id,
                    'kpi_competency_ids': [(6, 0, kpi_competency_ids.ids)],
                })
        return res

    def action_update_all_old_kpis(self):
        # نحدد السجلات المختارة أو كل السجلات في النظام
        records_to_update = self if self else self.search([])

        new_competencies_data = [
            {
                'key': 'PLANNING CULTURE',
                'name': 'PLANNING CULTURE \n This competency structure can serve as the foundation for developing individual performance objectives and training programs. It ensures that planning, scheduling, and implementing activities are aligned across all levels, helping improve both operational efficiency and strategic alignment within the gold mining business.',
            },
            {
                'key': 'EMBRACING NEW TECHNOLOGIES',
                'name': 'EMBRACING NEW TECHNOLOGIES AND SKILLS \n This behavioral competency framework ensures that employees at all levels in the gold mining business are prepared for the challenges of embracing new technologies and skills. It promotes a mindset of continuous improvement, from basic skills at the operational level to strategic leadership in the executive ranks.',
            },
            {
                'key': 'QHSE CULTURE',
                'name': 'QHSE CULTURE \n This competency structure can be used as a foundation for performance reviews and training programs. It ensures alignment with the company\'s goals while empowering individuals at all levels to contribute to a culture of safety and quality.',
            }
        ]

        for rec in records_to_update:
            # 1. إرجاع السجل إلى حالة المسودة (Draft)
            # تأكد أن اسم الحقل في الموديل الخاص بك هو 'state' واسم الحالة هو 'draft'
            rec.write({'state': 'draft'})

            # 2. إضافة التقييمات الثلاثة الجديدة
            for comp in new_competencies_data:
                exists = rec.kpi_competency_ids.filtered(lambda c: comp['key'] in (c.name or ''))
                if not exists:
                    new_comp = self.env['kpi.competency'].create({'name': comp['name']})
                    rec.write({'kpi_competency_ids': [(4, new_comp.id)]})

        return False

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    date = fields.Date(default=fields.Date.today())
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True)
    department_id = fields.Many2one('hr.department', string="Department")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    state = fields.Selection(
        [('draft', 'Draft'), ('emp_acceptance', 'Employee Acceptance'),
         ('wlm_approve', 'Waiting Line Manager'),
         ('emp_approve', 'Employee Comment'),
         ('w_director_approve', 'Director Decision'),
         ('w_c_level_approve', 'Chief Decision'),
         ('w_hr_m', 'HR Manager Approve'),
         ('reject', 'reject'),
         ('approved', 'Approved')],
        string='Status', default='draft', tracking=True)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    employee_id = fields.Many2one("hr.employee", string="Name")
    job_id = fields.Many2one('hr.job', string="Position Title", related='employee_id.job_id', readonly=True)
    emp_code = fields.Char( readonly=True, string="Staff No", store=True)
    emp_department_id = fields.Many2one(related="employee_id.department_id", string="Division/Department/Section")
    report_emp_id = fields.Many2one("hr.employee", string="Report To", related="employee_id.parent_id", )
    emp_approve_date = fields.Datetime(string='Date Approve', readonly=1)
    date_from = fields.Date(string="From")
    date_to = fields.Date(string="To")
    kpi_ids = fields.One2many(comodel_name="kpi.works", inverse_name="request_id",
                              string="PART || : KEY PERFORMANCE INDICATOR WORKS", copy=1)
    kpi_competency_ids = fields.One2many(comodel_name="kpi.competency", inverse_name="request_id",
                                         string="KPI competenct", copy=1)
    kpi2_more_info = fields.Boolean(string="More Information", default=True)
    kpi3_more_info = fields.Boolean(string="More Information", default=True)
    kpi4_more_info = fields.Boolean(string="More Information", default=True)
    emp_comment = fields.Text(string="COMMENTS OF EMPLOYEE")
    lmn_comment = fields.Text(string="COMMENTS OF APPRAISER")
    overall_weight_kpi = fields.Float(string="WEIGHT (%)", compute='_compute_overall')
    overall_weight_competency = fields.Float(string="WEIGHT (%)", compute='_compute_overall')
    total_overall_weight = fields.Float(string="WEIGHT (%)", compute='_compute_overall')
    total_weigh_kpi = fields.Integer(string="WEIGHT (%)", default='60', readonly=1)
    total_weight_competency = fields.Integer(string="WEIGHT (%)", default='40', readonly=1)
    total_weight_kpi_competenct = fields.Integer(string="WEIGHT (%)", compute='_compute_overall')
    overall_score_kpi = fields.Float(string="SCORE", compute='_compute_kpi2')
    overall_score_competency = fields.Float(string="SCORE", compute='_compute_kpi2')
    total_overall_score = fields.Float(string="WEIGHT (%)", compute='_compute_overall',store=True)
    total_score_actual = fields.Integer(string="SCORE", compute='_compute_kpi2')
    last_rating = fields.Integer(string="RATING", compute='compute_last_rating',group_operator=False,store=True)
    display_name = fields.Char(compute='compute_display_name', string="Name", store=False)
    review_state = fields.Selection(string="", selection=[('mid_year_review', 'Mid year review'), ('final_year_review', 'Final year review')],)
    review_ids = fields.One2many('kpi.review', 'person_id', string="Reviews")
    review_count = fields.Integer(string="Review Count", compute="_compute_review_count")
    year = fields.Selection(
        [(str(y), str(y)) for y in range(2020, datetime.now().year + 2)],
        string='Year',
        default=lambda self: str(datetime.now().year)
    )
    show_mid_year_button = fields.Boolean(compute='_compute_show_buttons', string="Show Mid Year Button")
    show_final_year_button = fields.Boolean(compute='_compute_show_buttons', string="Show Final Year Button")
    round_number = fields.Integer(string="Evaluation Round", default=1)
    previous_review_id = fields.Many2one('kpi.person', string="Previous Evaluation")



    def action_lm_new_approve(self):
        self.ensure_one()
        self.write({'state': 'w_director_approve'})
        return True



    def action_re_evaluate_employee(self):
        for rec in self:
            new_round = rec.round_number + 1
            new_competencies = []
            for comp in rec.kpi_competency_ids:
                new_competencies.append((0, 0, {
                    'name': comp.name,
                    'kpi_weight': comp.kpi_weight,
                    'behavior_evaluation': comp.behavior_evaluation,
                    'kpi2_weight_score': comp.kpi2_weight_score,
                }))
            new_kpis = []
            for kpi in rec.kpi_ids:
                new_kpis.append((0, 0, {
                    'sequence': kpi.sequence or 0,
                    'kpi_indicator': kpi.kpi_indicator or '',
                    'performance_measure': kpi.performance_measure or '',
                    'kpi2_weight': kpi.kpi2_weight or 0.0,
                    'kpi2_plan_target': kpi.kpi2_plan_target or 0,
                }))

            new_review = rec.copy(default={
                'name': f"{rec.name or 'KPI Review'} - Round {new_round}",
                'state': 'wlm_approve',
                'round_number': new_round,
                'previous_review_id': rec.id,
                'kpi_competency_ids': new_competencies,
                'kpi_ids': new_kpis,
            })

            # فتح التقييم الجديد في واجهة Odoo
            return {
                'name': f"Re-Evaluation: {rec.name}",
                'type': 'ir.actions.act_window',
                'res_model': 'kpi.person',
                'view_mode': 'form',
                'res_id': new_review.id,
                'target': 'current',
            }

    @api.depends('employee_id', 'year')
    def _compute_show_buttons(self):
        today = date.today()
        for rec in self:
            rec.show_mid_year_button = False
            rec.show_final_year_button = False
            if not rec.employee_id or not rec.year:
                continue

            if date(today.year, 6, 1) <= today <= date(today.year, 6, 25):
                rec.show_mid_year_button = True

                # Final-Year: 1 December → 25 December
            if date(today.year, 12, 1) <= today <= date(today.year, 12, 25):
                rec.show_final_year_button = True

    @api.depends('total_overall_score')
    def compute_last_rating(self):
        for rec in self:
            score = rec.total_overall_score or 0.0

            if score < 1.5:
                rec.last_rating = 1
            elif score < 2.5:
                rec.last_rating = 2
            elif score < 3.5:
                rec.last_rating = 3
            elif score < 4.5:
                rec.last_rating = 4
            else:
                rec.last_rating = 5

    # @api.depends('total_overall_score')
    # def compute_last_rating(self):
    #     for rec in self:
    #         if rec.total_overall_score:
    #             if rec.total_overall_score < 1.49:
    #                 rec.last_rating = 1
    #             elif 1.50 <= rec.total_overall_score <= 2.49:
    #                 rec.last_rating = 2
    #             elif 2.50 <= rec.total_overall_score <= 3.49:
    #                 rec.last_rating = 3
    #             elif 3.50 <= rec.total_overall_score <= 4.49:
    #                 rec.last_rating = 4
    #             elif rec.total_overall_score > 4.49:
    #                 rec.last_rating = 5
    #         else:
    #             rec.last_rating = 0

    @api.onchange('review_state')
    def _onchange_review_state(self):
        """Automatically set date_from/date_to based on review type."""
        current_year = date.today().year
        for record in self:
            if record.review_state == 'mid_year_review':
                record.date_from = date(current_year, 1, 1)
                record.date_to = date(current_year, 6, 30)
            elif record.review_state == 'final_year_review':
                record.date_from = date(current_year, 1, 1)
                record.date_to = date(current_year, 12, 31)
            else:
                record.date_from = False
                record.date_to = False


    @api.depends('date_from', 'date_to')
    def compute_display_name(self):
        for rec in self:
            display_name = ""
            if rec.date_from and rec.date_to:
                display_name = str(rec.date_from) + " -> " + str(rec.date_to)
            rec.display_name = display_name

    @api.depends('kpi_ids', 'kpi_competency_ids', 'overall_weight_competency', )
    def _compute_overall(self):
        for rec in self:
            if rec.kpi_ids or rec.kpi_competency_ids or rec.overall_weight_competency:
                rec.overall_weight_kpi = sum(rec.kpi2_weight_score for rec in rec.kpi_ids)
                rec.overall_weight_competency = sum(rec.kpi2_weight_score for rec in rec.kpi_competency_ids)
                rec.total_overall_weight = rec.overall_weight_kpi + rec.overall_weight_competency
                if rec.total_weigh_kpi > 0 and rec.total_weight_competency > 0:
                    rec.total_weight_kpi_competenct = rec.total_weigh_kpi + rec.total_weight_competency
                rec.overall_score_kpi = rec.overall_weight_kpi * 0.60
                rec.overall_score_competency = rec.overall_weight_competency * 0.40
                rec.total_overall_score = rec.overall_score_kpi + rec.overall_score_competency

            else:
                rec.overall_weight_kpi = 0
                rec.overall_weight_competency = 0
                rec.total_overall_weight = 0
                rec.total_weight_kpi_competenct = 0
                rec.overall_score_kpi = 0
                rec.overall_score_competency = 0
                rec.total_overall_score = 0

    @api.constrains('kpi_ids', 'kpi_competency_ids')
    def constraint_field_Request_KPI(self):
        # if self.kpi_ids:
        #     if len(self.kpi_ids) < 5:
        #         raise UserError('Please add 5 KPIs Minimum')
        total_kip_weight = sum(rec.kpi2_weight for rec in self.kpi_ids)
        total_competency_weight = sum(rec.kpi_weight for rec in self.kpi_competency_ids)
        total_kpi2_weight_score = sum(rec.kpi2_weight_score for rec in self.kpi_ids)
        total_competency_weight_score = sum(rec.kpi2_weight_score for rec in self.kpi_competency_ids)
        if total_kip_weight > 100 or total_competency_weight > 100:
            raise UserError("The KPI and Competency Weight Must be Less or Equal 100")
        if total_kpi2_weight_score > 5.00 or total_competency_weight_score > 5.00:
            raise UserError("The KPI and Competency weight Score Must be Less or Equal 5")

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('kpi.person.code') or ' '

        return super(KpiPerson, self).create(vals)

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")
        return super(KpiPerson, self).unlink()

    def action_submit(self):
        # return self.write({'state': 'emp_acceptance'})
        return self.write({'state': 'wlm_approve'})

    def action_draft(self):
        return self.write({'state': 'draft'})

    def action_emp_acceptance(self):
        # return self.write({'state': 'wlm_approve'})
        return self.write({'state': 'w_director_approve'})

    def action_wlm_approve(self):
        line_manager = False
        try:
            line_manager = self.req_id.line_manager_id
        except:
            line_manager = False

        if not line_manager or line_manager != self.env.user:
            raise UserError("Sorry. You are not authorized to approve this document!")

        self.write({'state': 'emp_approve'})

    def action_emp_approve(self):
        line_manager = False
        try:
            line_manager = self.req_id.line_manager_id
        except:
            line_manager = False
            # Check if the director exists
        self.emp_approve_date = fields.Datetime.now()
        director = self.employee_id.department_id.director_id

        if not director:
            return self.write({'state': 'w_c_level_approve'})
        else:
            return self.write({'state': 'w_director_approve'})






    def action_lmn_approve(self):
        line_manager = False
        try:
            line_manager = self.req_id.line_manager_id
        except:
            line_manager = False

        if not line_manager or line_manager != self.env.user:
            raise UserError("Sorry. You are not authorized to approve this document!")

        return self.write({'state': 'emp_approve'})
   


    def action_director_approve(self):
        director = False
        try:
            director = self.employee_id.department_id.director_id
        except:
            director = False
        if not director or director != self.env.user:
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

    # def _compute_review_count(self):
    #     for rec in self:
    #         rec.review_count = self.env['kpi.review'].search_count([('person_id', '=', rec.id)])
    @api.depends('employee_id', 'year')
    def _compute_review_count(self):
        for rec in self:
            reviews = self.env['kpi.review'].search([
                ('person_id.employee_id', '=', rec.employee_id.id),
                ('person_id.year', '=', rec.year)
            ])
            rec.review_count = len(reviews)

    def action_set_mid_year_review(self):
        today = date.today()
        current_year = today.year
        created_reviews = self.env['kpi.review']
        start_date = date(current_year, 6, 1)
        end_date = date(current_year, 6, 25)

        if not (start_date <= today <= end_date):
            raise UserError(_(
                "You can only create a Mid-Year Review between June 1 and June 25"
            ))

        for rec in self:
            exists = self.env['kpi.review'].search_count([
                ('person_id', '=', rec.id),
                ('review_state', '=', 'mid_year_review'),
                ('date_from', '>=', date(current_year, 1, 1)),
                ('date_to', '<=', date(current_year, 12, 31)),
            ])
            if exists:
                continue

            review = self.env['kpi.review'].create({
                'name': f'Mid-Year Review {current_year} - {rec.name}',
                'person_id': rec.id,
                'note': rec.employee_id.name,
                'review_state': 'mid_year_review',
                'date_from': date(current_year, 1, 1),
                'date_to': date(current_year, 6, 30),
            })

            for work in rec.kpi_ids:
                self.env['kpi.review.work'].create({
                    'name': work.kpi_indicator or '',
                    'description': work.performance_measure or '',
                    'weight': work.kpi2_weight or 0.0,
                    'score': work.kpi2_score_actual or 0.0,
                    'person_work_id': work.id,
                    'review_id': review.id,
                    'kpi2_plan_target': work.kpi2_plan_target or 0,
                    'kpi2_actual_result': work.kpi2_actual_result or 0,
                    'kpi2_rating': work.kpi2_rating or 0,
                    'kpi2_weight_score': work.kpi2_weight_score or 0.0,
                    'sequence': work.sequence or 0,
                })

            for comp in rec.kpi_competency_ids:
                self.env['kpi.review.competency'].create({
                    'name': comp.name or '',
                    'level': comp.kpi2_rating or 0,
                    'score': comp.kpi2_weight_score or 0.0,
                    'weight': comp.kpi_weight or 0.0,
                    'behavior_evaluation': comp.behavior_evaluation or '',
                    'person_competency_id': comp.id,
                    'review_id': review.id,
                })
            total_weight_kpi = sum(work.kpi2_weight for work in rec.kpi_ids)
            total_score_kpi = sum(work.kpi2_weight_score for work in rec.kpi_ids)
            total_weight_comp = sum(comp.kpi_weight for comp in rec.kpi_competency_ids)
            total_score_comp = sum(comp.kpi2_weight_score for comp in rec.kpi_competency_ids)

            review.write({
                'overall_weight_kpi': total_score_kpi,
                'total_weigh_kpi': total_weight_kpi,
                'overall_score_kpi': total_score_kpi,

                'overall_weight_competency': total_score_comp,
                'total_weight_competency': total_weight_comp,
                'overall_score_competency': total_score_comp,

                'total_overall_weight': total_score_kpi + total_score_comp,
                'total_weight_kpi_competenct': total_weight_kpi + total_weight_comp,
                'total_overall_score': total_score_kpi + total_score_comp,

                'last_rating': 5 if (total_score_kpi + total_score_comp) >= 4.5 else
                4 if (total_score_kpi + total_score_comp) >= 3.5 else
                3 if (total_score_kpi + total_score_comp) >= 2.5 else
                2 if (total_score_kpi + total_score_comp) >= 1.5 else 1,
                'kpi4_more_info': True,
            })

            rec.write({'review_state': 'mid_year_review'})
            created_reviews |= review

            if not created_reviews:
                raise UserError(_("Mid-Year review was created already for this year"))

        line_manager = False
        try:
            line_manager = self.req_id.line_manager_id
        except:
            line_manager = False

        if not line_manager or line_manager != self.env.user:
            raise UserError("Sorry. You are not authorized to approve this document!")

        self.write({'state': 'emp_approve'})

        if len(created_reviews) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'kpi.review',
                'res_id': created_reviews.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'kpi.review',
                'view_mode': 'list,form',
                'domain': [('id', 'in', created_reviews.ids)],
            }

    def action_set_final_year_review(self):
        today = date.today()
        current_year = today.year
        created_reviews = self.env['kpi.review']
        start_date = date(current_year, 12, 1)
        end_date = date(current_year, 12, 25)

        if not (start_date <= today <= end_date):
            raise UserError(_(
                "You can only create a Final-Year Review between December 1 and December 25"
            ))

        for rec in self:
            exists = self.env['kpi.review'].search_count([
                ('person_id', '=', rec.id),
                ('review_state', '=', 'final_year_review'),
                ('date_from', '>=', date(current_year, 1, 1)),
                ('date_to', '<=', date(current_year, 12, 31)),
            ])
            if exists:
                continue

            review = self.env['kpi.review'].create({
                'name': f'Final-Year Review {current_year} - {rec.name}',
                'note': rec.employee_id,
                'person_id': rec.id,
                'review_state': 'final_year_review',
                'date_from': date(current_year, 1, 1),
                'date_to': date(current_year, 12, 31),
            })

            for work in rec.kpi_ids:
                self.env['kpi.review.work'].create({
                    'name': work.kpi_indicator or '',
                    'description': work.performance_measure or '',
                    'weight': work.kpi2_weight or 0.0,
                    'score': work.kpi2_score_actual or 0.0,
                    'person_work_id': work.id,
                    'review_id': review.id,
                    'kpi2_plan_target': work.kpi2_plan_target or 0,
                    'kpi2_actual_result': work.kpi2_actual_result or 0,
                    'kpi2_rating': work.kpi2_rating or 0,
                    'kpi2_weight_score': work.kpi2_weight_score or 0.0,
                    'sequence': work.sequence or 0,
                })

            for comp in rec.kpi_competency_ids:
                self.env['kpi.review.competency'].create({
                    'name': comp.name or '',
                    'level': comp.kpi2_rating or 0,
                    'score': comp.kpi2_weight_score or 0.0,
                    'weight': comp.kpi_weight or 0.0,
                    'behavior_evaluation': comp.behavior_evaluation or '',
                    'person_competency_id': comp.id,
                    'review_id': review.id,
                })
            total_weight_kpi = sum(work.kpi2_weight for work in rec.kpi_ids)
            total_score_kpi = sum(work.kpi2_weight_score for work in rec.kpi_ids)
            total_weight_comp = sum(comp.kpi_weight for comp in rec.kpi_competency_ids)
            total_score_comp = sum(comp.kpi2_weight_score for comp in rec.kpi_competency_ids)

            review.write({
                'overall_weight_kpi': total_score_kpi,
                'total_weigh_kpi': total_weight_kpi,
                'overall_score_kpi': total_score_kpi,

                'overall_weight_competency': total_score_comp,
                'total_weight_competency': total_weight_comp,
                'overall_score_competency': total_score_comp,

                'total_overall_weight': total_score_kpi + total_score_comp,
                'total_weight_kpi_competenct': total_weight_kpi + total_weight_comp,
                'total_overall_score': total_score_kpi + total_score_comp,

                'last_rating': 5 if (total_score_kpi + total_score_comp) >= 4.5 else
                4 if (total_score_kpi + total_score_comp) >= 3.5 else
                3 if (total_score_kpi + total_score_comp) >= 2.5 else
                2 if (total_score_kpi + total_score_comp) >= 1.5 else 1,
                'kpi4_more_info': True,
            })

            rec.write({'review_state': 'final_year_review'})
            created_reviews |= review

            if not created_reviews:
                raise UserError(_("Final-Year review was created already for this year"))
        line_manager = False
        try:
            line_manager = self.req_id.line_manager_id
        except:
            line_manager = False

        if not line_manager or line_manager != self.env.user:
            raise UserError("Sorry. You are not authorized to approve this document!")

        if len(created_reviews) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'kpi.review',
                'res_id': created_reviews.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'kpi.review',
                'view_mode': 'list,form',
                'domain': [('id', 'in', created_reviews.ids)],
            }



    def action_open_reviews(self):
        self.ensure_one()
        return {
            'name': 'Reviews',
            'type': 'ir.actions.act_window',
            'res_model': 'kpi.review',
            'view_mode': 'list,form',
            'domain': [
                ('person_id.employee_id', '=', self.employee_id.id),
                ('person_id.year', '=', self.year)
            ],
            'context': {'default_employee_id': self.employee_id.id, 'default_year': self.year},
        }


    def action_print_kpi(self):
        self.ensure_one()
        # if self.state != 'approved':
        #     raise UserError("You can only print KPI when approved.")
        return self.env.ref('kpi.action_report_kpi').report_action(self)




class KpiWorks(models.Model):
    _name = 'kpi.works'


    request_id = fields.Many2one("kpi.person", string="Employee")
    kpi_indicator = fields.Text(string="KEY PERFORMANCE INDICATOR (Minimum 5 )")
    performance_measure = fields.Text(string="PERFORMANCE MEASUREMENT ")
    kpi2_weight = fields.Integer(string="WEIGHT (%)")
    kpi2_plan_target = fields.Integer(string="PLANNED TARGET")
    kpi2_actual_result = fields.Integer(string="ACTUAL RESULTS")
    kpi2_score_actual = fields.Integer(string="SCORE")
    kpi2_rating = fields.Integer(string="RATING", readonly=0)
    kpi2_weight_score = fields.Float(string="WEIGHTED SCORE", compute='_compute_kpi2')
    sequence = fields.Integer(string="NO",compute = '_compute_step_number')



    @api.depends('request_id.kpi_ids')
    def _compute_step_number(self):
        for index, record in enumerate(self, start=1):
            record.sequence = str(index)

    @api.onchange('kpi2_actual_result', 'kpi2_plan_target', 'kpi2_weight', 'kpi2_score_actual', 'kpi2_rating')
    def _compute_kpi2(self):
        for rec in self:
            if rec.kpi2_actual_result or rec.kpi2_plan_target or rec.kpi2_weight:
                if rec.kpi2_plan_target > 0 and rec.kpi2_actual_result:
                    rec.kpi2_score_actual = round(rec.kpi2_actual_result / rec.kpi2_plan_target * 100)
                if rec.kpi2_plan_target:
                    if rec.kpi2_score_actual:
                        if rec.kpi2_score_actual < 70:
                            rec.kpi2_rating = 1
                        elif rec.kpi2_score_actual >= 70 and rec.kpi2_score_actual <= 90:
                            rec.kpi2_rating = 2
                        elif rec.kpi2_score_actual >= 91 and rec.kpi2_score_actual <= 110:
                            rec.kpi2_rating = 3
                        elif rec.kpi2_score_actual >= 111 and rec.kpi2_score_actual <= 120:
                            rec.kpi2_rating = 4
                        elif rec.kpi2_score_actual >= 121:
                            rec.kpi2_rating = 5
                rec.kpi2_weight_score = (rec.kpi2_weight * rec.kpi2_rating) / 100
            else:
                rec.kpi2_score_actual = 0
                rec.kpi2_weight_score = 0
                rec.kpi2_rating = 0

    @api.constrains('kpi2_rating')
    def constraint_field_kpi(self):
        for rec in self:
            if rec.kpi2_rating:
                if rec.kpi2_rating > 5 or rec.kpi2_rating <= 0:
                    raise UserError("The Rating Must be from [0-5]")


class KpiCompetency(models.Model):
    _name = 'kpi.competency'

    request_id = fields.Many2one("kpi.person", string="Employee")
    name = fields.Text(string="COMPETENCIES")
    behavior_evaluation = fields.Text(string="BEHAVIORAL EVIDENCES (STAR) (S=Situation, T=Task, A=Action, R=Result)")
    kpi_weight = fields.Integer(string="WEIGHT (%)")
    kpi2_rating = fields.Integer(string="RATING")
    kpi2_weight_score = fields.Float(string="WEIGHTED SCORE", compute='_compute_kpi3')

    @api.onchange('kpi_weight', 'kpi2_rating')
    def _compute_kpi3(self):
        for rec in self:
            if rec.kpi_weight > 0 and rec.kpi2_rating > 0:
                rec.kpi2_weight_score = (rec.kpi_weight * rec.kpi2_rating) / 100
            else:
                rec.kpi2_weight_score = 0

    @api.constrains('kpi2_rating')
    def constraint_competency(self):
        for rec in self:
            if rec.kpi2_rating:
                if rec.kpi2_rating > 5 or rec.kpi2_rating <= 0:
                    raise UserError("The Rating Must be from [0-5]")


class KpiReview(models.Model):
    _name = 'kpi.review'
    _description = 'Performance Review'

    name = fields.Char(string="Review Name")
    person_id = fields.Many2one('kpi.person', string="Person", ondelete='cascade')
    review_state = fields.Selection([
        ('mid_year_review', 'Mid-Year Review'),
        ('final_year_review', 'Final-Year Review')
    ], string="Review Type")
    date_from = fields.Date()
    date_to = fields.Date()
    note = fields.Text()
    work_ids = fields.One2many('kpi.review.work', 'review_id', string="Work Items")
    competency_ids = fields.One2many('kpi.review.competency', 'review_id', string="Competencies")
    # PART IV + V Overall Rating fields
    overall_weight_kpi = fields.Float(string="Actual Weighted Score KPI")
    total_weigh_kpi = fields.Float(string="Weight KPI")
    overall_score_kpi = fields.Float(string="Individual Weighted Score KPI")

    overall_weight_competency = fields.Float(string="Actual Weighted Score Competency")
    total_weight_competency = fields.Float(string="Weight Competency")
    overall_score_competency = fields.Float(string="Individual Weighted Score Competency")

    total_overall_weight = fields.Float(string="Total Actual Weighted Score")
    total_weight_kpi_competenct = fields.Float(string="Total Weight KPI + Competency")
    total_overall_score = fields.Float(string="Total Individual Weighted Score")

    last_rating = fields.Integer(string="Rating")
    kpi4_more_info = fields.Boolean(string="Show Rating Table")


class KpiReviewCompetency(models.Model):
    _name = 'kpi.review.competency'
    _description = 'Review Competency'

    name = fields.Char(string="COMPETENCIES")
    level = fields.Integer(string="RATING")
    score = fields.Float(string="WEIGHTED SCORE")
    weight = fields.Integer(string="WEIGHT (%)")
    person_competency_id = fields.Many2one('kpi.competency', string="Original Competency")
    review_id = fields.Many2one('kpi.review', string="Review", ondelete='cascade')
    behavior_evaluation = fields.Text(string="BEHAVIORAL EVIDENCES (STAR) (S=Situation, T=Task, A=Action, R=Result)")



class KpiReviewWork(models.Model):
    _name = 'kpi.review.work'
    _description = 'Review Work Item'

    name = fields.Char(string="KEY PERFORMANCE INDICATOR (Minimum 5 )")
    description = fields.Text(string="PERFORMANCE MEASUREMENT ")
    weight = fields.Float(string="WEIGHT (%)")
    score = fields.Float(string="Score")
    person_work_id = fields.Many2one('kpi.works', string="Original Work")
    review_id = fields.Many2one('kpi.review', string="Review", ondelete='cascade')
    kpi2_plan_target = fields.Integer(string="PLANNED TARGET")
    kpi2_actual_result = fields.Integer(string="ACTUAL RESULTS")
    kpi2_rating = fields.Integer(string="RATING", readonly=0)
    kpi2_weight_score = fields.Float(string="WEIGHTED SCORE", compute='_compute_weight_score', store=True)
    sequence = fields.Integer(string="NO")

    @api.depends('weight', 'kpi2_rating')
    def _compute_weight_score(self):
        for rec in self:
            if rec.weight and rec.kpi2_rating:
                rec.kpi2_weight_score = (rec.weight * rec.kpi2_rating) / 100
            else:
                rec.kpi2_weight_score = 0



class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    kpi_count = fields.Integer(string="Count", compute='compute_kpi_count')

    def compute_kpi_count(self):
        self.kpi_count = self.env['kpi.person'].search_count(
            [('employee_id.id', '=', self.id), ('state', '=', 'approved')])

    def set_employee_kpi(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Employee KPI',
            'view_mode': 'list,form',
            'res_model': 'kpi.person',
            'domain': [('employee_id.id', '=', self.id), ('state', '=', 'approved')],
            'context': "{'create': False}"
        }
