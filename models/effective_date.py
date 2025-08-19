from odoo import models, fields, api

class EffectiveDate(models.Model):
    _inherit = "sale.order"

    effective_date = fields.Date(string="Effective Date")