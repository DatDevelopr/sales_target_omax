# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    sales_team_target_id = fields.Many2one('sales.team.target', string="Sales Team Target")

    @api.model
    def create(self, vals):
        inv = super(AccountMove, self).create(vals)
        inv._assign_sales_team_target()
        return inv

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        if any(f in vals for f in ('invoice_date', 'invoice_user_id', 'payment_state', 'invoice_origin', 'state')):
            for rec in self:
                rec._assign_sales_team_target()
        return res

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for inv in self:
            inv._assign_sales_team_target()
        return res

    def _assign_sales_team_target(self):
        """Gán sales_team_target dựa trên invoice_origin -> sale.order -> team_id"""
        for inv in self:
            assigned = False
            if inv.invoice_origin:
                so = self.env['sale.order'].search([('name', '=', inv.invoice_origin)], limit=1)
                if so and so.team_id:
                    point = 'invoice_paid' if inv.payment_state == 'paid' else 'invoice_validation'
                    target = self.env['sales.team.target'].search([
                        ('team_id', '=', so.team_id.id),
                        ('state', '=', 'open'),
                        ('start_date', '<=', inv.invoice_date),
                        ('end_date', '>=', inv.invoice_date),
                        ('target_point', '=', point),
                    ], limit=1)
                    if target:
                        inv.sales_team_target_id = target.id
                        assigned = True
            if not assigned:
                inv.sales_team_target_id = False


class SaleOrder(models.Model):
    _inherit = "sale.order"

    sales_team_target_id = fields.Many2one('sales.team.target', string="Sales Team Target")

    def action_confirm(self, *args, **kwargs):
        res = super(SaleOrder, self).action_confirm(*args, **kwargs)
        for order in self:
            # Gán target nếu chưa có
            if not order.sales_team_target_id and order.team_id and order.date_order:
                target = self.env['sales.team.target'].search([
                    ('team_id', '=', order.team_id.id),
                    ('state', '=', 'open'),
                    ('start_date', '<=', order.date_order),
                    ('end_date', '>=', order.date_order),
                    ('target_point', '=', 'so_confirm'),
                ], limit=1)
                if target:
                    order.sales_team_target_id = target.id

            # Cập nhật achievement
            self.env['sales.team.target'].sudo()._update_achievement(order, 'so_confirm')
        return res


    @api.model
    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            # Gán target nếu chưa có
            if not order.sales_team_target_id and order.team_id and order.date_order:
                target = self.env['sales.team.target'].search([
                    ('team_id', '=', order.team_id.id),
                    ('state', '=', 'open'),
                    ('start_date', '<=', order.date_order),
                    ('end_date', '>=', order.date_order),
                    ('target_point', '=', 'so_confirm'),
                ], limit=1)
                if target:
                    order.sales_team_target_id = target.id

            # Cập nhật achievement
            self.env['sales.team.target'].sudo()._update_achievement(order, 'so_confirm')
        return res
