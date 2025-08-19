from odoo import models, fields, api

class SalesTarget(models.Model):
    _name = "sales.target"
    _description = "Salesperson Sales Target"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ======================
    # FIELDS
    # ======================
    name = fields.Char(
        string="Target Reference",
        required=True,
        copy=False,
        default="New"
    )
    salesperson_id = fields.Many2one(
        'res.users',
        string="Salesperson",
        required=True
    )
    responsible_id = fields.Many2one(
        'res.users',
        string="Responsible"
    )
    target_point = fields.Float(string="Target Point")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    target_amount = fields.Float(string="Target Amount")
    achievement_amount = fields.Float(
        string="Achievement",
        compute="_compute_achievement",
        store=True
    )
    achievement_percent = fields.Float(
        string="Achievement Percent",
        compute="_compute_achievement",
        store=True
    )

    state = fields.Selection([
        ('draft', "Draft"),
        ('in_progress', "In Progress"),
        ('done', "Done"),
        ('cancel', "Cancelled"),
    ], string="Status", default="draft", tracking=True)

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )

    # ======================
    # COMPUTE METHODS
    # ======================
    @api.depends('target_amount', 'salesperson_id', 'start_date', 'end_date')
    def _compute_achievement(self):
        """
        Tính doanh số đã đạt được dựa trên Sale Order đã confirm
        """
        for record in self:
            total_sales = 0
            if record.salesperson_id and record.start_date and record.end_date:
                orders = self.env['sale.order'].search([
                    ('user_id', '=', record.salesperson_id.id),
                    ('state', 'in', ['sale', 'done']),
                    ('date_order', '>=', record.start_date),
                    ('date_order', '<=', record.end_date),
                ])
                total_sales = sum(orders.mapped('amount_total'))

            record.achievement_amount = total_sales
            record.achievement_percent = (total_sales / record.target_amount * 100) if record.target_amount else 0
