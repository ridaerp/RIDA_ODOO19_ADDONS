from odoo import models, fields, tools


class LeaveBalanceReport(models.Model):
    """Balance Leave Report model"""

    _name = 'report.balance.leave'
    _description = 'Leave Balance Report'
    _auto = False

    emp_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    gender = fields.Char(string='gender', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    country_id = fields.Many2one('res.country', string='Nationality', readonly=True)
    job_id = fields.Many2one('hr.job', string='Job', readonly=True)
    leave_type_id = fields.Many2one('hr.leave.type', string='Leave Type', readonly=True)
    allocated_days = fields.Integer('Allocated Balance')
    taken_days = fields.Integer('Taken Leaves')
    balance_days = fields.Integer('Remaining Balance')
    company_id = fields.Many2one('res.company', string="Company")

    def init(self):
        """Loads report data"""
        tools.drop_view_if_exists(self._cr, 'report_balance_leave')
        self._cr.execute("""
         CREATE OR REPLACE VIEW report_balance_leave AS (
    SELECT 
        row_number() OVER(ORDER BY e.id) AS id,
        e.id AS emp_id,
        e.gender AS gender,
        e.country_id AS country_id,
        e.department_id AS department_id,
        e.job_id AS job_id,
        lt.id AS leave_type_id,
        (SELECT COALESCE(SUM(a.number_of_days), 0) 
         FROM hr_leave_allocation a 
         WHERE a.employee_id = e.id 
         AND a.holiday_status_id = lt.id 
         AND a.state = 'validate') AS allocated_days,
        SUM(CASE WHEN l.state = 'validate' THEN l.number_of_days ELSE 0 END) AS taken_days,
        (SELECT COALESCE(SUM(a.number_of_days), 0) 
         FROM hr_leave_allocation a 
         WHERE a.employee_id = e.id 
         AND a.holiday_status_id = lt.id 
         AND a.state = 'validate') - 
        SUM(CASE WHEN l.state = 'validate' THEN l.number_of_days ELSE 0 END) AS balance_days,
        e.company_id AS company_id
    FROM hr_employee e
    JOIN hr_leave_type lt 
        ON EXISTS (SELECT 1 FROM hr_leave_allocation a 
                   WHERE a.holiday_status_id = lt.id 
                   AND a.employee_id = e.id 
                   AND a.state = 'validate')  -- ✅ Ensures only allocated leave types
    LEFT JOIN hr_leave l 
        ON l.employee_id = e.id 
        AND l.holiday_status_id = lt.id
        AND l.state = 'validate'
    WHERE e.active = TRUE
    GROUP BY e.id, lt.id
);
""")
