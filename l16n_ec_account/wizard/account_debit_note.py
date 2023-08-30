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


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    def _prepare_default_values(self, move):
        res = super(AccountDebitNote, self)._prepare_default_values(move)
        if move.country_code == 'EC' and move.l10n_latam_document_type_id:
            if move.l10n_latam_document_type_id.internal_type != 'invoice':
                raise ValidationError(_('You can only apply a debit note for an invoice'))
            if not self.journal_id or self.journal_id.l10n_ec_internal_type != 'debit_note':
                raise ValidationError(_('You must choose a debit note type journal'))
            if not self.reason or not self.reason.strip():
                raise ValidationError(_('You must specify a reason to complete this operation'))
            if move.move_type not in ('out_invoice', 'in_invoice'):
                raise ValidationError(_('This document cannot be reversed with a credit note'))
            res['l10n_ec_modified_move_id'] = move.id
            res['l10n_ec_modified_reason'] = self.reason or res['ref']
            res['journal_id'] = self.journal_id.id
        return res
