# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError
from datetime import date, timedelta

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    import_ids = fields.Many2one('import.folder','Imports')
    account_debit_id = fields.Many2one('account.account', string='Debit Account')

    def post(self):
    #Metodo sobrecargado para poder anexar los pagos a la importacion
        payments_need_trans = self.filtered(lambda pay: pay.payment_token_id and not pay.payment_transaction_id)
        transactions = payments_need_trans._create_payment_transaction()

        res = super(AccountPayment, self - payments_need_trans)
        res.post()
        transactions.s2s_do_transaction()
        #==agregado===#
        self._compute_get_import()
        #=============#
        return res

    @api.constrains('name')
    def _compute_get_import(self):
        for inv in self.reconciled_invoice_ids:
            if inv.import_ids and inv.type == 'in_invoice':
                self.write({'import_ids':self.import_ids.id})
    
    # @api.depends('reconciled_invoice_ids', 'payment_type', 'partner_type', 'partner_id')
    # def _compute_destination_account_id(self):
    #     for payment in self:
    #         if payment.reconciled_invoice_ids:
    #             payment.destination_account_id = payment.reconciled_invoice_ids[0].mapped(
    #                 'line_ids.account_id').filtered(
    #                     lambda account: account.user_type_id.type in ('receivable', 'payable'))[0]
    #         elif payment.payment_type == 'transfer':
    #             if not payment.company_id.transfer_account_id.id:
    #                 raise UserError(_('There is no Transfer Account defined in the accounting settings. Please define one to be able to confirm this transfer.'))
    #             payment.destination_account_id = payment.company_id.transfer_account_id.id
    #         elif payment.partner_id:
    #             if payment.partner_type == 'customer':
    #                 payment.destination_account_id = payment.partner_id.property_account_receivable_id.id
    #             else:
    #                 payment.destination_account_id = payment.partner_id.property_account_payable_id.id
    #         elif payment.partner_type == 'customer':
    #             default_account = self.env['ir.property'].get('property_account_receivable_id', 'res.partner')
    #             payment.destination_account_id = default_account.id
    #         elif payment.partner_type == 'supplier':
    #             default_account = self.env['ir.property'].get('property_account_payable_id', 'res.partner')
    #             payment.destination_account_id = default_account.id
    #         if self.account_debit_id:
    #             self.destination_account_id = self.account_debit_id.id
