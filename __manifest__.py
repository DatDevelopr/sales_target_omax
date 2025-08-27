# -*- coding: utf-8 -*-
{
    'name': "sales_target_omax",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale_management', 'mail'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'security/record_rules.xml',
        'data/mail_template.xml',
        
        'views/menu.xml',
        'views/sales_target_views.xml',

        'data/ir_sequence.xml',
        'views/sales_team_target_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

