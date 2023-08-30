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


class L10NEcEmissionPoint(models.Model):
    _inherit = 'l10n_ec.emission.point'

    def _has_moves(self):
        journals = self.env['account.journal'].search([('l10n_ec_emission_point_id', '=', self.id)])
        moves = self.env['account.move'].search([('journal_id', 'in', journals.ids), ('state', '=', 'posted')], limit=1)
        if moves:
            return True
        return super(L10NEcEmissionPoint, self)._has_moves()
