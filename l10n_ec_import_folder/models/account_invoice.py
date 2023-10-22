# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError
from datetime import date, timedelta
import json


class accountMove(models.Model):
    _name = 'account.move'
    _inherit = 'account.move'
    
    import_ids = fields.Many2one('import.folder', string="Imports")
    require_import = fields.Boolean(string="Required Import")

    @api.onchange('partner_id')
    def _require_import(self):
        for move in self:
            if move.move_type == 'in_invoice' and move.partner_id.request_import:
                move.require_import = True
            else:
                move.require_import = False
    
    @api.constrains('partner_id','invoice_line_ids','import_ids')
    def changeMandatory(self):
     
        for lines in self.invoice_line_ids:
            if lines.account_id.request_import == True and (self.import_ids == None or not self.import_ids.id) and self.type == 'in_invoice':
                raise ValidationError(_("You can't save if you don't choose an import folder."))

class resPartner(models.Model):
    _name = 'account.account'
    _inherit = 'account.account'

    request_import = fields.Boolean('Request Import Folder')

    

