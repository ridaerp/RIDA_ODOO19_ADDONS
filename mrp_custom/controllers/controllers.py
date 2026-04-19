from odoo import http
from odoo.http import request

# class ChemicalSamplesController(http.Controller):

#     @http.route('/chemical_request/generate', type='json', auth='user')
#     def generate_samples(self, args):
#         request.env['chemical.samples.request'].browse(args[0]).button_generate()
#         return {'status': 'success'}

#     @http.route('/chemical_request/submit', type='json', auth='user')
#     def submit_samples(self, args):
#         request.env['chemical.samples.request'].browse(args[0]).button_submit()
#         return {'status': 'success'}


