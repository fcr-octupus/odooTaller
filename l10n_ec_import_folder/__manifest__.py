# -*- coding: utf-8 -*-
{
    'name': "Importaciones",

    'summary': """
        Ingreso de Importaciones en Odoo""",

    'description': """
        Permite el ingreso de Importaciones de pedidos de compras
        dando seguimento desde la compra hasta la liquidación o 
        gasto de envio manteniendo la trazabilidad en modulos como
        compras, facturacion, recepociones, costo de envio y pagos.
    """,

    'author': "OctupusTech S.A",
    'website': "https://www.octupustech.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','stock','stock_landed_costs','account','purchase','account_accountant','contacts'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/import.folder.type.csv',
        'report/stock_landed_report_view.xml',
        'views/purchase_import_views.xml',
        # 'views/account_invoice_views.xml',  #1
        # 'views/purchase_order_import_views.xml',
        'views/account_account_views.xml',
        # 'views/stock_view.xml',
        'views/stock_landed_cost_views.xml',
        # 'views/account_payment_views.xml', #2
        'views/purchase_order_views.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_views.xml',
    ],
}