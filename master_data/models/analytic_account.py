from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

from odoo import SUPERUSER_ID

class RequestAnalyticAccount(models.Model):
    _name = 'request.analytic.account'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Analytic Account  Request'

    code_seq = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True,
                             readonly=True)
    department_id = fields.Many2one('hr.department', string="Department", readonly=True, store=True)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")
    state = fields.Selection(
        [('draft', 'Draft'), ('w_adv', 'Waiting Account Advisor'), ('md', 'Waiting Master Admin'),
         ('reject', 'reject'), ('done', 'Done')],
        string='Status', default='draft', track_visibility='onchange', copy=False)
    date = fields.Date(default=fields.Date.today(), readonly=True)

    name = fields.Char(string='Analytic Account', index=True, required=True, tracking=True)
    code = fields.Char(string='Reference', index=True, tracking=True)
    type = fields.Selection(string="", selection=[('dept', 'Department'), ('asset_mach', 'Asset / Machine'),('plant', 'Plant'),('process', 'Process'),('project', 'Project'),('supplier', 'Material Minds/supplier'),('other', 'Others'),], required=False, )
    analytic_type = fields.Selection(string="", selection=[('ser_cost_center', 'Service Cost Centers'),
                                                           ('prod_cost_center', 'Productive Cost Center'),
                                                           ('admin_cost_center', 'Administrative Cost Center'),
                                                           ('capitalized', 'Capitalized Cost Centers'),
                                                           ('group_business_dev', 'Group Business Development '),
                                                           ('group_cost_center', 'Group Cost Centers'),
                                                           ('none', 'None'), ], required=False, )
    group_id = fields.Many2one('account.analytic.group', string='Group', check_company=True)
    plan_id = fields.Many2one('account.analytic.plan', string='Analytic Plan', )
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)
    new_analytic = fields.Many2one("account.analytic.account", string='Analytic Account', readonly=1, copy=False)
    supplier_id=fields.Many2one("request.vendor","Supplier Request")
    partner_id=fields.Many2one("res.partner","Partner")
    def _track_subtype(self, init_values):
        self.ensure_one()
        if self.state == 'done':
            return self.env.ref('master_data.request_account_analytic_account_status')
        if self.state == 'reject':
            return self.env.ref('master_data.request_account_analytic_account_rej_status')
        return super(RequestAnalyticAccount, self)._track_subtype(init_values)

    def activity_update(self):
        for rec in self:
            users = []
            message = ""
            if rec.state == 'w_adv':
                users = self.env.ref('base_rida.rida_group_master_data_manager').users
                message = "Please Create the Analytic Account"
                for user in users:
                    self.activity_schedule('master_data.mail_act_master_data_approval', user_id=user.id, note=message)
            else:
                continue


    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")

        return super(RequestAnalyticAccount, self).unlink()

    @api.model
    def create(self, vals):
        for val in vals:
            val['code_seq'] = self.env['ir.sequence'].next_by_code('analytic.request') or ' '

        return super(RequestAnalyticAccount, self).create(vals)

    def set_confirm(self):
        return self.write({'state': 'w_adv'})

    def set_validate(self):
        self.activity_update()
        return self.write({'state': 'md'})


    def create_analytic(self):
        if self.new_analytic:
            raise UserError("Analytic account has already been created.")

        # Step 1: Create analytic account without partner_id
        analytic = self.env["account.analytic.account"].create({
            'name': self.name,
            'code': self.code,
            'type': self.type,
            'analytic_type': self.analytic_type,
            'plan_id': self.plan_id.id,
            'company_id': self.company_id.id,
            # 'partner_id': self.partner_id.id  # can't set yet
        })

        self.new_analytic = analytic

        # Step 2: Create or assign the partner
        if self.supplier_id:
            self.supplier_id.with_user(SUPERUSER_ID).create_vendor()
            if self.supplier_id.partner:
                # Step 3: Update partner_id in analytic account
                analytic.partner_id = self.supplier_id.partner.id

        self.state = 'done'
        return True

class accountAnalyticGroup(models.Model):
    _name = 'account.analytic.group'
    _description = 'Analytic Account Group'

    name = fields.Char()



class maintenanceEquipmentTag(models.Model):
    _name = 'maintenance.equipment.tag'
    _description = 'Maintenance Equipment Tag'

    name = fields.Char()