# -*- coding: utf-8 -*-
{
    'name': "purchase_request",
    'summary': """
            Zad training first task""",
    'description': """
        Long description of module's purpose
    """,
    'author': "Mohannad Error",
    'website': "https://www.yourcompany.com",
    'category': 'Purchase',
    'version': '0.1',
    'sequence': 1,
    'depends': ['base', 'purchase', 'product', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'wizard/reject_request_views.xml',
        'views/purchase_request_views.xml',
        'views/purchase_request_lines_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',

}
