from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = "sale.order"

    sales_target_id = fields.Many2one('sales.team.target', string="Sales Target")