# -*- coding: utf-8 -*-
from odoo import http

# class ModuleTemp(http.Controller):
#     @http.route('/module_temp/module_temp/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/module_temp/module_temp/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('module_temp.listing', {
#             'root': '/module_temp/module_temp',
#             'objects': http.request.env['module_temp.module_temp'].search([]),
#         })

#     @http.route('/module_temp/module_temp/objects/<model("module_temp.module_temp"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('module_temp.object', {
#             'object': obj
#         })