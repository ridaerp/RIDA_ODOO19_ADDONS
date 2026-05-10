# -*- coding: utf-8 -*-
# from odoo import http


# class MaterialRequest(http.Controller):
#     @http.route('/material_request/material_request/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/material_request/material_request/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('material_request.listing', {
#             'root': '/material_request/material_request',
#             'objects': http.request.env['material_request.material_request'].search([]),
#         })

#     @http.route('/material_request/material_request/objects/<model("material_request.material_request"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('material_request.object', {
#             'object': obj
#         })
