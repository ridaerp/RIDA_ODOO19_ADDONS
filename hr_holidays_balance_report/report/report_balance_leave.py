# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Gee Paul Joby (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import fields, models, tools


class ReportBalanceLeave(models.Model):
    """Balance Leave Report model"""

    _name = 'report.balance.leave'
    _description = 'Leave Balance Report'
    _auto = False

    emp_id = fields.Many2one(
        'hr.employee', string="Employee", readonly=True, help="Employee name"
    )
    gender = fields.Char(string='Gender', readonly=True, help="Employee gender")
    department_id = fields.Many2one(
        'hr.department', string='Department', readonly=True, help="Department Name"
    )
    country_id = fields.Many2one(
        'res.country', string='Country', readonly=True, help="Employee country"
    )
    job_id = fields.Many2one(
        'hr.job', string='Job', readonly=True, help="Job of employee"
    )
    leave_type_id = fields.Many2one(
        'hr.leave.type', string='Leave Type', readonly=True,
        help="Leave type of employee"
    )
    allocated_days = fields.Float(
        string='Allocated Balance', help="Total validated leave assigned to the employee"
    )
    taken_days = fields.Float(
        string='Taken Leaves', help="Validated leaves taken by the employee"
    )
    balance_days = fields.Float(
        string='Remaining Balance', help="Remaining leaves of employee"
    )
    company_id = fields.Many2one(
        'res.company', string="Company", help="Company Name"
    )

    def init(self):
        """Load report data for Odoo 19.

        In Odoo 19 several HR fields (gender, department, job, etc.) are stored on
        hr.version instead of directly on hr.employee. The report therefore joins
        the employee current version and aggregates validated allocations/leaves in
        separate CTEs to avoid duplicated totals.
        """
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH allocations AS (
                    SELECT
                        al.employee_id,
                        al.holiday_status_id AS leave_type_id,
                        SUM(al.number_of_days) AS allocated_days
                    FROM hr_leave_allocation al
                    WHERE al.state = 'validate'
                      AND al.employee_id IS NOT NULL
                    GROUP BY al.employee_id, al.holiday_status_id
                ),
                taken AS (
                    SELECT
                        l.employee_id,
                        l.holiday_status_id AS leave_type_id,
                        SUM(l.number_of_days) AS taken_days
                    FROM hr_leave l
                    WHERE l.state = 'validate'
                      AND l.employee_id IS NOT NULL
                    GROUP BY l.employee_id, l.holiday_status_id
                ),
                leave_types AS (
                    SELECT employee_id, leave_type_id FROM allocations
                    UNION
                    SELECT employee_id, leave_type_id FROM taken
                )
                SELECT
                    ROW_NUMBER() OVER (ORDER BY e.id, lt.leave_type_id) AS id,
                    e.id AS emp_id,
                    v.sex AS gender,
                    v.private_country_id AS country_id,
                    v.department_id AS department_id,
                    v.job_id AS job_id,
                    lt.leave_type_id AS leave_type_id,
                    COALESCE(a.allocated_days, 0.0) AS allocated_days,
                    COALESCE(t.taken_days, 0.0) AS taken_days,
                    COALESCE(a.allocated_days, 0.0) - COALESCE(t.taken_days, 0.0)
                        AS balance_days,
                    e.company_id AS company_id
                FROM hr_employee e
                JOIN hr_version v
                    ON v.id = e.current_version_id
                JOIN leave_types lt
                    ON lt.employee_id = e.id
                LEFT JOIN allocations a
                    ON a.employee_id = e.id
                   AND a.leave_type_id = lt.leave_type_id
                LEFT JOIN taken t
                    ON t.employee_id = e.id
                   AND t.leave_type_id = lt.leave_type_id
                WHERE e.active = TRUE
            )
        """)
