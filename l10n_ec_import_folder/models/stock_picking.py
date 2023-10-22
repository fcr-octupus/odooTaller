# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError,UserError
from datetime import date, timedelta
from odoo.addons import decimal_precision as dp
from odoo.addons.stock_landed_costs.models import product
import collections

SPLIT_METHOD = [
    ('equal', 'Equal'),
    ('by_quantity', 'By Quantity'),
    ('by_current_cost_price', 'By Current Cost'),
    ('by_weight', 'By Weight'),
    ('by_volume', 'By Volume'),
]

class stockPicking(models.Model):
    _inherit = 'stock.picking'
    
    import_ids = fields.Many2one('import.folder','Imports')


class LandedCost(models.Model):
    _name = 'stock.landed.cost'
    _inherit = 'stock.landed.cost'
    

    @api.onchange('picking_ids','import_ids')
    def _get_product_domain(self):
        if self.import_ids :
            stock = self.import_ids.mapped('stock_ids').mapped('id')
            if stock:
                return  {'domain':{'picking_ids':[('id', 'in', stock)]}}
            else:
                return  {'domain':{'picking_ids':[('id', 'in', [])]}}

    picking_ids = fields.Many2many('stock.picking', string='Transfers',
        copy=False, states={'done': [('readonly', True)]},domain=_get_product_domain)

    import_ids = fields.Many2one('import.folder','Imports', states={'done': [('readonly', True)]})

    cost_lines = fields.One2many('stock.landed.cost.lines', 'cost_id', 'Cost Lines',
        copy=True, states={'done': [('readonly', True)]})

    def fieldEmpty(self):
        if len(self.picking_ids) == 1:
            return True
        else:
            return False

    def invoiceExists(self,inv=None):
        if inv != None:
            invoice = self.env['stock.landed.cost.lines'].search([('invoice_id','=',inv)])
            for inv in invoice:
                if inv.id :
                    return True
                else:
                    return False       
                
    @api.onchange('picking_ids')
    def fillLines(self):
        if self.fieldEmpty():
            for inv in self.picking_ids.import_ids.invoice_ids:    
                if inv.state in ('posted'): #anteriormente usado->('open','paid'):                       
                    for line in inv.invoice_line_ids:
                        if line.product_id.landed_cost_ok and line.product_id.product_tmpl_id.type == 'service' and line.product_id.product_tmpl_id.purchase_ok and not self.invoiceExists(inv.id):
                            self.cost_lines = [(0,0,{'invoice_id': inv.id,
                                                    'cost_id':self._origin.id,
                                                    'product_id':line.product_id.id,
                                                    'price_unit':line.price_subtotal,
                                                    'name':line.product_id.product_tmpl_id.default_code,
                                                    'account_id':line.product_id.product_tmpl_id.property_account_expense_id.id,
                                                    'split_method': line.product_id.product_tmpl_id.split_method_landed_cost if line.product_id.product_tmpl_id.split_method_landed_cost else 'equal',
                                                    })]      
        if not self.picking_ids:
            self.cost_lines.unlink()

   

class LandedCostLine(models.Model):
    _inherit = 'stock.landed.cost.lines'
    _description = 'Stock Landed Cost Line'

   
    # split_method = fields.Selection(SPLIT_METHOD, string='Split Method', required=True)
    invoice_id = fields.Many2one('account.move', 'Invoice' )

    # @api.onchange('product_id')
    # def onchange_product_id(self):
    #     if not self.product_id:
    #         self.quantity = 0.0
    #     self.name = self.product_id.name or ''
    #     self.split_method = self.split_method or 'equal'
    #     self.price_unit = self.product_id.standard_price or 0.0
    #     self.account_id = self.product_id.property_account_expense_id.id or self.product_id.categ_id.property_account_expense_categ_id.id

