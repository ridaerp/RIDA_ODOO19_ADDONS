# -*- coding: utf-8 -*-
# from odoo import http


# class HrPayrollWorkflow(http.Controller):
#     @http.route('/hr_payroll_workflow/hr_payroll_workflow/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_payroll_workflow/hr_payroll_workflow/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_payroll_workflow.listing', {
#             'root': '/hr_payroll_workflow/hr_payroll_workflow',
#             'objects': http.request.env['hr_payroll_workflow.hr_payroll_workflow'].search([]),
#         })

#     @http.route('/hr_payroll_workflow/hr_payroll_workflow/objects/<model("hr_payroll_workflow.hr_payroll_workflow"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_payroll_workflow.object', {
#             'object': obj
#         })
