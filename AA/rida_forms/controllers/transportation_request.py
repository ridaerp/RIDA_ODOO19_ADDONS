# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from collections import OrderedDict, namedtuple
import datetime
from odoo import http, fields
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.tools.translate import _
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal
from odoo.addons.web.controllers.main import Binary
from odoo.tools import float_compare
from pytz import timezone, UTC
import datetime
from datetime import datetime as dt
from odoo.exceptions import UserError, ValidationError
from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY
import json
import math
import dateutil
from dateutil.relativedelta import relativedelta

DummyAttendance = namedtuple('DummyAttendance', 'hour_from, hour_to, dayofweek, day_period')

class CustomerPortal(CustomerPortal):
    REQUEST_MANDATORY_BILLING_FIELDS = ["date_request", "destination_from", "destination_to","reason","expected_departure"]
    REQUEST_OPTIONAL_BILLING_FIELDS = ["name_seq","other_requirements","department_id","requested_by","job_id","purpose"]


    def request_details_form_validate(self, data):
        error = dict()
        error_message = []

        # Validation
        for field_name in self.REQUEST_MANDATORY_BILLING_FIELDS:
            if not data.get(field_name):
                error[field_name] = 'missing'

        # error message for empty required fields
        if [err for err in error.values() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))

        unknown = [k for k in data if k not in self.REQUEST_MANDATORY_BILLING_FIELDS + self.REQUEST_OPTIONAL_BILLING_FIELDS]
        if unknown:
            error['common'] = 'Unknown field'
            error_message.append("Unknown field '%s'" % ','.join(unknown))

        return error, error_message



    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        employee_id = False
        if request.env.user.employee_ids:
            employee_id = request.env.user.employee_ids[0]

            values['request_count'] = request.env['transportation.request'].search_count([
                ('employee_id', '=', employee_id.id)
            ])
            values['employee_id'] = employee_id
        return values







    def _transport_request_get_page_view_values(self, transport_request, access_token, **kwargs):
        values = {
            'transport_request': transport_request,
        }
        return self._get_page_view_values(transport_request, access_token, values, 'my_transport_request_history', True, **kwargs)

    @http.route(['/my/transport_request', '/my/transport_request/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_transport_requests(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        employee_id = False
        if request.env.user.employee_ids:
            employee_id = request.env.user.employee_ids[0]
        else:
            return request.redirect('/my')
        # leave_types = request.env['hr.leave.type'].with_context(employee_id=employee_id.id).search([('valid', '=', True)])
        TransportRequest = request.env['transportation.request']

        domain = []

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name_seq': {'label': _('Name'), 'order': 'name_seq asc, id asc'},
        }


        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']


        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('employee_id', '=', employee_id.id)]},
            # 'approve': {'label': _('Approved'), 'domain': [('employee_id', '=', employee_id.id), ('state', '=', 'validate')]},
            # 'refuse': {'label': _('Refused'), 'domain': [('employee_id', '=', employee_id.id), ('state', '=', 'refuse')]},
        }
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # count for pager
        request_count = TransportRequest.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/transport_request",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=request_count,
            page=page,
            step=self._items_per_page
        )
        # search the records to display, according to the pager data
        transport_requests = TransportRequest.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session['my_transport_request_history'] = transport_requests.ids[:100]



        # purpose_values = ['internal_business_task','business_trip','regular_transportation']
        # types = []

        # types.append(purpose_values)

        values.update({
            'date': date_begin,
            'transport_requests': transport_requests,
            'page_name': 'transport_request',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            # 'purpose':types,
            'employee_id': employee_id,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': '/my/transport_request',
        })

        return request.render("rida_forms.portal_my_transport_requests", values)

    @http.route(['/my/transport_request/<int:transportaion_request_id>'], type='http', auth="public", website=True)
    def portal_my_transport_request(self, transportaion_request_id=None, access_token=None, **kw):
        try:
            request_sudo = self._document_check_access('transportation.request', transportaion_request_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._transport_request_get_page_view_values(request_sudo, access_token, **kw)
        return request.render("rida_forms.portal_my_transport_request", values)

    def _check_purpose(self, purpose, date_request, expected_departure):
        error = False


        if expected_departure and purpose=='business_trip':
            d = dateutil.parser.parse(expected_departure).date()
            checked_day = (datetime.datetime.strptime(date_request, '%Y-%m-%d') + datetime.timedelta(days=3) ).strftime('%Y-%m-%d')
            if str(expected_departure)< checked_day:
                print ("@@@@@@@@@@@@@@@",expected_departure,checked_day)
                error = ('The date of departure must be  three days after date of request')
        return error

    @http.route(['/my/transport_request/edit'], type='http', auth="public", website=True)
    def update_transport_request(self, redirect=None, **post):
        attachment = False

        transportaion_request_id = False
        if post.get('id'):
            transportaion_request_id = int(post.get('id'))
        values = self._prepare_portal_layout_values()
        employee_id = False
        if request.env.user.employee_ids:
            employee_id = request.env.user.employee_ids[0]

        values.update({
            'error': {},
            'error_message': [],
        })


        TransportRequest = request.env['transportation.request']


        transport_request = False
        if transportaion_request_id:
            transport_request = request.env['transportation.request'].browse(transportaion_request_id)
        attachment = post.get('attachment', False)
        post.pop('attachment', None)
        post.pop('id', None)

        if post:
            error, error_message = self.request_details_form_validate(post)
            values.update({'error': error, 'error_message': error_message})
            values.update(post)




            if error:
                values.update({
                    'employee_id': employee_id,
                    'transport_request': transport_request,
                    'redirect': redirect,
                    'page_name': 'transport_request',
                    'error_message': error_message,
                    'request_name': '/',
                })

                response = request.render("rida_forms.edit_transport_request_details", values)
                response.headers['X-Frame-Options'] = 'DENY'
                return response

            values = {key: post[key] for key in self.REQUEST_MANDATORY_BILLING_FIELDS}
            values.update({key: post[key] for key in self.REQUEST_OPTIONAL_BILLING_FIELDS if key in post})


            values.update(
                {
                    'employee_id': employee_id.id,
                })

            err = self._check_purpose(values.get('purpose'), values.get('date_request'),values.get('expected_departure'))
            
            if err:
                error_message.append(err)


            if error_message:
                values.update({
                    'employee_id': employee_id,
                    'transport_request': transport_request,
                    'redirect': redirect,
                    'page_name': 'transport_request',
                    'error_message': error_message,
                    'transport_request_name': '/',
                })
                response = request.render("rida_forms.edit_transport_request_details", values)
                response.headers['X-Frame-Options'] = 'DENY'
                return response


            if not transportaion_request_id:
                transport_request = TransportRequest.create(values)


                transport_request.sudo().write({'state':'line_approve'})

            else:
                transport_request.update(values)

            if redirect:
                return request.redirect(redirect)
            return request.redirect('/my/transport_request')

        values.update({
            'employee_id': employee_id,
            'transport_request': transport_request,
            'redirect': redirect,
            'page_name': 'transport_request',
            'transport_request_name': '/',
        })
        print ("###################",values)
        response = request.render("rida_forms.edit_transport_request_details", values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response



