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
from odoo.exceptions import ValidationError, UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ec_refund_product_id = fields.Many2one(related='company_id.l10n_ec_refund_product_id', readonly=False)
    l10n_ec_property_account_receivable_id = fields.Many2one(related='company_id.l10n_ec_property_account_receivable_id', readonly=False)
    l10n_ec_property_account_payable_id = fields.Many2one(related='company_id.l10n_ec_property_account_payable_id', readonly=False)
  
    module_l10n_ec_edi = fields.Boolean('Electronic invoicing (EC)')
    module_l10n_ec_reports = fields.Boolean('Fiscal reports (EC)')
