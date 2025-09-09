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

    sales_target_id = fields.Many2one('sales.target', string="Sales Target")

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._assign_sales_target()
        return record
    
    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ["invoice_user_id", "invoice_date", "payment_state"]):
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
            if inv.payment_state == "paid":
                target_point = "invoice_paid"
            else:
                target_point = "invoice_validation"
            target = self.env["sales.target"].search([
                ("salesperson_id", "=", inv.invoice_user_id.id),
                ("start_date", "<=", inv.invoice_date),
                ("end_date", ">=", inv.invoice_date),
                ("state", "=", "open"),
                ("target_point", "=", target_point),
            ], limit=1)

            if target:
                inv.sales_target_id = target.id           
