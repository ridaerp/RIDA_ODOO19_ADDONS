# -*- coding: utf-8 -*-
# from odoo import http


# class OmaxErp(http.Controller):
#     @http.route('/omax_erp/omax_erp/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/omax_erp/omax_erp/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('omax_erp.listing', {
#             'root': '/omax_erp/omax_erp',
#             'objects': http.request.env['omax_erp.omax_erp'].search([]),
#         })

#     @http.route('/omax_erp/omax_erp/objects/<model("omax_erp.omax_erp"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('omax_erp.object', {
#             'object': obj
#         })
