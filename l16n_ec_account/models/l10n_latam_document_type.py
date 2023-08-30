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
from odoo.addons.l10n_ec_base.models.account import INVOICE_TAX_TYPES


class L10NLatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'
