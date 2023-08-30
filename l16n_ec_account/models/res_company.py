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


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ec_special_taxpayer = fields.Boolean('Special taxpayer?', compute='_compute_l10n_ec_special_taxpayer',
                                              store=True, readonly=False)
    l10n_ec_keep_accounting = fields.Boolean('Keep accounting?', compute='_compute_l10n_ec_keep_accounting', store=True, readonly=False)
    l10n_ec_special_taxpayer_code = fields.Char('Special taxpayer code')
    l10n_ec_refund_product_id = fields.Many2one('product.product', 'Refund product')
    l10n_ec_property_account_receivable_id = fields.Many2one('account.account', 'Account Receivable')
    l10n_ec_property_account_payable_id = fields.Many2one('account.account', 'Account Payable')

    @api.depends('chart_template_id')
    def _compute_l10n_ec_special_taxpayer(self):
        for rec in self:
            rec.l10n_ec_special_taxpayer = rec.chart_template_id.l10n_ec_special_taxpayer

    @api.depends('chart_template_id')
    def _compute_l10n_ec_keep_accounting(self):
        for rec in self:
            rec.l10n_ec_keep_accounting = rec.chart_template_id.l10n_ec_keep_accounting
