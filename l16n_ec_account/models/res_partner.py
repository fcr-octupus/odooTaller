#######################################################################################
#
#    ALZATI S.A.
#    Copyright (C) 2020-TODAY ALZATI S.A. (https://www.alzatisolutions.com)
#    Author: Carlos Rodriguez Trujillo | @crrodriguezt1
#
#    See LICENSE file for full copyright and licensing details.
#
#######################################################################################

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_ec_related_party = fields.Boolean('Related party?', company_dependent=True)
    l10n_ec_payment_method_id = fields.Many2one('l10n_ec.ats.payment.method', 'Default payment method (EC)',
                                                company_dependent=True)
    l10n_ec_payment_method_supplier_id = fields.Many2one('l10n_ec.ats.payment.method',
                                                         'Default payment method for suppliers (EC)',
                                                         company_dependent=True)
