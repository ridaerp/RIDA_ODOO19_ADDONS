# -*- coding: utf-8 -*-
# from odoo import http


# class MaintenanceInherit(http.Controller):
#     @http.route('/maintenance_inherit/maintenance_inherit/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/maintenance_inherit/maintenance_inherit/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('maintenance_inherit.listing', {
#             'root': '/maintenance_inherit/maintenance_inherit',
#             'objects': http.request.env['maintenance_inherit.maintenance_inherit'].search([]),
#         })

#     @http.route('/maintenance_inherit/maintenance_inherit/objects/<model("maintenance_inherit.maintenance_inherit"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('maintenance_inherit.object', {
#             'object': obj
#         })
