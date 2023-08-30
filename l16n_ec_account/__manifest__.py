{
    'name': 'Ecuador - Accounting',
    'version': '16',
    'category': 'OctupusTech/Accounting/Localizations',
    'description': """Accounting chart and localization for Ecuador""",
    'author': 'OctupusTech S.A',
    'website': "https://www.octupustech.com/",
    'depends': [
        'l10n_ec_base',
        'web'
    ],
    'data': [
        'security/ir.model.access.csv',

        'data/data.xml',

        'views/assets.xml',
        'views/res_company.xml',
        'views/res_partner.xml',
        'views/account_move.xml',
        'views/account_journal.xml',
        'views/res_config_settings.xml',

        'views/report_invoice.xml',

        'wizard/account_move_reversal.xml',
    ],
    'qweb': ['static/src/xml/qweb.xml'],
}
