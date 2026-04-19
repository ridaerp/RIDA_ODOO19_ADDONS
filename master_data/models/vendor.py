from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

from difflib import SequenceMatcher




class RequestVendor(models.Model):
    _name = 'request.vendor'
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Supplier Request'

    def default_get(self, fields):
        res = super(RequestVendor, self).default_get(fields)
        if not self.env.user.has_group('material_request.group_ore_rock_purchase_user'):
            is_rock_vendor = False
        else:
            is_rock_vendor = True
        res['is_rock_vendor'] = is_rock_vendor
        return res

    def _default_category(self):
        return self.env['res.partner.category'].browse(self._context.get('category_id'))

    @api.model
    def _lang_get(self):
        return self.env['res.lang'].get_installed()

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'NEW')
    req_id = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, tracking=True,
                             readonly=True)
    department_id = fields.Many2one('hr.department', string="Department", readonly=True, store=True)
    reason_reject = fields.Text(string='Reject Reason', track_visibility="onchange")

    lang = fields.Selection(_lang_get, string='Language'
                            , default='en_US',
                            help="All the emails and documents sent to this contact will be translated in this language.")
    description = fields.Text('')
    category_id = fields.Many2many('res.partner.category', column1='partner_id',
                                   column2='category_id', string='Tags', default=_default_category)
    date = fields.Date(default=fields.Date.today(), readonly=True)
    vendor_name = fields.Char(required=True)
    phone = fields.Char(required=True)
    email = fields.Char()
    state = fields.Selection(
        [('draft', 'Draft'), ('scm', 'Waiting Procurement Manager'), ('w_ore_rock', 'Waiting Ore/Rock Manager'),
         ('w_account', 'Waiting Account Verification'), ('w_audit', 'Waiting Internal Audit'),
         ('w_scm_director', 'Waiting Supply Chain Director'),
         ('w_adv', 'Waiting Finance Manager /Analyti Account'),
         ('md', 'Waiting Finance Manager'),
         ('reject', 'reject'), ('done', 'Done')],
        string='Status', default='draft', tracking=True)
    state_rock = fields.Selection(related='state')
    partner = fields.Many2one('res.partner', string='Partner')
    is_rock_vendor = fields.Boolean()
    bank_ids = fields.One2many('master.data.res.partner.bank', 'master_data_sup_id', string='Banks')

    # area_x = fields.Many2many('x_area')
    analytic_account_req_id=fields.Many2one("request.analytic.account","Analyti Account Request No.")

    rea_ids = fields.Many2many(
        comodel_name='x_area',  # The model to relate to
        relation='partner_area_rel',  # The name of the relation table
        column1='partner_id',  # The column for the current model (res.partner)
        column2='area_id',     # The column for the related model (area)
        string='Areas'
    )
   
    east = fields.Integer("Easting")
    north = fields.Integer("Northing")
    rock_type = fields.Selection(
        [('qtz', 'QTZ'),
         ('m_vol', 'M.VOL'),
         ('chert', 'CHERT')],
        string='Rock Type'
    )
    duplicate_warning = fields.Boolean(default=False)


    def activity_update(self):
        for rec in self:
            users = []
            # rec.activity_unlink(['hr_salary_advance.mail_act_approval'])
            # if rec.state not in ['draft','reject']:
            #     continue
            message = ""
            if rec.state == 'w_account':
                users = self.env.ref('account.group_account_user').user_ids
                message = "Please check the supplier's financial data."
                for user in users:
                    self.activity_schedule('master_data.mail_act_master_data_approval', user_id=user.id, note=message)
            if rec.state == 'w_audit':
                users = self.env.ref('base_rida.rida_internal_audit').user_ids
                message = "Please Conduct an internal review of the supplier request."
                for user in users:
                    self.activity_schedule('master_data.mail_act_master_data_approval', user_id=user.id, note=message)
            if rec.state == 'md':
                users = self.env.ref('base_rida.rida_finance_manager').user_ids
                message = "Please Review the Supplier's Request And Create the Supplier "
                for user in users:
                    self.activity_schedule('master_data.mail_act_master_data_approval', user_id=user.id, note=message)
            else:
                continue

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError("Sorry! only draft records can be deleted!")

        return super(RequestVendor, self).unlink()

    @api.model
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('vendor.request') or ' '

        return super(RequestVendor, self).create(vals)


    # =========================
    # ARABIC NORMALIZATION FUNCTION
    # =========================
    def _normalize_arabic(self, text):
        if not text:
            return ""
        replacements = {
            "أ": "ا", "إ": "ا", "آ": "ا",
            "ة": "ه",
            "ى": "ي",
            "ئ": "ي", "ؤ": "و",
            "ـ": "",
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return "".join(text.split()).strip()



    def _check_duplicates(self):
        partners = self.env['res.partner'].search([])
        normalized_req = self._normalize_arabic(self.vendor_name)
        duplicates_name = []
        duplicates_phone = []
        duplicates_email = []

        req_words = normalized_req.split()

        for partner in partners:
            # Phone duplicate
            if self.phone and partner.phone == self.phone:
                duplicates_phone.append(partner)
                continue

            # Email duplicate
            if self.email and partner.email == self.email:
                duplicates_email.append(partner)
                continue

            # Name similarity
            name_norm = self._normalize_arabic(partner.name)
            partner_words = name_norm.split()
            match_count = sum(
                1 for rw in req_words if any(SequenceMatcher(None, rw, pw).ratio() > 0.75 for pw in partner_words)
            )
            if match_count >= max(1, len(req_words)//2):
                duplicates_name.append(partner)

        return duplicates_name, duplicates_phone, duplicates_email





    def set_submit(self):
        duplicates_name, duplicates_phone, duplicates_email = self._check_duplicates()
        warning_messages = []

        # Block submission for phone/email duplicates
        if duplicates_phone:
            raise UserError(_("Phone already exists for another supplier: %s") % duplicates_phone[0].name)
        if duplicates_email:
            raise UserError(_("Email already exists for another supplier: %s") % duplicates_email[0].name)

        # Check name duplicates
        if duplicates_name:
            names = ", ".join([p.name for p in duplicates_name])
            warning_messages.append("⚠ Warning: Similar supplier names detected:\n%s" % names)

        # If any warning, show popup but continue
        # if warning_messages:
        #     return {
        #         'type': 'ir.actions.client',
        #         'tag': 'display_notification',
        #         'params': {
        #             'title': "Duplicate Check",
        #             'message': "\n".join(warning_messages),
        #             'sticky': False,  # True = user must dismiss, False = auto-hide
        #         }
        #     }

        # Normal state change
        return self.write({'state': 'w_ore_rock' if self.is_rock_vendor else 'scm'})





    # def set_submit(self):
    #     duplicates_name, duplicates_phone, duplicates_email = self._check_duplicates()
    #     warning_messages = []

    #     # Check phone duplicates
    #     if duplicates_phone:
    #         warning_messages.append("Phone already exists for supplier: %s" % duplicates_phone[0].name)

    #     # Check email duplicates
    #     if duplicates_email:
    #         warning_messages.append("Email already exists for supplier: %s" % duplicates_email[0].name)

    #     # Check name duplicates
    #     if duplicates_name:
    #         names = ", ".join([p.name for p in duplicates_name])
    #         warning_messages.append("⚠ Warning: Similar supplier names detected:\n%s" % names)

    #     # If any warning, show popup but continue
    #     if warning_messages:
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'title': "Duplicate Check",
    #                 'message': "\n".join(warning_messages),
    #                 'sticky': False,  # True = user must dismiss, False = auto-hide
    #             }
    #         }

    #     # Normal state change
    #     return self.write({'state': 'w_ore_rock' if self.is_rock_vendor else 'scm'})

    @api.onchange('vendor_name', 'phone', 'email','state')
    def _onchange_duplicate_check(self):
        duplicates_name, duplicates_phone, duplicates_email = self._check_duplicates()
        # Only for similar names
        if duplicates_name:
            names = ", ".join([p.name for p in duplicates_name])
            self.duplicate_warning = True
            return {
                'warning': {
                    'title': "Similar Suppliers Detected",
                    'message': f"⚠ Warning: Similar supplier names detected:\n{names}\nYou can still submit this request."
                }
            }
        self.duplicate_warning = False
        return {}







    def set_confirm(self):
        if self.is_rock_vendor:
            self.activity_update()

            is_opu = any(tag.name == 'MATERIAL MINDS' for tag in self.category_id)

            if is_opu:
                # Auto-create the analytic request if not already created
                analytic_request = self.env['request.analytic.account'].search([('supplier_id', '=', self.id)], limit=1)
                if not analytic_request:
                    Analyti_account=self.env['request.analytic.account'].create({
                        'name': 'منجم ' + self.vendor_name,
                        'code': 'M-MIND/Su-00'+str(self.id),
                        'department_id': self.department_id.id,
                        'supplier_id': self.id,
                        'partner_id': self.partner.id if self.partner else None,
                        'type': 'supplier',
                        'analytic_type': 'prod_cost_center',
                        'state': 'w_adv',
                        'company_id': self.env.company.id,
                    })


                return self.write({'state': 'w_adv','analytic_account_req_id':Analyti_account})
            else:
                return self.write({'state': 'md'})
        else:
            return self.write({'state': 'w_scm_director'})

    def account_verification(self):
        for rec in self:
            if rec.is_rock_vendor:
                rec.state = 'w_audit'
                rec.activity_update()

    def internal_audit(self):
            for rec in self:
                if rec.is_rock_vendor:
                    rec.state = 'md'
                    rec.activity_update()

    def set_draft(self):
        for rec in self:
            rec.state = 'draft'


    def create_vendor(self):
        attachment = self.env['ir.attachment'].sudo().search(
            [('res_model', '=', 'request.vendor'), ('res_id', '=', self.id)])
        self.partner = self.env['res.partner'].sudo().create({
            'name': self.vendor_name,
            'type': 'contact',
            'category_id': [(6, 0, [rec.id for rec in self.category_id])],
            'phone': self.phone,
            'email': self.email,
            'lang': 'en_US',
            'comment': self.description,
            'east': self.east,
            'north': self.north,
            'rock_type': self.rock_type,
            'rea_ids': [(6, 0, [rec.id for rec in self.rea_ids])],
        })
        for rec in attachment:
            rec.sudo().write({'res_model': 'res.partner', 'res_id': self.partner.id})

        # Create the corresponding bank accounts from master data banks
        if self.partner:
            bank_records = []
            for bank in self.sudo().bank_ids:
                new_bank = self.env['res.partner.bank'].sudo().create({
                    'partner_id': self.partner.sudo().id,
                    'bank_id': bank.sudo().bank_id.id,
                    'acc_number': bank.sudo().acc_number,
                    'sequence': bank.sequence,
                })
                bank_records.append(new_bank.id)

            # Update the partner's bank_ids with the created bank accounts
            self.partner.sudo().bank_ids = [(6, 0, bank_records)]
        





        return self.sudo().write({'state': 'done'})


class MasterDataResPartnerBank(models.Model):
    _name = "master.data.res.partner.bank"

    master_data_sup_id = fields.Many2one(comodel_name="request.vendor")
    bank_id = fields.Many2one('res.bank', string='Bank')
    acc_number = fields.Char('Account Number', required=True)
    sequence = fields.Integer(default=10)
