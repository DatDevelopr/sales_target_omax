# -*- coding: utf-8 -*-
# from odoo import http


# class SalesTargetOmax(http.Controller):
#     @http.route('/sales_target_omax/sales_target_omax', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sales_target_omax/sales_target_omax/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sales_target_omax.listing', {
#             'root': '/sales_target_omax/sales_target_omax',
#             'objects': http.request.env['sales_target_omax.sales_target_omax'].search([]),
#         })

#     @http.route('/sales_target_omax/sales_target_omax/objects/<model("sales_target_omax.sales_target_omax"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sales_target_omax.object', {
#             'object': obj
#         })

