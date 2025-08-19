from odoo import models, fields, api


class SalesTarget(models.Model):
    _name = "sales.target"
    _description = "Salesperson Sales Target"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ======================
    # BASIC INFO
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
        required=True,
        tracking=True
    )

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)

    

    responsible_id = fields.Many2one(
        'res.users',
        string="Responsible"
    )

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id
    )

    # ======================
    # TARGET INFO
    # ======================
    target_point = fields.Selection([
        ('order_confirm', 'Sale Order Confirm'),
        ('invoice_paid', 'Invoice Paid'),
        ('invoice_validate', 'Invoice Validate'),
    ], string="Target Point", default="order_confirm")

    target_amount = fields.Monetary(
        string="Target",
        currency_field="currency_id"
    )

    achievement_amount = fields.Monetary(
        string="Achievement",
        currency_field="currency_id",
        compute="_compute_achievement",
        store=True
    )

    difference_amount = fields.Monetary(
        string="Difference",
        currency_field="currency_id",
        compute="_compute_difference",
        store=True
    )

    achievement_percent = fields.Float(
        string="Achievement Percentage",
        compute="_compute_achievement",
        store=True
    )

    # ======================
    # THEORETICAL DATA
    # ======================
    theoretical_amount = fields.Monetary(
        string="Theoretical Achievement",
        currency_field="currency_id",
        compute="_compute_theoretical",
        store=False
    )

    theoretical_percent = fields.Float(
        string="Theoretical Achievement Percentage",
        compute="_compute_theoretical",
        store=False
    )

    # ======================
    # STATE
    # ======================
    state = fields.Selection([
        ('draft', "Draft"),
        ('open', "Open"),
        ('closed', "Closed"),
    ], string="Status", default="draft", tracking=True)

    # ======================
    # COMPUTE METHODS
    # ======================
    @api.depends('target_amount', 'salesperson_id', 'start_date', 'end_date', 'target_point')
    def _compute_achievement(self):
        """Tính Achievement dựa theo Target Point"""
        for record in self:
            total_sales = 0
            if record.salesperson_id and record.start_date and record.end_date:
                domain = []
                if record.target_point == 'order_confirm':
                    domain = [
                        ('user_id', '=', record.salesperson_id.id),
                        ('state', 'in', ['sale', 'done']),
                        ('date_order', '>=', record.start_date),
                        ('date_order', '<=', record.end_date),
                    ]
                    orders = self.env['sale.order'].search(domain)
                    total_sales = sum(orders.mapped('amount_total'))

                elif record.target_point == 'invoice_paid':
                    domain = [
                        ('invoice_user_id', '=', record.salesperson_id.id),
                        ('payment_state', '=', 'paid'),
                        ('invoice_date', '>=', record.start_date),
                        ('invoice_date', '<=', record.end_date),
                    ]
                    invoices = self.env['account.move'].search(domain)
                    total_sales = sum(invoices.mapped('amount_total'))

                elif record.target_point == 'invoice_validate':
                    domain = [
                        ('invoice_user_id', '=', record.salesperson_id.id),
                        ('state', '=', 'posted'),
                        ('invoice_date', '>=', record.start_date),
                        ('invoice_date', '<=', record.end_date),
                    ]
                    invoices = self.env['account.move'].search(domain)
                    total_sales = sum(invoices.mapped('amount_total'))

            record.achievement_amount = total_sales
            record.achievement_percent = (total_sales / record.target_amount * 100) if record.target_amount else 0

    @api.constrains('target_amount')
    def _check_target_amount(self):
        """Kiểm tra target_amount phải lớn hơn 0"""
        for record in self:
            if record.target_amount <= 0:
                raise ValueError("Target amount must be greater than 0.")
    
    @api.depends('target_amount', 'achievement_amount')
    def _compute_difference(self):
        for record in self:
            record.difference_amount = record.target_amount - record.achievement_amount

    def _compute_theoretical(self):
        """Demo: Tính theoretical achievement (giả định 50%)"""
        for record in self:
            record.theoretical_amount = record.target_amount * 0.5
            record.theoretical_percent = 50
    def action_confirm(self):
        """Chuyển từ draft -> open"""
        for record in self:
            record.state = 'open'

    def action_close(self):
        """Đóng target (open -> closed)"""
        for record in self:
            record.state = 'closed'

    def action_reset_to_draft(self):
        """Đưa về draft"""
        for record in self:
            record.state = 'draft'