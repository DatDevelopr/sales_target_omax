from odoo import models, fields, api
from odoo.exceptions import ValidationError

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
        ('sale_order_confirm', 'Sale Order Confirm'),
        ('invoice_paid', 'Invoice Paid'),
        ('invoice_amount', 'Invoice Amount'),
    ], string="Target Point", default='sale_order_confirm')

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