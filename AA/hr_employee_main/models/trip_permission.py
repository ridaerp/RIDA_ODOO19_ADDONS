from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, format_date
from odoo import fields, models, api
from odoo.exceptions import UserError


class Company(models.Model):
    _inherit = "res.company"

    trip_bussiness_account_id = fields.Many2one('account.account', string='Trip Permission Account', store=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    trip_bussiness_account_id = fields.Many2one('account.account', related='company_id.trip_bussiness_account_id',
                                                string='Trip Permission Account', store=True, readonly=False)


class TripPermission(models.Model):
    _name = 'trip.permission'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    @api.model
    def default_get(self, fields):
        res = super(TripPermission, self).default_get(fields)
        if res.get('req_id', False):
            emp = self.env['hr.employee'].sudo().search([('user_id', '=', res['req_id'])],
                                                        limit=1)
            if not res.get('department_id', False):
                res.update({
                    'department_id': emp.department_id.id,
                })
        return res

    name = fields.Char(string='Name', readonly=True, )
    date = fields.Date(default=fields.Date.today())
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True)
    department_id = fields.Many2one('hr.department', string="Department")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    comments = fields.Text("Purpose")
    state = fields.Selection(
        [('draft', 'Draft'), ('wlm', 'Waiting Line Manager'), ('whmp', 'Waiting HR Manager Approve'),
         ('wha', 'Waiting HR Approve'),
         ('reject', 'reject'), ('wfm', 'Waiting Finance Manager'), ('internal_aud', 'Internal Audit'),
         ('ccso', 'CCSO Approve'), ('wod', 'Waiting Operation Director'),
         ('wd', 'Waiting Accountant'), ('wdp', 'Waiting Payment'), ('paid', 'Paid')],
        string='Status', default='draft', track_visibility='onchange')
    state_ccso = fields.Selection(related='state')
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    number_of_days = fields.Float(
        'Days', compute='_compute_number_of_days', store=True, copy=False, tracking=True)
    expense_type = fields.Selection(
        [('included', 'Included'),
         ('unincluded', 'Not-Included'), ], default='included',
        string='Accommodations')
    prop_date = fields.Date(string="Prop Departure date")
    return_date = fields.Date(string="Suggested Return date")
    user_type = fields.Char(compute='onchange_req')
    origin_point = fields.Char('Origin Point')
    employees_line_ids = fields.One2many(comodel_name="trip.permission.line", inverse_name="request_id",
                                         string="Employees", copy=1)
    journal_id = fields.Many2one('account.move', string='Journal Entry', readonly=1, copy=False)
    journal_payment_id = fields.Many2one('account.journal', string='Payment Journal', copy=False)
    trip_bussiness_account_id = fields.Many2one('account.account', string='Trip Permission Account',
                                                related='company_id.trip_bussiness_account_id'
                                                )
    trip_type = fields.Selection([('internal', 'Internal'),
         ('external', 'External'), ], default='internal',
        string='trip type')
    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency',
    store=True,
    readonly=True,)

    @api.depends('trip_type')
    def _compute_currency(self):
        sdg = self.env.ref('base.SDG')  # Change ID to your SDG currency xml_id
        usd = self.env.ref('base.USD')  # Change ID to your USD currency xml_id

        for rec in self:
            if rec.trip_type == 'internal':
                rec.currency_id = sdg
            else:
                rec.currency_id = usd

    def action_submit(self):
        return self.write({'state': 'wlm'})

    def action_approve(self):
        for rec in self:
            if self.env.user.has_group('base.group_system'):
                pass
            else:
                self.ensure_one()
                try:
                    line_manager = self.req_id.line_manager_id
                except:
                    line_manager = False
                # comment by ekhlas
                # if not line_manager or not self.user_has_groups('material_request.group_department_manager'):
                #     raise UserError("Sorry. Your are not authorized to approve this document!")
                if not line_manager or line_manager != rec.env.user:
                    raise UserError("Sorry. Your are not authorized to approve this document!")
        return self.write({'state': 'whmp'})

    def action_hr_manager_approve(self):
        return self.write({'state': 'wha'})

    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    def action_reject(self):
        for rec in self:
            rec.state = "reject"

    def action_validate(self):
        return self.write({'state': 'wfm'})

    def approve_finance_manager(self):
        x = []
        for emp in self.employees_line_ids:
            if not emp.employee_id.employee_partner_id:
                x.append(emp.employee_id.name)
        if x:
            raise UserError(f'{x} Doesn\'t Have Partner ')
        return self.write({'state': 'internal_aud'})

    def approve_internal_audit(self):
        if self.user_type == 'hq':
            return self.write({'state': 'ccso'})
        if self.user_type == 'site' or self.user_type == 'fleet':
            return self.write({'state': 'wod'})

    def approve_internal_audit(self):
        if self.user_type == 'hq':
            return self.write({'state': 'ccso'})
        if self.user_type == 'site' or self.user_type == 'fleet':
            return self.write({'state': 'wod'})

    def approve_operation_director(self):
        return self.write({'state': 'wd'})

    def approve_ccso(self):
        return self.write({'state': 'wd'})

    def approve_accountant(self):
        
        x = []
        for emp in self.employees_line_ids:
            if not emp.employee_id.company_id:
                x.append(emp.employee_id.name)

        if x:
            raise UserError(f"{x} Doesn't Assign Company")

        line_ids = []

        for cre in self.employees_line_ids:
            line_ids.append((0, 0, {
                'debit': 0,'credit': cre.total,'partner_id': cre.partner_id.id,'account_id': cre.account_payable.id,
                'currency_id': self.currency_id.id,
            }))

        # ع
        for deb in self.employees_line_ids:
            line_vals = { 'debit': deb.total,
                'credit': 0,'partner_id': deb.partner_id.id,'account_id': self.trip_bussiness_account_id.id,
                'currency_id': self.currency_id.id,}
            
            if deb.analytic_account_id:
                line_vals['analytic_distribution'] = {deb.analytic_account_id.id: 100}

            line_ids.append((0, 0, line_vals))

        move_line = self.env['account.move'].sudo().create({
            'ref': self.name,
            'move_type': 'entry',
            'currency_id': self.currency_id.id,
            'invoice_date': fields.Date.today(),
            'date': fields.Date.today(),
            'line_ids': line_ids,
            'company_id': self.company_id.id,
        })

        
        move_line.sudo().action_post()

           
        self.journal_id = move_line.id

        return self.write({'state': 'wdp'})


    def action_register_payment(self):
        for recc in self:
            if not recc.journal_payment_id:
                raise UserError(_("Please Enter Payment Journal"))
            for rec in recc.employees_line_ids:
                create_payment = {
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'partner_id': rec.partner_id.id,
                    # 'destination_account_id':rec.account_id.id,
                    'company_id': recc.company_id.id,
                    'amount': rec.total,
                    'currency_id': recc.currency_id.id,
                    'ref': recc.name,
                    'journal_id': recc.journal_payment_id.id,

                }
                po = self.env['account.payment'].create(create_payment)
                po.action_post()
                recc.state = "paid"
            return po

    def button_action_post(self):
        for record in self:
            po = self.env['account.payment'].search([('ref', '=', record.name)])
            po.action_post()
            record.state = "paid"

    def get_payment(self):
        self.ensure_one()
        tree_view_id = self.env.ref('account.view_account_supplier_payment_tree').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment',
            'view_id': tree_view_id,
            'view_mode': 'list',
            'res_model': 'account.payment',
            'domain': [('ref', '=', self.name)],
            'context': "{'create': False}"
        }

    @api.depends("req_id")
    def onchange_req(self):
        if self.req_id.user_type:
            self.user_type = self.req_id.user_type
        else:
            raise UserError('The Employee Type if NOT Set')

    @api.depends('prop_date', 'return_date')
    def _compute_number_of_days(self):
        for rec in self:
            if rec.prop_date and rec.return_date:
                rec.number_of_days = abs((rec.prop_date - rec.return_date).days) + 1
            else:
                rec.number_of_days = 0

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('trip.permission.code')
        return super(TripPermission, self).create(vals)

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")

        return super(TripPermission, self).unlink()


