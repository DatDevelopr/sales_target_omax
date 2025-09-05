from odoo import models, fields, api
from datetime import date
from odoo.exceptions import ValidationError


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

    order_ids = fields.One2many(
        'sale.order', 'sales_target_id',
        string="Sales Orders",
        compute="_compute_sale_orders",
    )
    sale_total = fields.Monetary(
        compute="_compute_sale_total", string="Total Sales", currency_field="currency_id"
    )
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)


    invoice_ids = fields.One2many(
        'account.move',   # model invoice
        'sales_target_id',   # field Many2one bên invoice (cần thêm)
        string="Invoices"
    )
    payment_ids = fields.One2many(
        'account.payment',
        'sales_target_id',
        string='Payments'
    )

    # ======================
    # TARGET INFO
    # ======================
    target_point = fields.Selection([
        ('so_confirm', 'Sale Order Confirm'),
        ('invoice_validation', 'Invoice Validation'),
        ('invoice_paid', 'Invoice Paid'),
    ], string="Target Point", required=True)

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

    theoretical_status = fields.Selection([
        ('above', "Above Target"),
        ('below', "Below Target"),
        ('completed', "Completed"),
    ], string="Theoretical Status", compute="_compute_theoretical", store=False)

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
                if record.target_point == 'so_confirm':
                    orders = self.env['sale.order'].search([
                        ('user_id', '=', record.salesperson_id.id),
                        ('state', 'in', ['sale', 'done']),
                        ('date_order', '>=', record.start_date),
                        ('date_order', '<=', record.end_date),
                    ])
                    total_sales = sum(orders.mapped('amount_total'))

                elif record.target_point == 'invoice_validation':
                    invoices = self.env['account.move'].search([
                        ('invoice_user_id', '=', record.salesperson_id.id),
                        ('state', '=', 'posted'),
                        ('invoice_date', '>=', record.start_date),
                        ('invoice_date', '<=', record.end_date),
                    ])
                    total_sales = sum(invoices.mapped('amount_total'))

                elif record.target_point == 'invoice_paid':
                    invoices = self.env['account.move'].search([
                        ('invoice_user_id', '=', record.salesperson_id.id),
                        ('payment_state', '=', 'paid'),
                        ('invoice_date', '>=', record.start_date),
                        ('invoice_date', '<=', record.end_date),
                    ])
                    total_sales = sum(invoices.mapped('amount_total'))

            record.achievement_amount = total_sales
            record.achievement_percent = (total_sales / record.target_amount * 100) if record.target_amount else 0

    @api.depends("order_ids.amount_total")
    def _compute_sale_total(self):
        for rec in self:
            rec.sale_total = sum(rec.order_ids.mapped("amount_total"))

    @api.depends('target_amount', 'achievement_amount')
    def _compute_difference(self):
        for record in self:
            record.difference_amount = record.target_amount - record.achievement_amount

    def _compute_theoretical(self):
        """Tính Theoretical Achievement dựa trên ngày hiện tại"""
        today = date.today()
        for record in self:
            record.theoretical_amount = 0
            record.theoretical_percent = 0
            record.theoretical_status = 'completed'

            if record.start_date and record.end_date and record.target_amount:
                if record.start_date <= today <= record.end_date:
                    total_days = (record.end_date - record.start_date).days + 1
                    current_day = (today - record.start_date).days + 1

                    theoretical_amount = (record.target_amount / total_days) * current_day
                    theoretical_percent = (theoretical_amount * 100) / record.target_amount

                    record.theoretical_amount = theoretical_amount
                    record.theoretical_percent = theoretical_percent

                    if record.achievement_amount > theoretical_amount:
                        record.theoretical_status = 'above'
                    else:
                        record.theoretical_status = 'below'
                else:
                    record.theoretical_status = 'completed'

    # ======================
    # CONSTRAINTS
    # ======================
    @api.constrains('salesperson_id', 'start_date', 'end_date', 'target_point')
    def _check_unique_sales_target(self):
        for record in self:
            # Tìm target khác cùng salesperson + target_point và thời gian overlap
            overlapping = self.search([
                ('id', '!=', record.id),
                ('salesperson_id', '=', record.salesperson_id.id),
                ('target_point', '=', record.target_point),
                ('start_date', '<=', record.end_date),
                ('end_date', '>=', record.start_date),
            ])
            if overlapping:
                raise ValidationError(
                    "Same Sales Person can't be in same duration for %s" % dict(self._fields['target_point'].selection).get(record.target_point)
                )
    @api.constrains('target_amount')
    def _check_target_amount(self):
        for record in self:
            if record.target_amount <= 0:
                raise ValidationError("Target amount must be greater than 0.")

    # ======================
    # ACTION METHODS
    # ======================
    def _update_achievement(self, record, point_type):
        """Hàm cập nhật Achievement khi có sự kiện xảy ra"""
        date_field = getattr(record, 'date_order', getattr(record, 'invoice_date', False))
        user_field = getattr(record, 'user_id', getattr(record, 'invoice_user_id', False))

        if not date_field or not user_field: 
            return

        targets = self.search([
            ('salesperson_id', '=', user_field.id),
            ('target_point', '=', point_type),
            ('start_date', '<=', date_field),
            ('end_date', '>=', date_field),
            ('state', '=', 'open')
        ])
        for target in targets:
            amount = record.amount_total
            target.achievement_amount += amount
            target.difference_amount = target.target_amount - target.achievement_amount
            target.achievement_percent = (target.achievement_amount / target.target_amount) * 100 if target.target_amount else 0

    def _compute_sale_orders(self):
        for rec in self:
            orders = self.env['sale.order'].search([
                ('user_id', '=', rec.salesperson_id.id),
                ('date_order', '>=', rec.start_date),
                ('date_order', '<=', rec.end_date),
                ('state', 'in', ['sale', 'done'])
            ])
            rec.order_ids = orders
    def action_confirm(self):

        for record in self:
            record.name = self.env['ir.sequence'].next_by_code('sales.target') or "New"
            record.state = 'open'

    def action_close(self):

        for record in self:
            record.state = 'closed'

    def action_send_mail(self):
        self.ensure_one()
        template = self.env.ref('sales_target_omax.email_template_sales_target')
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)

        ctx = {
            'default_model': 'sales.target',
            'default_res_ids': [self.id],
            'default_use_template': bool(template.id),
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
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


    def action_set_draft(self):
        self.write({'state': 'draft'})
