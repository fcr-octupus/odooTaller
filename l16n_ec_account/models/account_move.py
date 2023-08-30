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
from collections import defaultdict
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_is_zero

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression
from odoo.addons.l10n_ec_base.util.helper import format_serial, format_document_sequence, mod11
from odoo.addons.l10n_ec_base.models.account import WITHHOLDING_TAX_TYPES


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'l10n_ec.document.mixin']

    l10n_ec_related_party = fields.Boolean('Related party?', compute='_compute_l10n_ec_related_party', store=True,
                                           readonly=False, copy=False)
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
    l10n_ec_require_payment = fields.Boolean('Require payment details?', compute='_compute_l10n_ec_require_payment',
                                             store=True, readonly=False)
    # credit / debit notes
    l10n_ec_modified_reason = fields.Char('Modification reason', copy=False)
    l10n_ec_modified_move_id = fields.Many2one('account.move', 'Modified document', store=True, readonly=False,
                                               copy=False, check_company=True)

    # ATS fields
    l10n_ec_tx_id = fields.Many2one('l10n_ec.ats.transaction', 'Transaction type',
                                    compute='_compute_l10n_ec_transaction', store=True, readonly=False)
    l10n_ec_support_id = fields.Many2one('l10n_ec.ats.support', 'Support', compute='_compute_l10n_ec_support',
                                         store=True, readonly=False)
    l10n_ec_payment_method_id = fields.Many2one('l10n_ec.ats.payment.method', 'Default payment method', store=True,
                                                compute='_compute_l10n_ec_payment', inverse='_inverse_l10n_ec_payment')
    l10n_ec_payment_ids = fields.One2many('l10n_ec.ats.payment.line', 'move_id', 'Payments',
                                          compute='_compute_l10n_ec_payment_lines', store=True, readonly=False)
    l10n_ec_refund_line_ids = fields.One2many('l10n_ec.refund.line', 'move_id', 'Refund lines')
    l10n_ec_3rd_party_ids = fields.One2many('l10n_ec.3rd.party', 'move_id', '3rd parties')

    # Technical fields
    l10n_ec_tx_code = fields.Char('Transaction type code (EC)', related='l10n_ec_tx_id.code')
    l10n_ec_tx_type_code = fields.Char('Transaction code (EC)', related='l10n_ec_tx_id.type_code')
    l10n_ec_use_support = fields.Boolean('Use document support?', compute='_compute_l10n_ec_use_support')
    l10n_ec_vat_bases = fields.Binary('VAT Bases', compute='_compute_l10n_ec_vat_bases')
    l10n_ec_available_tx_ids = fields.Many2many('l10n_ec.ats.transaction', compute='_compute_l10n_ec_available_tx_ids')
    l10n_ec_available_support_ids = fields.Many2many('l10n_ec.ats.support',
                                                     compute='_compute_l10n_ec_available_support_ids')
    l10n_latam_internal_type = fields.Selection(related='l10n_latam_document_type_id.internal_type',
                                                string='LATAM internal type')

    # COMEX fields
    l10n_ec_src_port = fields.Char('Source port (comex)')
    l10n_ec_dst_port = fields.Char('Destination port (comex)')
    l10n_ec_export_correlative = fields.Char('Correlative (comex)')
    l10n_ec_export_transport = fields.Char('Transport number (comex)')
    l10n_ec_export_date = fields.Date('Date (comex)')
    l10n_ec_export_amount = fields.Monetary('Amount (comex)')
    l10n_ec_foreign_income_tax_ok = fields.Boolean('Foreign income taxed?')
    l10n_ec_foreign_income_tax = fields.Monetary('Foreign income tax')
    l10n_ec_foreign_double_taxation = fields.Boolean('Apply double taxation?')
    l10n_ec_foreign_legal_regulations = fields.Boolean('Apply legal regulations?')
    l10n_ec_fiscal_regime_id = fields.Many2one('l10n_ec.ats.fiscal.regime', 'Fiscal regime')
    l10n_ec_country_id = fields.Many2one('l10n_ec.ats.country', 'Country code')
    l10n_ec_incoterm_untaxed_id = fields.Many2one('account.incoterms', 'Untaxed incoterm')
    l10n_ec_dst_country_id = fields.Many2one('l10n_ec.ats.country', 'Destination country (comex)')
    l10n_ec_acq_country_id = fields.Many2one('l10n_ec.ats.country', 'Acquirer country (comex)')
    l10n_ec_export_type_id = fields.Many2one('l10n_ec.ats.export.type', 'Export type (comex)')
    l10n_ec_foreign_income_id = fields.Many2one('l10n_ec.ats.foreign.income', 'Foreign income (comex)')
    l10n_ec_export_district_id = fields.Many2one('l10n_ec.ats.district', 'District (comex)')
    l10n_ec_export_regime_id = fields.Many2one('l10n_ec.ats.regime', 'Regime (comex)')

    # Waybill fields
    l10n_ec_waybill_ok = fields.Boolean('Is a waybill')
    l10n_ec_waybill_src = fields.Char('Waybill source address', size=300)
    l10n_ec_waybill_dst = fields.Char('Waybill destination address', size=300)
    l10n_ec_waybill_starts = fields.Date('Waybill starts at')
    l10n_ec_waybill_ends = fields.Date('Waybill ends at')
    l10n_ec_waybill_partner_id = fields.Many2one('res.partner', 'Waybill driver')
    l10n_ec_waybill_plate = fields.Char('Waybill plate')
    l10n_ec_waybill_dst_ids = fields.One2many('l10n_ec.waybill.destination', 'move_id', 'Destinations', copy=True)

    def _compute_invoice_taxes_by_group(self):
        super(AccountMove, self)._compute_invoice_taxes_by_group()
        group_ids = self.env['account.tax.group'].search([('l10n_ec_type', 'in', WITHHOLDING_TAX_TYPES)]).ids
        for rec in self:
            rec.amount_by_group = [g for g in rec.amount_by_group if g[6] not in group_ids]

    @api.model
    def _get_default_invoice_date(self):
        if self.env.company.country_code == 'EC':
            return fields.Date.context_today(self) if self._context.get('default_move_type', 'entry') in (
                    self.get_purchase_types(include_receipts=True) + self.get_sale_types(
                include_receipts=True)) else False
        return super(AccountMove, self)._get_default_invoice_date()

    @api.depends('partner_id')
    def _compute_l10n_ec_related_party(self):
        for rec in self:
            rec.l10n_ec_related_party = rec.partner_id.commercial_partner_id.l10n_ec_related_party

    @api.depends('amount_by_group')
    def _compute_l10n_ec_vat_bases(self):
        groups = set()
        for rec in self:
            for line in rec.amount_by_group:
                groups.add(line[-1])
        groups = self.env['account.tax.group'].search([('l10n_ec_type', 'in', ['vat', 'vat_0', 'vat_not', 'vat_ex']),
                                                       ('id', 'in', list(groups))]).ids
        for rec in self:
            all_groups = rec.amount_by_group or []
            res = False
            if all_groups:
                res = [(_('Base of %s', g[0]), g[2], g[4], g[6]) for g in all_groups if g[-1] in groups]
            rec.l10n_ec_vat_bases = res or []

    @api.depends('amount_total')
    def _compute_l10n_ec_payment_lines(self):
        self._inverse_l10n_ec_payment()

    @api.depends('name')
    def _compute_l10n_latam_document_number(self):
        l10n_ec_moves = self.filtered(
            lambda x: x.l10n_latam_document_type_id and x.name != '/' and x.country_code == 'EC')
        for rec in l10n_ec_moves:
            name = rec.name
            doc_code_prefix = rec.l10n_latam_document_type_id.doc_code_prefix
            if doc_code_prefix and name:
                name = name.split(" ", 1)[-1]
            rec.l10n_latam_document_number = rec.l10n_latam_document_type_id._format_document_number(
                name.split('-', 2)[-1])
        super(AccountMove, self - l10n_ec_moves)._compute_l10n_latam_document_number()

    @api.onchange('l10n_latam_document_type_id', 'l10n_latam_document_number')
    def _inverse_l10n_latam_document_number(self):
        l10n_ec_moves = self.filtered(
            lambda x: x.l10n_latam_document_type_id and x.l10n_latam_document_type_id.country_id.code == 'EC' and (
                    x.l10n_latam_manual_document_number or not x.highest_name))
        for rec in l10n_ec_moves:
            if not rec.l10n_latam_document_number:
                rec.name = '/'
            else:
                l10n_latam_document_number = rec.l10n_latam_document_type_id._format_document_number(
                    rec.l10n_latam_document_number)
                if rec.l10n_latam_document_number != l10n_latam_document_number:
                    rec.l10n_latam_document_number = l10n_latam_document_number
                rec.name = rec._get_formatted_sequence(l10n_latam_document_number)
        super(AccountMove, self - l10n_ec_moves)._inverse_l10n_latam_document_number()

    @api.depends('journal_id', 'partner_id', 'l10n_ec_payment_ids.payment_method_id')
    def _compute_l10n_ec_payment(self):
        draft_docs = self.filtered(lambda x: x.state == 'draft')
        pm = self.env['l10n_ec.ats.payment.method'].search([], limit=1) if draft_docs else False
        for rec in draft_docs:
            if rec.state == 'draft':
                if rec.l10n_ec_require_payment:
                    if rec.l10n_ec_payment_ids:
                        current_pm = rec.l10n_ec_payment_ids.mapped('payment_method_id')[:1]
                    else:
                        current_pm = rec.l10n_ec_payment_method_id
                    payment_method = current_pm or rec.journal_id.l10n_ec_payment_method_id or pm
                else:
                    payment_method = False
                rec.l10n_ec_payment_method_id = payment_method

    def _inverse_l10n_ec_payment(self):
        for rec in self:
            rec.l10n_ec_payment_ids = rec._prepare_l10n_ec_payment_lines(
                rec.amount_total, rec.l10n_ec_payment_method_id) if rec.l10n_ec_payment_method_id else False

    @api.onchange('l10n_ec_payment_method_id')
    def _onchange_l10n_ec_payment(self):
        self._inverse_l10n_ec_payment()

    @api.depends('l10n_ec_internal', 'l10n_latam_document_type_id')
    def _compute_l10n_ec_require_payment(self):
        for rec in self:
            rec.l10n_ec_require_payment = rec.l10n_latam_document_type_id.internal_type in (
                'invoice', 'debit_note', 'purchase_liq')

    @api.depends('l10n_latam_document_type_id', 'l10n_ec_internal')
    def _compute_l10n_ec_available_support_ids(self):
        ec_docs = self.filtered(lambda x: x.l10n_latam_document_type_id and
                                          x.move_type in ('in_invoice', 'in_refund') and (
                                                  not x.l10n_ec_internal or
                                                  x.l10n_latam_document_type_id.internal_type == 'purchase_liq'))
        for rec in ec_docs:
            rec.l10n_ec_available_support_ids = rec.l10n_latam_document_type_id.l10n_ec_support_ids._origin
        (self - ec_docs).l10n_ec_available_support_ids = False

    @api.depends('journal_id', 'partner_id', 'company_id')
    def _compute_l10n_ec_available_tx_ids(self):
        t_object = self.env['l10n_ec.ats.transaction']
        docs = self.filtered(lambda x: x.journal_id and x.l10n_latam_use_documents and x.partner_id)
        for rec in docs:
            rec.l10n_ec_available_tx_ids = t_object.search(rec._get_l10n_ec_tx_domain())
        (self - docs).l10n_ec_available_tx_ids = False

    @api.depends('l10n_latam_available_document_type_ids', 'debit_origin_id')
    def _compute_l10n_latam_document_type(self):
        ec_docs = self.filtered(lambda x: x.state == 'draft' and x.country_code == 'EC')
        for rec in ec_docs:
            debit_note = rec.debit_origin_id
            document_types = rec.l10n_latam_available_document_type_ids._origin
            document_types = debit_note and document_types.filtered(
                lambda x: x.internal_type == 'debit_note') or document_types
            if not rec.l10n_latam_document_type_id in document_types:
                rec.l10n_latam_document_type_id = document_types[:1]
        super(AccountMove, self - ec_docs)._compute_l10n_latam_document_type()

    @api.depends('l10n_ec_available_support_ids')
    def _compute_l10n_ec_support(self):
        for rec in self:
            support = rec.l10n_ec_available_support_ids._origin
            if rec.state == 'draft' and not (rec.l10n_ec_support_id and rec.l10n_ec_support_id in support):
                rec.l10n_ec_support_id = support[:1].id

    @api.depends('l10n_ec_available_support_ids')
    def _compute_l10n_ec_use_support(self):
        for rec in self:
            rec.l10n_ec_use_support = not not rec.l10n_ec_available_support_ids._origin

    @api.depends('l10n_ec_available_tx_ids')
    def _compute_l10n_ec_transaction(self):
        draft_docs = self.filtered(lambda x: x.state == 'draft')
        for rec in draft_docs:
            document_types = rec.l10n_ec_available_tx_ids._origin
            if not (rec.l10n_ec_tx_id and rec.l10n_ec_tx_id in document_types):
                rec.l10n_ec_tx_id = document_types[:1].id
                rec._compute_l10n_latam_available_document_types()

    @api.depends('journal_id')
    def _compute_l10n_ec_document(self):
        for rec in self:
            se = ep = el = an = False
            rec.l10n_ec_internal = rec.journal_id.l10n_ec_internal
            if rec.l10n_ec_internal:
                se = rec.journal_id.l10n_ec_emission_point_id.branch_code
                ep = rec.journal_id.l10n_ec_emission_point_id.code
                el = rec.journal_id.l10n_ec_electronic
                if not el:
                    an = rec.journal_id.l10n_ec_auth_number
            rec.l10n_ec_electronic = el if not rec.l10n_ec_electronic else rec.l10n_ec_electronic
            rec.l10n_ec_serial_entity = se if not rec.l10n_ec_serial_entity else rec.l10n_ec_serial_entity
            rec.l10n_ec_emission_point = ep if not rec.l10n_ec_emission_point else rec.l10n_ec_emission_point
            rec.l10n_ec_auth_number = an if not rec.l10n_ec_auth_number else rec.l10n_ec_auth_number

    @api.onchange('l10n_ec_serial_entity', 'l10n_ec_emission_point')
    def _onchange_l10n_ec_emission_point(self):
        for rec in self:
            if rec.country_code == 'EC':
                rec.l10n_ec_serial_entity = rec.l10n_ec_serial_entity and format_serial(rec.l10n_ec_serial_entity)
                rec.l10n_ec_emission_point = rec.l10n_ec_emission_point and format_serial(rec.l10n_ec_emission_point)
                if rec.l10n_latam_document_number:
                    rec._inverse_l10n_latam_document_number()

    @api.onchange('l10n_ec_tx_id')
    def _onchange_l10n_ec_tx_id(self):
        self._compute_l10n_latam_available_document_types()

    @api.onchange('l10n_ec_auth_number')
    def _onchange_l10n_ec_auth_number(self):
        p_object = self.env['res.partner']
        data = self._parse_access_key(self.l10n_ec_auth_number or '')
        if data and self.l10n_ec_electronic and not self.l10n_ec_internal:
            doc_type, serial_entity, emission_point, document_number, identification, document_date, environment, \
                emission_type = data
            self.partner_id = p_object.search([('vat', '=', identification)], limit=1) or self.partner_id
            self._onchange_partner_id()
            self.l10n_ec_serial_entity = serial_entity
            self.l10n_ec_emission_point = emission_point
            self.l10n_latam_document_number = document_number

    @api.onchange('l10n_ec_refund_line_ids')
    def _onchange_l10n_ec_refund_lines(self):
        l_object = self.env['account.move.line']
        if self.l10n_latam_document_type_code == '41':
            product = self.company_id.l10n_ec_refund_product_id
            if product:
                line = l_object.with_context(default_move_id=self.id).new({'product_id': product.id})
                line._onchange_product_id()
                line.price_unit = sum(r for r in self.l10n_ec_refund_line_ids.mapped('amount_total'))
                line._onchange_price_subtotal()
                self.invoice_line_ids = line
            self._compute_l10n_ec_payment()
            self._inverse_l10n_ec_payment()

    @api.constrains('l10n_ec_waybill_ok', 'l10n_ec_waybill_dst_ids')
    def _check_l10n_ec_waybill(self):
        for rec in self:
            if rec.l10n_ec_waybill_ok and not rec.l10n_ec_waybill_dst_ids:
                raise ValidationError(_('You are not specified any destination path in the waybill'))

    @api.constrains('l10n_ec_auth_number', 'l10n_ec_electronic')
    def _check_l10n_ec_auth_number(self):
        super(AccountMove, self)._check_l10n_ec_auth_number()

    @api.constrains('l10n_ec_emission_point', 'l10n_ec_serial_entity')
    def _check_l10n_ec_emission_point(self):
        super(AccountMove, self)._check_l10n_ec_emission_point()

    @api.constrains('l10n_ec_waybill_ok', 'l10n_ec_waybill_dst_ids')
    def _check_l10n_ec_waybill(self):
        for rec in self:
            if rec.l10n_ec_waybill_ok and not rec.l10n_ec_waybill_dst_ids:
                raise ValidationError(_('You are not specified any destination path in the waybill'))

    def _is_manual_document_number(self, journal):
        if journal.country_code == 'EC':
            return not (journal.l10n_ec_internal and journal.l10n_ec_auto_sequence)
        return super(AccountMove, self)._is_manual_document_number(journal)

    def _is_valid_access_key(self, access_key):
        # self.ensure_one()
        doc_codes = ('01', '03', '04', '05', '06', '07')
        access_key = access_key or ''
        if re.match('^[0-9]{49}$', access_key):
            return str(mod11(access_key[:48])) == access_key[48] and access_key[8:10] in doc_codes
        return False

    def _get_l10n_latam_documents_domain(self):
        if self.company_id.country_code == 'EC':
            internal_type = self.journal_id.l10n_ec_document_type_id.internal_type
            if self.move_type in ['out_refund', 'in_refund'] and internal_type == 'credit_note':
                internal_types = ['credit_note']
            else:
                internal_types = [internal_type]
            return [('internal_type', 'in', internal_types), ('country_id', '=', self.company_id.country_id.id),
                    ('l10n_ec_transaction_ids', 'in', self.l10n_ec_tx_id.ids)]
        return super(AccountMove, self)._get_l10n_latam_documents_domain()

    def _get_l10n_ec_tx_codes(self):
        if self.journal_id.type == 'sale':
            return ['02', '04']
        if self.journal_id.type == 'purchase':
            return ['01']
        return False

    def _get_l10n_ec_identification_type(self):
        it_code = False
        if self.partner_id.l10n_latam_identification_type_id:
            it_code = self.partner_id.l10n_latam_identification_type_id.l10n_ec_type or 'P'
            if it_code == 'X':
                it_code = 'P'
        return it_code

    def _get_l10n_ec_tx_domain(self):
        return [('type_code', 'in', self._get_l10n_ec_tx_codes()),
                ('identification_type', '=', self._get_l10n_ec_identification_type())]

    def _get_formatted_sequence(self, number=0):
        if self.country_code == 'EC':
            doc = format_document_sequence(self.l10n_ec_serial_entity, self.l10n_ec_emission_point, number)
            if self.l10n_latam_document_type_id:
                return f'{self.l10n_latam_document_type_id.doc_code_prefix} {doc}'
            return f'{self.journal_id.code}/ {doc}'
        return f'{self.l10n_latam_document_type_id.doc_code_prefix} {number}'

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.l10n_latam_use_documents and self.company_id.country_id.code == 'EC':
            return 'l10n_ec_account.report_invoice_document'
        return super()._get_name_invoice_report()

    def _get_starting_sequence(self):
        if self.journal_id.l10n_latam_use_documents:
            if self.l10n_latam_document_type_id:
                return self._get_formatted_sequence()
            return ""
        return super(AccountMove, self)._get_starting_sequence()

    def _prepare_l10n_ec_payment_lines(self, total, new_payment_method=None):
        lines = []
        current_lines = self.l10n_ec_payment_ids
        line_will_change_method = len(current_lines.mapped('payment_method_id')) == 1
        _map = {p.term * (p.term_type == 'months' and 30 or 1): p for p in
                self.l10n_ec_payment_ids}
        invoice_date = self.invoice_date or fields.Date.context_today(self)
        new_payment_method = new_payment_method or self.l10n_ec_payment_method_id
        if self.invoice_payment_term_id:
            parts = self.invoice_payment_term_id.compute(total, invoice_date, self.currency_id)
            parts = [(datetime.strptime(str(d), DEFAULT_SERVER_DATE_FORMAT).date(), v) for d, v in parts]
        else:
            parts = [(self.invoice_date_due or invoice_date, total)]
        for date, amount in parts:
            days = (date - invoice_date).days
            if days < 0:
                days = 0
            p = _map.pop(days, None)
            if p:
                data = {'amount': amount}
                if line_will_change_method:
                    data.update(payment_method_id=new_payment_method.id)
                current_lines -= p
                lines.append((1, p.id, data))
            else:
                lines.append((0, 0, {'payment_method_id': new_payment_method.id,
                                     'term': days, 'term_type': 'days', 'amount': amount}))
        for p in current_lines:
            lines.append((2, p.id, 0))
        return lines

    def _parse_access_key(self, access_key):
        if not self._is_valid_access_key(access_key):
            return None
        return access_key[8:10], access_key[24:27], access_key[27:30], access_key[30:39], access_key[10:23], \
               datetime.strptime(access_key[:8], '%d%m%Y').date(),access_key[23], access_key[47]


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    name_without_code = fields.Char(compute='_compute_name_without_code')

    def _get_computed_taxes(self):
        move = self.move_id
        tax_ids = super(AccountMoveLine, self)._get_computed_taxes()
        if move.move_type not in ('in_invoice', 'out_invoice') or \
                (move.l10n_latam_document_type_id and not move.l10n_latam_document_type_id.l10n_ec_wh_ok):
            return tax_ids.filtered(lambda x: not (x.l10n_ec_tax_group_type or '').startswith('wh_'))
        return tax_ids

    @api.depends('product_id', 'name')
    def _compute_name_without_code(self):
        for rec in self:
            name = rec.name or ''
            code = f'[{rec.product_id.default_code}] '
            if name.startswith(code):
                name = name[len(code):]
            rec.name_without_code = name
