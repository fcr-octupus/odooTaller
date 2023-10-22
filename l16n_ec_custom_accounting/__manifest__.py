
{
    'name': '[Contabilidad] Guía de Remisión',
    'version': '0.0.0.1',
    'category': "Accounting/Localization",
    'description': '[Ecuador] Remission guide support', 
    'author': 'OctupusTech S.A',
    'depends': ['base','account_accountant','l10n_ec_extended','account', 'contacts', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/l16n_ec_custom_accounting.xml',
        'data/template.xml',
    ],

    "installable": True,
    "license": "OPL-1"
}
