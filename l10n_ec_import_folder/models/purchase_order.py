# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError
from datetime import date, timedelta
from odoo.addons import decimal_precision as dp
import ast
import json


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = 'purchase.order'
    
    import_ids = fields.Many2one('import.folder', string="Imports")
    require_import = fields.Boolean(string="Required Import")

    @api.onchange('partner_id')
    def _require_import(self):
        for move in self:
            if move.partner_id.request_import:
                move.require_import = True
            else:
                move.require_import = False

    def button_confirm(self):
        self.changeMandatory()
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.po_double_validation == 'one_step'\
                    or (order.company_id.po_double_validation == 'two_step'\
                        and order.amount_total < self.env.user.company_id.currency_id._convert(
                            order.company_id.po_double_validation_amount, order.currency_id, order.company_id, order.date_order or fields.Date.today()))\
                    or order.user_has_groups('purchase.group_purchase_manager'):
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
        return True

    #@api.constrains('partner_id')
    def changeMandatory(self):
        if self.partner_id.request_import == True and (self.import_ids.id == None or self.import_ids.id == False):
            raise ValidationError("You can't save if you don't choose an import folder.")

    def action_view_invoice(self, invoices=False):
        res = super(PurchaseOrder, self).action_view_invoice(invoices)
        if self.import_ids:
            vals = (ast.literal_eval(res['context']))
            vals.update({'default_import_ids': self.import_ids.id,})
            res['context'] = json.dumps(vals)
        return res
      
    @api.model
    def _prepare_picking(self):
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.name,
                'partner_id': self.partner_id.id
            })
        if not self.partner_id.property_stock_supplier.id:
            raise ValidationError(_("You must set a Vendor Location for this partner %s") % self.partner_id.name)
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'date': self.date_order,
            'origin': self.name,
            'location_dest_id': self._get_destination_location(),
            'location_id': self.partner_id.property_stock_supplier.id,
            'company_id': self.company_id.id,
            'import_ids': self.import_ids.id,
        }

    def _create_picking(self):
        StockPicking = self.env['stock.picking']
        for order in self:
            if any([ptype in ['product', 'consu'] for ptype in order.order_line.mapped('product_id.type')]):
                pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                if not pickings:
                    res = order._prepare_picking()
                    picking = StockPicking.create(res)
                else:
                    picking = pickings[0]
                moves = order.order_line._create_stock_moves(picking)
                moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
                seq = 0
                for move in sorted(moves, key=lambda move: move.date_deadline):
                    seq += 5
                    move.sequence = seq
                moves._action_assign()
                picking.message_post_with_view('mail.message_origin_link',
                    values={'self': picking, 'origin': order,'import_ids':order.import_ids.id},
                    subtype_id=self.env.ref('mail.mt_note').id)
        return True

    def button_approve(self, force=False):
        result = super(PurchaseOrder, self).button_approve(force=force)
        self._create_picking()
        return result

