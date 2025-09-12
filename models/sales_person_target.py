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
        compute="_compute_sale_total", string="Total Sales", currency_field="currency_id", store=False
    )
    
    invoice_ids = fields.One2many(
        'account.move',   # model invoice
        'sales_target_id',   # field Many2one bên invoice (cần thêm)
        string="Invoices",
        compute="_compute_invoice_ids",
        store=False
    )
    invoice_total = fields.Monetary(
        compute="_compute_invoice_total", 
        string="Total Invoices", 
        currency_field="currency_id"
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

    @api.depends('order_ids.amount_total')
    def _compute_sale_total(self):
        for rec in self:
            rec.sale_total = sum(rec.order_ids.mapped('amount_total'))

    
    @api.depends("invoice_ids.amount_total")
    def _compute_invoice_total(self):
        for rec in self:
            rec.invoice_total = sum(rec.invoice_ids.mapped("amount_total"))
    
    @api.depends('target_amount', 'achievement_amount')
    def _compute_difference(self):
        for rec in self:
            rec.difference_amount = rec.target_amount - rec.achievement_amount
            
    @api.depends('target_point', 'salesperson_id', 'start_date', 'end_date')
    def _compute_invoice_ids(self):
        for rec in self:
            if not (rec.salesperson_id and rec.start_date and rec.end_date):
                rec.invoice_ids = False
                continue
            domain = [
                ('invoice_user_id', '=', rec.salesperson_id.id),
                ('invoice_date', '>=', rec.start_date),
                ('invoice_date', '<=', rec.end_date),
                ('state', '=', 'posted'),
            ]
            if rec.target_point == 'invoice_validation':
                domain.append(('payment_state', '!=', 'paid'))  # chỉ lấy Not Paid
            elif rec.target_point == 'invoice_paid':
                domain.append(('payment_state', '=', 'paid'))   # chỉ lấy Paid

            invoices = self.env['account.move'].search(domain)
            rec.invoice_ids = invoices
    @api.depends('target_amount', 'order_ids', 'invoice_ids', 'target_point')
    def _compute_achievement(self):
        """Tính tổng achievement dựa trên target_point"""
        for rec in self:
            total = 0
            if rec.target_point == 'so_confirm':
                total = rec.sale_total
            else:
                total = rec.invoice_total

            rec.achievement_amount = total
            rec.achievement_percent = (total / rec.target_amount * 100) if rec.target_amount else 0

    def _compute_theoretical(self):
        """Tính theoretical achievement theo tiến độ ngày"""
        today = date.today()
        for rec in self:
            rec.theoretical_amount = 0
            rec.theoretical_percent = 0
            rec.theoretical_status = 'completed'

            if rec.start_date and rec.end_date and rec.target_amount:
                if rec.start_date <= today <= rec.end_date:
                    total_days = (rec.end_date - rec.start_date).days + 1
                    current_day = (today - rec.start_date).days + 1

                    theo_amount = (rec.target_amount / total_days) * current_day
                    theo_percent = (theo_amount * 100) / rec.target_amount

                    rec.theoretical_amount = theo_amount
                    rec.theoretical_percent = theo_percent

                    if rec.achievement_amount > theo_amount:
                        rec.theoretical_status = 'above'
                    else:
                        rec.theoretical_status = 'below'
                else:
                    rec.theoretical_status = 'completed'
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
        """Cập nhật achievement khi có Sale Order hoặc Invoice."""
        # Lấy ngày, người phụ trách và số tiền
        date_field = getattr(record, 'date_order', getattr(record, 'invoice_date', False))
        user_field = getattr(record, 'user_id', getattr(record, 'invoice_user_id', False))
        amount = getattr(record, 'amount_total', 0)

        if not date_field or not user_field:
            return

        # Tìm các sales.target phù hợp
        targets = self.search([
            ('salesperson_id', '=', user_field.id),
            ('target_point', '=', point_type),
            ('start_date', '<=', date_field),
            ('end_date', '>=', date_field),
            ('state', '=', 'open')
        ])

        # Cập nhật achievement
        for target in targets:
            new_amount = target.achievement_amount + amount
            target.write({
                'achievement_amount': new_amount,
                'difference_amount': target.target_amount - new_amount,
                'achievement_percent': (new_amount / target.target_amount * 100) if target.target_amount else 0,
            })

    @api.depends('target_point', 'salesperson_id', 'start_date', 'end_date')
    def _compute_sale_orders(self):
        """Filter Sale Orders theo thời gian và salesperson"""
        for rec in self:
            if not (rec.salesperson_id and rec.start_date and rec.end_date):
                rec.order_ids = False
                continue

            rec.order_ids = self.env['sale.order'].search([
                ('user_id', '=', rec.salesperson_id.id),
                ('date_order', '>=', rec.start_date),
                ('date_order', '<=', rec.end_date),
                ('state', 'in', ['sale', 'done'])
            ])
            return rec.order_ids

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
