# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError,UserError
from datetime import date, timedelta


class importFolder(models.Model):
    _name = "import.folder"
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = "Import"


    import_folder = fields.Boolean("Import Folder", default=lambda self: self.env.user.company_id.po_double_validation == 'two_step')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.user.company_id.id
    )
    import_folder_father = fields.Boolean("Have Parent Folder?", default=False)
    import_id = fields.Many2one('import.folder', 'Parent Folder')

    name = fields.Char('Name', tracking=True, required=True)
    elaboration_date =  fields.Date('Date From', required=True, default=fields.Date.today())
    responsable = fields.Many2one('res.users', 'Responsable',default=lambda self: self.env.user.id)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('close', 'Finished')], tracking=True, string='State', index=True, readonly=True, default='open')  

    type_import = fields.Many2one('import.folder.type', string="Type Import", tracking=True, required=True)
    bl = fields.Char('B/L #', tracking=True)
    container = fields.Char('Container', tracking=True) 
    dai = fields.Char('DAI #', tracking=True)
    warehouse = fields.Char('Warehouse')
    customs_regime = fields.Char('Customs Regime')
    boarding_date = fields.Date('Shipping Date', tracking=True)
    estimated_date = fields.Date('Estimated Arrival Date', tracking=True)
    # arrival_date = fields.Date('Fecha de Llegada a Puerto', tracking=True)
    arrival_days = fields.Integer('Arrival Time in Days')
    admission_date = fields.Date('Entry Warehouse Date', tracking=True)
    processing_time = fields.Integer('Customs Processing Time')
    cellar = fields.Char('Input Warehouse', tracking=True) 
    real_days = fields.Integer(string="Import Time(Days)", compute="_compute_days")
   
    #=======Lineas======#
    invoice_ids = fields.One2many('account.move','import_ids',string="Invoices")
   
    stock_ids = fields.One2many('stock.picking','import_ids', string="Pickings")
   
    stock_landed_ids = fields.One2many('stock.landed.cost','import_ids', string="Landed Cost")
   
    payment_ids = fields.One2many( 'account.payment','import_ids', string="Payments")
                                    
    purchase_ids = fields.One2many('purchase.order','import_ids', string="Purchases")

    def close_import(self):
        self.write({'state':'close'})

    def open_import(self):
        self.write({'state':'open'})

    @api.depends('estimated_date','boarding_date')
    def _compute_days(self):
        for s in self:
            if s.estimated_date and s.boarding_date:
                s.real_days = (s.estimated_date - s.boarding_date).days
                return (s.estimated_date - s.boarding_date).days
            else:
                s.real_days=0
                return 0


class importFolder(models.Model):
    _name = 'import.folder.type'
    _description = "Import Type"

    name = fields.Char(string="Name")
    