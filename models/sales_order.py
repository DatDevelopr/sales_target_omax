from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = "sale.order"

    sales_target_id = fields.Many2one(
        'sales.target',
        string="Sales Target"
    )
    sales_team_target_id = fields.Many2one('sales.team.target', string="Sales Team Target")

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            self.env['sales.target'].sudo()._update_achievement(order, 'so_confirm')
        return res

    @api.model
    def create(self, vals):

        order = super(SaleOrder, self).create(vals)
        
        salesperson = order.user_id
        order_date = order.date_order or fields.Datetime.now()
        
        if salesperson and order_date:
            
            target = self.env["sales.target"].search([
                ("salesperson_id", "=", salesperson.id),
                ("start_date", "<=", order_date.date()),
                ("end_date", ">=", order_date.date()),
                ("state", "=", "open"),
                ("target_point", "=", "so_confirm"),
            ], limit=1)
            
            if target:
                order.sales_target_id = target.id
        return order 

class AccountMove(models.Model):
    _inherit = 'account.move'

    sales_target_id = fields.Many2one('sales.target', string="Sales Target", ondelete="set null")

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._assign_sales_target()
        return record
    
    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ["invoice_user_id", "invoice_date"]):
            for rec in self:
                rec._assign_sales_target()
        return res
    
    def action_post(self):
        res = super().action_post()
        for inv in self:
            self.env['sales.target'].sudo()._update_achievement(inv, 'invoice_validation')
        return res

    def _reconcile_paid(self):
        res = super()._reconcile_paid()
        for inv in self:
            self.env['sales.target'].sudo()._update_achievement(inv, 'invoice_paid')
        return res
    
    def _assign_sales_target(self):
        for inv in self:
            if not inv.invoice_user_id or not inv.invoice_date:
                continue

            target = self.env["sales.target"].search([
                ("salesperson_id", "=", inv.invoice_user_id.id),
                ("start_date", "<=", inv.invoice_date),
                ("end_date", ">=", inv.invoice_date),
                ("state", "=", "open"),
                ("target_point", "in", ["invoice_validation", "invoice_paid"]),
            ], limit=1)

            if target:
                inv.sales_target_id = target.id           
    
class AccountPayment(models.Model):
    _inherit = 'account.payment'

    sales_target_id = fields.Many2one('sales.target', string="Sales Target")

    def action_post(self):
        res = super().action_post()
        for pay in self:
            pay._assign_sales_target()
            # Nếu payment liên quan đến target "invoice_paid"
            if pay.sales_target_id and pay.sales_target_id.target_point == "invoice_paid":
                self.env['sales.target'].sudo()._update_achievement(pay, 'invoice_paid')
        return res

    def _assign_sales_target(self):
        """Tìm sales.target phù hợp cho Payment"""
        for pay in self:
            salesperson = pay.create_uid  # mặc định lấy user tạo payment
            if not salesperson or not pay.date:
                continue

            target = self.env["sales.target"].search([
                ("salesperson_id", "=", salesperson.id),
                ("start_date", "<=", pay.date),
                ("end_date", ">=", pay.date),
                ("state", "=", "open"),
                ("target_point", "=", "invoice_paid"),
            ], limit=1)

            if target:
                pay.sales_target_id = target.id