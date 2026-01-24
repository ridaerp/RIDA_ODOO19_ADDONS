from odoo import fields , api , models , _
from datetime import datetime, time
from pytz import timezone, UTC
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import  UserError,AccessError


class hrLeaveType(models.Model):
    _inherit = 'hr.leave.type'


    expense_account_id = fields.Many2one('account.account', string='Expense Account')
    journal_id = fields.Many2one('account.journal', string='Journal')

    attachment_required = fields.Boolean(string='Required Attachment')
    exclude_weekend = fields.Boolean("Exclude Weekend")
    exclude_public = fields.Boolean("Exclude Public Holidays")
    leave_maximum  = fields.Boolean(string='Maximum')
    leave_maximum_number  = fields.Float(string='Maximum Number')
    year = fields.Char(string='Year')
    leave_type  = fields.Selection([
        ('annual', 'Annual Leave'),
        ('unpaid', 'Unpaid Leave'),
        ('sick', 'Sick Leave'),
        ('compassionate', 'Compassionate Leave'),
        ('maternaty', 'Maternaty Leave'),
        ('paternaty', 'Paternaty Leave'),
        ('emergancy', 'Emergancy Leave'),
        ('examination', 'Examination Leave'),
        ('haj', 'Haj Leave'),
        ('marriage', 'Marriage Leave'),
        ('comensatory', 'Comensatory Days'),
        ('permisssion', 'Permisssion'),
        ('other', 'Other'),
        ], string='Leave Type',required=True, )

class Employee(models.Model):
    _inherit = "hr.employee"
    current_leave_state = fields.Selection(compute='_compute_leave_status', string="Current Time Off Status",
        selection=[
            ('draft', 'New'),
            ('confirm', 'To Approve'),
            ('refuse', 'Refused'),
            ('validate1', 'HR Manager Approve'),
            ('line_manager', 'Line Manager'),
            ('hr_officer', ' HR officer'),
            ('ccso', 'COO'),
            ('validate', 'Approved'),
            ('cancel', 'Cancelled')
        ])
class hrLeave(models.Model):
    _inherit = 'hr.leave'

    attachment = fields.Binary(string='Attachment')
    cut_leave = fields.Boolean("Leave Cut",default=False,tracking=True)

    mercy_relation = fields.Selection([
        ('father', 'وفاة الوالد'),
        ('mother', 'وفاة الوالدة'),
        ('spouse', 'وفاة زوج/زوجة'),
        ('child', 'وفاة الأبناء'),
        ('grandfather', 'وفاة الجد'),
        ('grandmother', 'وفاة الجدة'),
        ('hospital', 'أحد الأقارب بالمستشفى'),
        ('natural', 'كوارث طبيعية'),
    ], string="سبب الاجازة")
    show_mercy_relation = fields.Boolean(compute='_compute_show_mercy_relation')

    @api.depends('holiday_status_id')
    def _compute_show_mercy_relation(self):
        for rec in self:
            rec.show_mercy_relation = rec.holiday_status_id.name == 'Compassionate'

    @api.onchange('mercy_relation', 'holiday_status_id', 'request_date_from')
    def _onchange_mercy_relation(self):
        for rec in self:
            if rec.holiday_status_id and rec.holiday_status_id.name == 'Compassionate':
                days = 0
                if rec.mercy_relation in ['father', 'mother', 'child', 'spouse']:
                    days = 5
                elif rec.mercy_relation in ['grandfather', 'grandmother']:
                    days = 3
                elif rec.mercy_relation in ['hospital', 'natural']:
                    days = 2

                rec.number_of_days_display = days
                if rec.request_date_from and days > 0:
                    rec.request_date_to = rec.request_date_from + timedelta(days=days - 1)


    def action_cut_leave(self):
        self.write({
            'state': 'draft',
            'cut_leave': True
        })


    def action_refuse(self):
      
        return {
            'type': 'ir.actions.act_window',
            'name': 'Justification',
            'view_mode':'form',
            'view_id':self.env.ref('hr_leave_main.wizard_justification_view_form').id,
            'target':'new',
            'res_model':'justification.justification',

        }
        # return True
  
      

    def return_wizard(self):
        # raise UserError(self.env.ref('hr_leave_main.justification_open_wizard').name)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Justification',
            'view_mode':'form',
            'view_id':self.env.ref('hr_leave_main.wizard_justification_view_form').id,
            'target':'new',
            'res_model':'justification.justification',

        }


    # cut_leave = fields.Boolean(string='Cut Leave',default=False,track_visibility='onchange')

    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'HR Manager Approve'),
        ('line_manager', 'Line Manager'),
        ('hr_officer', ' HR officer'),
        ('ccso', 'COO'),
        ('validate', 'Approved')
    ], string='Status', readonly=True, tracking=True, copy=False, default='draft',
        help="The status is set to 'To Submit', when a time off request is created." +
             "\nThe status is 'To Approve', when time off request is confirmed by user." +
             "\nThe status is 'Refused', when time off request is refused by manager." +
             "\nThe status is 'Approved', when time off request is approved by manager.")

    click = fields.Boolean(string='Check', default= False)



