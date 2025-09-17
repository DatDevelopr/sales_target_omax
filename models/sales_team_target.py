from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

class SalesTeamTarget(models.Model):
    _name = "sales.team.target"
    _description = "Sales Team Sales Target"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('sales.team.target'))

    team_id = fields.Many2one('crm.team', string="Sales Team", required=True)
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    user_id = fields.Many2one('res.users', string="Responsible (Team Leader)", required=True)

    company_id = fields.Many2one('res.company', string="Company", required=True,
                                default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string="Currency", required=True,
                                default=lambda self: self.env.company.currency_id)

    target_point = fields.Selection([
        ('so_confirm', 'Sale Order Confirm'),
        ('invoice_validation', 'Invoice Validation'),
        ('invoice_paid', 'Invoice Paid'),
    ], string="Target Point", default='so_confirm')

    target = fields.Monetary(string="Target", currency_field="currency_id")
    achievement = fields.Monetary(string="Achievement", currency_field="currency_id", readonly=True)
    difference = fields.Monetary(string="Difference", compute="_compute_difference", store=True, currency_field="currency_id")
    achievement_percentage = fields.Float(string="Achievement Percentage", compute="_compute_percentage", store=True)

    # Theoretical
    theoretical_achievement = fields.Float(string="Theoretical Achievement")
    theoretical_percentage = fields.Float(string="Theoretical Achievement Percentage")
    theoretical_status = fields.Selection([
        ('completed', 'Completed'),
        ('in_progress', 'In Progress'),
        ('failed', 'Failed'),
    ], string="Theoretical Achievement Status", default="in_progress")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string="Status", default="draft", tracking=True)

    order_ids = fields.One2many(
        'sale.order',
        'sales_team_target_id',
        string="Sales Orders"
    )
    sale_total = fields.Monetary(
        string="Total Sales", 
        compute="_compute_sale_total", 
        store=False,
        currency_field="currency_id"
    )
    invoice_ids = fields.One2many(
        'account.move',   # model invoice
        'sales_team_target_id',   # field Many2one bên invoice (cần thêm)
        string="Invoices",
        compute="_compute_invoice_ids",
        store=False
    )
    invoice_total = fields.Monetary(
        string="Total Invoice", 
        compute="_compute_invoice_total", 
        store=False,
        currency_field="currency_id"
    )
    @api.depends('order_ids', 'order_ids.amount_total')
    def _compute_sale_total(self):
        for rec in self:
            rec.sale_total = sum(rec.order_ids.mapped('amount_total'))
    @api.depends('invoice_ids.amount_total')
    def _compute_invoice_total(self):
        for rec in self:
            rec.invoice_total = sum(rec.invoice_ids.mapped('amount_total'))

    @api.depends('target_point', 'team_id', 'start_date', 'end_date')
    def _compute_invoice_ids(self):
        for rec in self:
            if not (rec.team_id and rec.start_date and rec.end_date):
                rec.invoice_ids = False
                continue
            domain = [
                ('team_id', '=', rec.team_id.id),  # cần chắc chắn account.move có field team_id
                ('invoice_date', '>=', rec.start_date),
                ('invoice_date', '<=', rec.end_date),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
            ]
            if rec.target_point == 'invoice_validation':
                domain.append(('payment_state', '!=', 'paid'))
            elif rec.target_point == 'invoice_paid':
                domain.append(('payment_state', '=', 'paid'))
            rec.invoice_ids = self.env['account.move'].search(domain)


    @api.constrains('team_id', 'start_date', 'end_date', 'target_point')
    def _check_unique_team_date_targetpoint(self):
        for rec in self:
            conflict = self.search([
                ('id', '!=', rec.id),
                ('team_id', '=', rec.team_id.id),
                ('target_point', '=', rec.target_point),
                ('start_date', '<=', rec.end_date),
                ('end_date', '>=', rec.start_date),
            ], limit=1)
            if conflict:
                raise ValidationError((
                    "A Sales Team Target already exists for team '%s' with Target Point '%s' in this date range!"
                ) % (rec.team_id.name, rec.target_point))

    @api.depends('target')
    def _compute_achievement(self):
        """Tự cộng achievement từ sale.order hoặc invoice theo target_point"""
        for rec in self:
            achievement = 0.0
            if rec.target_point == 'so_confirm':
                orders = self.env['sale.order'].search([
                    ('team_id', '=', rec.team_id.id),
                    ('date_order', '>=', rec.start_date),
                    ('date_order', '<=', rec.end_date),
                    ('state', 'in', ['sale', 'done']),
                ])
                achievement = sum(orders.mapped('amount_total'))
            elif rec.target_point == 'invoice_paid':
                invoices = self.env['account.move'].search([
                    ('invoice_date', '>=', rec.start_date),
                    ('invoice_date', '<=', rec.end_date),
                    ('team_id', '=', rec.team_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('payment_state', '=', 'paid'),
                ])
                achievement = sum(invoices.mapped('amount_total'))

            elif rec.target_point == 'invoice_amount':
                invoices = self.env['account.move'].search([
                    ('invoice_date', '>=', rec.start_date),
                    ('invoice_date', '<=', rec.end_date),
                    ('team_id', '=', rec.team_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                ])
                achievement = sum(invoices.mapped('amount_total'))
            rec.achievement = achievement
    @api.depends('target', 'achievement')
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.achievement - rec.target

    @api.depends('target', 'achievement')
    def _compute_percentage(self):
        for rec in self:
            if rec.target > 0:
                rec.achievement_percentage = (rec.achievement / rec.target) * 100
            else:
                rec.achievement_percentage = 0

    @api.depends('target', 'start_date', 'end_date')
    def _compute_theoretical(self):
        """Tính Theoretical achievement theo ngày hiện tại"""
        today = date.today()
        for rec in self:
            if not rec.start_date or not rec.end_date or not rec.target:
                rec.theoretical_achievement = 0
                rec.theoretical_percentage = 0
                rec.theoretical_status = 'in_progress'
                continue

            if rec.start_date <= today <= rec.end_date:
                total_days = (rec.end_date - rec.start_date).days + 1
                current_day = (today - rec.start_date).days + 1
                theo = (rec.target / total_days) * current_day
                rec.theoretical_achievement = theo
                rec.theoretical_percentage = (theo / rec.target) * 100 if rec.target else 0
                rec.theoretical_status = 'completed' if rec.achievement >= theo else 'in_progress'
            else:
                rec.theoretical_achievement = rec.target
                rec.theoretical_percentage = 100
                rec.theoretical_status = 'completed'

    def _update_achievement(self, record, point_type):
        """Cập nhật achievement khi có Sale Order hoặc Invoice."""
        date_field = getattr(record, 'date_order', getattr(record, 'invoice_date', False))
        team_field = getattr(record, 'team_id', False)
        amount = getattr(record, 'amount_total', 0)

        if not date_field or not team_field:
            return

        targets = self.search([
            ('team_id', '=', team_field.id),
            ('target_point', '=', point_type),
            ('start_date', '<=', date_field),
            ('end_date', '>=', date_field),
            ('state', '=', 'open')
        ])

        for target in targets:
            new_amount = target.achievement + amount
            target.write({
                'achievement': new_amount,
                'difference': new_amount - target.target,
                'achievement_percentage': (new_amount / target.target * 100) if target.target else 0,
            })
    def action_confirm(self):
        for record in self:
            if not record.start_date or not record.end_date or not record.target:
                raise ValidationError("Start Date, End Date, and Target are required to confirm!")
            record.state = 'open'

    def action_close(self):
        for record in self:
            if record.state != 'open':
                raise ValidationError("Can only close an Open target!")
            record.state = 'closed'

    def action_set_draft(self):
        for record in self:
            if record.state == 'closed':
                raise ValidationError("Cannot set a Closed target back to Draft!")
            record.state = 'draft'

    def action_send_mail(self):
        self.ensure_one()
        template = self.env.ref('sales_target_omax.email_template_sales_team_target', raise_if_not_found=False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=False)
        
        if not compose_form:
            raise ValueError("Email compose form not found!")
        if not template:
            raise ValueError("Email template 'sales_target_omax.email_template_sales_team_target' not found!")
        
        # Đảm bảo context truyền đúng dữ liệu
        ctx = {
            'default_model': 'sales.team.target',
            'default_res_ids': [self.id],
            'default_use_template': bool(template.id),
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'force_email': True,  # Bắt buộc sử dụng email
        }

        return {
            'name': 'Send Mail',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'target': 'new',
            'context': ctx,
        }