class TripPermissionLine(models.Model):
    _name = 'trip.permission.line'
    _order = "create_date desc"

    request_id = fields.Many2one("trip.permission", string="Employee")
    employee_id = fields.Many2one("hr.employee", string="Employee")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Partner", related='employee_id.employee_partner_id',
                                 readonly=True)
    account_payable = fields.Many2one(comodel_name="account.account", string="Payable",
                                      related='employee_id.employee_partner_id.property_account_payable_id', readonly=True)
    job_id = fields.Many2one('hr.job', string="Job", related='employee_id.job_id', readonly=True)
    number_of_days = fields.Float('No of Days')
    number_of_night = fields.Float('No of nights', compute='_compute_total')
    gross = fields.Integer("Gross", compute='check_employee_id')
    analytic_account_id = fields.Many2one("account.analytic.account", )
    per_diem = fields.Float('Per diem', compute='_compute_total')
    total = fields.Float('Total', compute='_compute_total')
    Location = fields.Char(string='Destination', required=True)
    b_account = fields.Many2one("res.partner.bank", related='employee_id.bank_account_id', string="Bank Account",
                                readonly=True)
    accommodation = fields.Float("Accommodation", compute='_compute_total', store=True)

    @api.depends('per_diem', 'number_of_days')
    def _compute_total(self):
        for rec in self:
            if rec.gross:
                per_diem = (rec.gross / 30) * 3
                if per_diem > 4000:
                    rec.per_diem = per_diem
                else:
                    rec.per_diem = 4000
                if rec.number_of_days:
                    rec.number_of_night = rec.number_of_days - 1
                rec.total = rec.per_diem * rec.number_of_night
            else:
                rec.per_diem = 0
                rec.number_of_night = 0
                rec.total = 0
                rec.accommodation = 0



    @api.depends('employee_id')
    def check_employee_id(self):
        for rec in self:
            if rec.employee_id:
                emp = self.env['hr.employee'].search([('id', '=', rec.employee_id.id)], limit=1)
                if emp and emp.sudo():
                    if emp.sudo().payroll_wage:
                        rec.gross = emp.sudo().payroll_wage
                    else:
                        raise UserError(f'The Employee {emp.name} doesn\'t have a Gross Salary in the Contract.')
                else:
                    raise UserError(f'The Employee {emp.emp_code} doesn\'t have a valid contract.')
                    print(f"Employee Code: {emp.emp_code}")
            else:
                rec.gross = 0 
