from odoo import models, fields, api

class SalesTeamTarget(models.Model):
    _name = "sales.team.target"
    _description = "Sales Team Sales Target"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Target Reference", 
        required=True, 
        copy=False, 
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('sales.team.target')
    )
    team_id = fields.Many2one("crm.team", string="Sales Team", required=True)
    user_id = fields.Many2one("res.users", string="Responsible (Team Leader)")
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", string="Currency", default=lambda self: self.env.company.currency_id)

    target_point = fields.Selection([
        ("sale_order", "Sale Order"),
        ("invoice_value", "Invoice Value"),
        ("invoice_paid", "Invoice Paid"),
    ], string="Target Point", required=True)

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    target = fields.Monetary(string="Target", currency_field="currency_id")
    achievement = fields.Monetary(string="Achievement", currency_field="currency_id")
    difference = fields.Monetary(string="Difference", compute="_compute_difference", store=True, currency_field="currency_id")

    achievement_percentage = fields.Float(string="Achievement Percentage", compute="_compute_percentage", store=True)

    # Theoretical Data
    theoretical_achievement = fields.Monetary(string="Theoretical Achievement", currency_field="currency_id")
    theoretical_percentage = fields.Float(string="Theoretical Achievement Percentage")
    theoretical_status = fields.Selection([
        ("completed", "Completed"),
        ("pending", "Pending"),
    ], string="Theoretical Achievement Status", default="pending")

    status = fields.Selection([
        ("draft", "Draft"),
        ("open", "Open"),
        ("closed", "Closed"),
    ], string="Status", default="draft", tracking=True)

    @api.depends("achievement", "target")
    def _compute_percentage(self):
        for rec in self:
            rec.achievement_percentage = (rec.achievement / rec.target * 100) if rec.target else 0.0

    @api.depends("achievement", "target")
    def _compute_difference(self):
        for rec in self:
            rec.difference = (rec.achievement - rec.target) if rec.target else 0.0

    # Actions
    def action_open(self):
        for rec in self:
            rec.status = "open"

    def action_close(self):
        for rec in self:
            rec.status = "closed"

    def action_draft(self):
        for rec in self:
            rec.status = "draft"
