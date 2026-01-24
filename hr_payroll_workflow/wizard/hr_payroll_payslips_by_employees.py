# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import datetime, date, time
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PayslipEmployeeRun(models.TransientModel):
    _inherit = 'hr.payslip.employees'
    
    
    currency_id = fields.Many2one("res.currency",compute='get_currency_id',store=True)

    def get_currency_id(self):
        active_id = self._context.get('active_id')
        currency = self.env['hr.payslip.run'].search([('id','=',active_id)]).currency_id
        self.currency_id = currency.id


    def _get_available_contracts_domain(self):
        active_id = self._context.get('active_id')
        currency = self.env['hr.payslip.run'].search([('id','=',active_id)]).currency_id
        structure = self.env['hr.payslip.run'].browse(self._context.get('active_id')).structure_id.type_id

        # employees = self.with_context(active_test=False).employee_ids
        # payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))


        # contracts = employees._get_contracts(
        #     payslip_run.date_start, payslip_run.date_end, states=['open', 'close']
        # ).filtered(lambda c: c.active)


        return [('contract_ids.state', 'in', ('open', 'close')),
                ('company_id', '=', self.env.company.id)
            ,('contract_id.salary_currency', '=', currency.id)
                 # ,('contract_ids.structure_type_id.id', '=', structure.id)
                 # ,('contract_ids.structure_type_id.id', '=', contracts.structure_type_id.id)
                ]
        # res = super(PayslipEmployeeRun,self)._get_available_contracts_domain()
        # return res





    def compute_sheet(self):
        self.ensure_one()
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
            end_date = fields.Date.to_date(self.env.context.get('default_date_end'))
            payslip_run = self.env['hr.payslip.run'].create({
                'name': from_date.strftime('%B %Y'),
                'date_start': from_date,
                'date_end': end_date,
            })
        else:
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

        employees = self.with_context(active_test=False).employee_ids
        for emp in self.employees:
            if emp.is_susupend:
                self.write({'employees': [(3, emp.id)]})
        if not employees:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        payslips = self.env['hr.payslip']
        Payslip = self.env['hr.payslip']

        contracts = employees._get_contracts(
            payslip_run.date_start, payslip_run.date_end, states=['open', 'close']
        ).filtered(lambda c: c.active)
        contracts._generate_work_entries(payslip_run.date_start, payslip_run.date_end)
        work_entries = self.env['hr.work.entry'].search([
            ('date_start', '<=', payslip_run.date_end),
            ('date_stop', '>=', payslip_run.date_start),
            ('employee_id', 'in', employees.ids),
        ])
        self._check_undefined_slots(work_entries, payslip_run)

        if(self.structure_id.type_id.default_struct_id == self.structure_id):
            work_entries = work_entries.filtered(lambda work_entry: work_entry.state != 'validated')
            if work_entries._check_if_error():
                work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])

                for work_entry in work_entries.filtered(lambda w: w.state == 'conflict'):
                    work_entries_by_contract[work_entry.contract_id] |= work_entry

                for contract, work_entries in work_entries_by_contract.items():
                    conflicts = work_entries._to_intervals()
                    time_intervals_str = "\n - ".join(['', *["%s -> %s" % (s[0], s[1]) for s in conflicts._items]])
                
                return False
                # return {
                #     'type': 'ir.actions.client',
                #     'tag': 'display_notification',
                #     'params': {
                #         'title': _('Some work entries could not be validated.'),
                #         'message': _('Time intervals to look for:%s', time_intervals_str),
                #         'sticky': False,
                #     }
                # }


        default_values = Payslip.default_get(Payslip.fields_get())
        payslip_values = [dict(default_values, **{
            'name': 'Payslip - %s' % (contract.employee_id.name),
            'employee_id': contract.employee_id.id,
            'credit_note': payslip_run.credit_note,
            'payslip_run_id': payslip_run.id,
            'date_from': payslip_run.date_start,
            'date_to': payslip_run.date_end,
            'contract_id': contract.id,
            'struct_id': self.structure_id.id or contract.structure_type_id.default_struct_id.id,
        }) for contract in contracts]

        payslips = Payslip.with_context(tracking_disable=True).create(payslip_values)
        for payslip in payslips:
            payslip._onchange_employee()

        payslips.compute_sheet()
        payslip_run.state = 'verify'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run',
            'views': [[False, 'form']],
            'res_id': payslip_run.id,
        }



    def compute_sheet(self):
        """ Get Employees with their contract currency is the same as selected in the payslip batch"""
        self.ensure_one()
        res = super(PayslipEmployeeRun, self).compute_sheet()
        active_id = self._context.get('active_id')
        date_from = self.env['hr.payslip.run'].search([('id','=',active_id)]).date_start
        date_to = self.env['hr.payslip.run'].search([('id','=',active_id)]).date_end
        currency = self.env['hr.payslip.run'].search([('id','=',active_id)]).currency_id
        structure = self.env['hr.payslip.run'].search([('id','=',active_id)]).structure_id
        # slp_start = datetime.datetime.strftime(date_from, '%Y-%m-%d')
        # slp_end = datetime.datetime.strftime(date_to, '%Y-%m-%d')
        total_amount = 0.00
        contracts = self.env['hr.contract'].search([('salary_currency','=',currency.id) ,('structure_type_id', '=', structure.id)])
        selected_emps = []
        for con in contracts:
            selected_emps.append(con.employee_id.id)
        for emp in self.employee_ids:
            if emp.id not in selected_emps:	
                self.write({'employee_ids':[(3, emp.id)]})


        payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))
        for run in payslip_run:
            run.write({'state':'draft'})

        for run in payslip_run.slip_ids:
            run.compute_sheet()
            for line in run.line_ids:
               if line.salary_rule_id.apper_on_journal:
                  line.partner_id=run.employee_id.address_home_id

        # raise UserError(res[0])
        return res



    def _check_undefined_slots(self, work_entries, payslip_run):
        """
        Check if a time slot in the contract's calendar is not covered by a work entry
        """
        work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])
        for work_entry in work_entries:
            work_entries_by_contract[work_entry.contract_id] |= work_entry

        for contract, work_entries in work_entries_by_contract.items():
            calendar_start = pytz.utc.localize(datetime.combine(max(contract.date_start, payslip_run.date_start), time.min))
            calendar_end = pytz.utc.localize(datetime.combine(min(contract.date_end or date.max, payslip_run.date_end), time.max))
            outside = contract.resource_calendar_id._attendance_intervals_batch(calendar_start, calendar_end)[False] - work_entries._to_intervals()
            # if outside:
            #     time_intervals_str = "\n - ".join(['', *["%s -> %s" % (s[0], s[1]) for s in outside._items]])
            #     raise UserError(_("Some part of %s's calendar is not covered by any work entry. Please complete the schedule. Time intervals to look for:%s") % (contract.employee_id.name, time_intervals_str))

