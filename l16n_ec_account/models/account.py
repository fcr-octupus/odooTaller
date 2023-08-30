#######################################################################################
#
#    ALZATI S.A.
#    Copyright (C) 2020-TODAY ALZATI S.A. (https://www.alzatisolutions.com)
#    Author: Carlos Rodriguez Trujillo | @crrodriguezt1
#
#    See LICENSE file for full copyright and licensing details.
#
#######################################################################################
import re

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.l10n_ec_base.util.helper import format_serial, format_emission_point
from odoo.addons.l10n_ec_base.models.l10n_ec import INTERNAL_TYPE_OPTIONS as INTERNAL_DOCUMENT_TYPES


class AccountJournal(models.Model):
    _name = 'account.journal'
    _inherit = ['account.journal', 'l10n_ec.document.mixin']

    l10n_ec_auth_number = fields.Char('Authorization number')
    l10n_ec_internal = fields.Boolean('Is internal?')
    l10n_ec_electronic = fields.Boolean('Is Electronic?')
    l10n_ec_auto_sequence = fields.Boolean('Auto sequence?')
    l10n_ec_document_ro = fields.Boolean('Document fields readonly? (EC)', compute='_compute_l10n_ec_document_ro')
    l10n_ec_display_auth = fields.Char('Authorization', compute='_compute_l10n_ec_display_auth')
    l10n_ec_internal_type = fields.Selection(related='l10n_ec_document_type_id.internal_type', string='Internal type')
    l10n_ec_document_type_id = fields.Many2one('l10n_ec.document.type', 'Document type',
                                               compute='_compute_l10n_ec_document_type', store=True, readonly=False)
    l10n_ec_branch_id = fields.Many2one('l10n_ec.branch', 'Branch', related='l10n_ec_emission_point_id.branch_id',
                                        store=True)
    l10n_ec_emission_point_id = fields.Many2one('l10n_ec.emission.point', 'Emission point (EC)',
                                                domain="[('company_id', '=', company_id), ('selectable', '=', True)]")
    l10n_ec_payment_method_id = fields.Many2one('l10n_ec.ats.payment.method', 'Default payment method (EC)')

    @api.depends('type')
    def _compute_l10n_ec_document_ro(self):
        for rec in self:
            rec.l10n_ec_document_ro = self.env['account.move'].search_count(
                [('journal_id', '=', rec.id), ('state', '=', 'posted')]) > 0

    @api.depends('type')
    def _compute_l10n_ec_document_type(self):
        t_object = self.env['l10n_ec.document.type']
        all_types = [k for k, v in INTERNAL_DOCUMENT_TYPES]
        for rec in self:
            types = list(all_types)
            if rec.type in ('sale', 'purchase'):
                if rec.type == 'sale':
                    types.remove('purchase_liq')
                rec.l10n_ec_document_type_id = t_object.search([('journal_type', 'in', ['all', rec.type]),
                                                                ('internal_type', 'in', types)], limit=1)
            else:
                rec.l10n_ec_document_type_id = t_object

    @api.depends('l10n_latam_use_documents', 'l10n_ec_internal', 'type', 'l10n_ec_emission_point_id',
                 'l10n_ec_auth_number')
    def _compute_l10n_ec_display_auth(self):
        for rec in self:
            prefix = False
            if rec.l10n_latam_use_documents and rec.type in ('sale', 'purchase') and rec.l10n_ec_internal:
                ep = rec.l10n_ec_emission_point_id
                prefix = format_emission_point(ep.branch_code, ep.code)
                if rec.l10n_ec_electronic:
                    prefix = _('%s (E)', prefix)
                elif rec.l10n_ec_auth_number:
                    prefix = _('%s AUT:%s', prefix, rec.l10n_ec_auth_number)
            rec.l10n_ec_display_auth = prefix

    @api.onchange('l10n_ec_internal', 'type')
    def _onchange_l10n_ec_internal(self):
        self.l10n_ec_document_type_id = self.l10n_ec_emission_point_id = self.l10n_ec_auth_number = False
        self.l10n_ec_auto_sequence = self.l10n_ec_internal

    @api.onchange('l10n_ec_electronic')
    def _onchange_l10n_ec_electronic(self):
        self.l10n_ec_auth_number = False
        self.l10n_ec_auto_sequence = True

    @api.onchange('type')
    def _onchange_type(self):
        res = super(AccountJournal, self)._onchange_type()
        self.l10n_ec_document_type_id = False
        return res

    @api.constrains('l10n_ec_electronic', 'l10n_ec_auth_number')
    def _check_l10n_ec_auth_number(self):
        super(AccountJournal, self)._check_l10n_ec_auth_number()

    def name_get(self):
        _map = {j.id: j for j in self}
        res = []
        for _id, name in super(AccountJournal, self).name_get():
            if _map[_id].l10n_ec_display_auth:
                name = '%s :: %s' % (name, _map[_id].l10n_ec_display_auth)
            res.append((_id, name))
        return res
