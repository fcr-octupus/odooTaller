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


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def get_paperformat(self):
        #  Ugly hacks in Ecuadorian Invoices
        if self.report_name in ('account.report_invoice', 'account.report_invoice_with_payments') and self.env.company.country_code == 'EC':
            return self.env.ref('l10n_ec_account.invoice_paperformat')
        return super(IrActionsReport, self).get_paperformat()
