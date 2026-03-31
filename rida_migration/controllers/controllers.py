# -*- coding: utf-8 -*-
# from odoo import http


# class RidaMigration(http.Controller):
#     @http.route('/rida_migration/rida_migration', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/rida_migration/rida_migration/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('rida_migration.listing', {
#             'root': '/rida_migration/rida_migration',
#             'objects': http.request.env['rida_migration.rida_migration'].search([]),
#         })

#     @http.route('/rida_migration/rida_migration/objects/<model("rida_migration.rida_migration"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('rida_migration.object', {
#             'object': obj
#         })

