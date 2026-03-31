# -*- coding: utf-8 -*-
# from odoo import http


# class BaseRida(http.Controller):
#     @http.route('/base_rida/base_rida/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/base_rida/base_rida/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('base_rida.listing', {
#             'root': '/base_rida/base_rida',
#             'objects': http.request.env['base_rida.base_rida'].search([]),
#         })

#     @http.route('/base_rida/base_rida/objects/<model("base_rida.base_rida"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('base_rida.object', {
#             'object': obj
#         })