# onchange function for unpaid state
    @api.onchange('holiday_status_id')
    def _onchange_(self):
        for rec in self:
            if rec.holiday_status_id.leave_type == 'unpaid':
                leave_count = 0.0
                leave_days = self.env['hr.leave.report'].search([('employee_id','=',self.employee_id.id), ('leave_type','=',['allocatin','request'])])
                for leave in leave_days:
                    leave_count += leave.number_of_days
                    if leave_count == 0:
                        rec.click=True
                    else:
                        # raise UserError(_('Sorry!!! You can not request unpaid leave. You have ' +str(leave_count) +' days left in your balance.'))
                        raise UserError(_('Sorry!!! You can not request unpaid leave. You have days left in your balance.'))
            else:
                rec.click=False
            

    def _get_number_of_days(self, date_from , date_to, employee_id):

        if self.request_unit_half:
            # """ Returns a float equals to the timedelta between two dates given as string."""
            if employee_id:
                employee = self.env['hr.employee'].browse(employee_id)
                return employee._get_work_days_data(date_from, date_to)

            today_hours = self.env.company.resource_calendar_id.get_work_hours_count(
                datetime.combine(date_from.date(), time.min),
                datetime.combine(date_from.date(), time.max),
                False)
            hours = self.env.company.resource_calendar_id.get_work_hours_count(date_from, date_to)
            return {'days': hours / (today_hours), 'hours': hours}

        else:
            days = 0
            from_dt = fields.Datetime.from_string(date_from)
            to_dt = fields.Datetime.from_string(date_to)
            if from_dt and to_dt:
                time_delta = to_dt - from_dt
                days = time_delta.days + 1
            day_list = []
            while from_dt <= to_dt:
                day_list.append(from_dt.date())
                from_dt += timedelta(days=1)
            if self.holiday_status_id.exclude_weekend:
                for day in day_list:
                    if day.weekday() == 4 or day.weekday() == 5 :
                        days -= 1
            if self.holiday_status_id.exclude_public:
                for p_id in self.env['hr.public.holidays'].search([]):
                    for day in day_list:
                        if ((fields.Datetime.from_string(p_id.date_from).date() <= day) and (day <= fields.Datetime.from_string(p_id.date_to).date())):
                            if day.weekday() != 4 and day.weekday() != 5:
                                days -= 1
            days_total = days
            hours = self.env.company.resource_calendar_id.get_work_hours_count(date_from, date_to)
            return {'days': days_total, 'hours': hours}
        


    @api.constrains('date_from','date_to','holiday_status_id')
    def _leave_validity(self):
        #check Maximum
        if not self.sudo().employee_id.contract_ids:
            raise UserError('Sorry!!! This employee dont has a Contract')

        else:
            if self.holiday_status_id.leave_maximum and ( self.number_of_days > self.holiday_status_id.leave_maximum_number ) :
                raise UserError('Maximum Number Of Days Should Not Exceed %s Days' % (self.holiday_status_id.leave_maximum_number))


            date_start_contract = self.sudo().employee_id.contract_ids[0].date_start
            date = relativedelta(self.date_from, date_start_contract)
            years = date.years
            months = date.months + years*12
            days = date.days
            # raise UserError(months)
                # annual
            # if self.holiday_status_id.leave_type == 'annual' and months < 6:
            #     raise UserError('Employee Must Complete 6 Months Of Service')
            #maternaty
            # if self.holiday_status_id.leave_type == 'maternaty' and months < 6:
            #     raise UserError('Employee Must Complete 6 Months Of Service')
            # #paternaty
            # if self.holiday_status_id.leave_type == 'paternaty' and months < 6:
            #     raise UserError('Employee Must Complete 6 Months Of Service')
            #haj
            if self.holiday_status_id.leave_type == 'haj' and years < 1:
                raise UserError('Employee Must Complete 1 Year Of Service')
            if len ( self.env['hr.leave'].search([('state','=','validate'),('id','!=',self.id),('employee_id','=',self.employee_id.id),('holiday_status_id.leave_type','=','haj')]) ) > 0 :
                raise UserError('Employee Already took Haj Leave')
            #marriage
            if len ( self.env['hr.leave'].search([('state','=','validate'),('id','!=',self.id),('employee_id','=',self.employee_id.id),('holiday_status_id.leave_type','=','marriage')]) ) > 0 :
                raise UserError('Employee Already took Marriage Leave')
            #check attachment
            if self.holiday_status_id.attachment_required and not self.attachment:
                raise UserError('Please Upload Required Attachment')


# draft buttons
    def submit(self):  
        self.write({                
        'state': 'line_manager'        })

# line_manager buttons
    def lm_approve(self):  
        self.write({                
        'state': 'hr_officer'        })

    def lm_approve_reject(self):  
        self.write({    
        'state': 'draft'        })  


# hr_officer buttons
    def hr_approve(self):  
        self.write({                
        'state': 'validate1'        })

    def hr_manager_approve(self):
        self.write({
        'state': 'validate'        })

    def hr_approve_reject(self):  
        self.write({    
        'state': 'line_manager'        })  

# ccso buttons
    def ccso_approve(self):  
        self.write({                
        'state': 'validate'        })

    def ccso_approve_reject(self):  
        self.write({    
        'state': 'refuse'        })  

# cancel and set to draft buttons
    def cancel(self):  
        self.write({                
        'state': 'refuse'        })

    def set_to_draft(self):  
        self.write({    
        'state': 'draft'        })  
