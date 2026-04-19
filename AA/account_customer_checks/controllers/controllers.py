# -*- coding: utf-8 -*-
from odoo import http

# class TempModule(http.Controller):
#     @http.route('/temp_module/temp_module/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/temp_module/temp_module/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('temp_module.listing', {
#             'root': '/temp_module/temp_module',
#             'objects': http.request.env['temp_module.temp_module'].search([]),
#         })

#     @http.route('/temp_module/temp_module/objects/<model("temp_module.temp_module"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('temp_module.object', {
#             'object': obj
#         })