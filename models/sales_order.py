from odoo import models, fields

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
    
class AccountMove(models.Model):
    _inherit = 'account.move'
    sales_target_id = fields.Many2one('sales.target', string="Sales Target")

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
    
class AccountPayment(models.Model):
    _inherit = 'account.payment'

    sales_target_id = fields.Many2one('sales.target', string="Sales Target")