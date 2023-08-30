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


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    # Fiscal basic fields
    l10n_ec_serial_entity = fields.Char('Serial entity', compute='_compute_l10n_ec_document', store=True,
                                        readonly=False, size=3, copy=True)
    l10n_ec_emission_point = fields.Char('Emission point', compute='_compute_l10n_ec_document', store=True,
                                         readonly=False, size=3, copy=True)
    l10n_ec_auth_number = fields.Char('Authorization number', compute='_compute_l10n_ec_document', store=True,
                                      readonly=False, copy=False, size=49)
    l10n_ec_electronic = fields.Boolean('Is Electronic?', compute='_compute_l10n_ec_document', store=True,
                                        readonly=False)
    l10n_ec_internal = fields.Boolean('Is Internal?', compute='_compute_l10n_ec_document', store=True, readonly=False)
    country_code = fields.Char(compute='_compute_country_code')

    @api.depends('move_ids')
    def _compute_country_code(self):
        for rec in self:
            codes = rec.move_ids.mapped('company_id.country_code')
            rec.country_code = codes and codes[0] or False

    @api.depends('journal_id')
    def _compute_l10n_ec_document(self):
        for rec in self:
            rec.l10n_ec_serial_entity = rec.journal_id.l10n_ec_emission_point_id.branch_code
            rec.l10n_ec_emission_point = rec.journal_id.l10n_ec_emission_point_id.code
            rec.l10n_ec_auth_number = rec.journal_id.l10n_ec_auth_number
            rec.l10n_ec_electronic = rec.journal_id.l10n_ec_electronic
            rec.l10n_ec_internal = rec.journal_id.l10n_ec_internal

    def _prepare_default_reversal(self, move):
        res = super(AccountMoveReversal, self)._prepare_default_reversal(move)
        if move.country_code == 'EC' and move.l10n_latam_document_type_id:
            if move.l10n_latam_document_type_id.internal_type != 'invoice':
                raise ValidationError(_('You can only apply a credit note for an invoice'))
            if not self.journal_id or self.journal_id.l10n_ec_internal_type != 'credit_note':
                raise ValidationError(_('You must choose a credit note type journal'))
            if move.l10n_ec_internal != self.journal_id.l10n_ec_internal:
                if move.l10n_ec_internal:
                    raise ValidationError(_('You cannot reverse an internal move with an external journal'))
                raise ValidationError(_('You cannot reverse an external move with an internal journal'))
            if not self.reason or not self.reason.strip():
                raise ValidationError(_('You must specify a reason to complete this operation'))
            if move.move_type not in ('out_invoice', 'in_invoice'):
                raise ValidationError(_('This document cannot be reversed with a credit note'))
            res['l10n_ec_modified_move_id'] = move.id
            res['l10n_ec_modified_reason'] = self.reason
            res['journal_id'] = self.journal_id.id
            res['move_type'] = 'out_refund' if move.move_type == 'out_invoice' else 'in_refund'
            res['l10n_ec_serial_entity'] = self.l10n_ec_serial_entity
            res['l10n_ec_emission_point'] = self.l10n_ec_emission_point
            res['l10n_ec_auth_number'] = self.l10n_ec_auth_number
            res['l10n_ec_electronic'] = self.l10n_ec_electronic
            res['l10n_ec_internal'] = self.l10n_ec_internal
            res['l10n_ec_require_payment'] = False
        return res

    @api.depends('move_ids', 'journal_id')
    def _compute_document_type(self):
        ec_moves = self.filtered(lambda x: 'EC' in x.move_ids.mapped('country_code'))
        ec_moves.l10n_latam_available_document_type_ids = False
        ec_moves.l10n_latam_document_type_id = False
        ec_moves.l10n_latam_use_documents = False
        for record in ec_moves:
            if len(record.move_ids) > 1:
                move_ids_use_document = record.move_ids._origin.filtered(lambda move: move.l10n_latam_use_documents)
                if move_ids_use_document:
                    raise UserError(_(
                        'You can only reverse documents with legal invoicing documents from Latin America one at a time.\nProblematic documents: %s') % ", ".join(
                        move_ids_use_document.mapped('name')))
            else:
                record.l10n_latam_use_documents = record.move_ids.journal_id.l10n_latam_use_documents
            if record.l10n_latam_use_documents:
                journal = record.journal_id
                if not journal:
                    journal = self.env['account.journal'].search([('l10n_latam_use_documents', '=', True),
                                                                  ('l10n_ec_internal_type', '=', 'credit_note'),
                                                                  ('l10n_ec_internal', '=',
                                                                   record.move_ids.l10n_ec_internal)], limit=1)
                refund = record.env['account.move'].new({
                    'move_type': record._reverse_type_map(record.move_ids.move_type),
                    'journal_id': journal.id,
                    'partner_id': record.move_ids.partner_id.id,
                    'company_id': record.move_ids.company_id.id,
                })
                record.l10n_latam_document_type_id = refund.l10n_latam_document_type_id
                record.l10n_latam_available_document_type_ids = refund.l10n_latam_available_document_type_ids
        super(AccountMoveReversal, self - ec_moves)._compute_document_type()
