from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'
    ingreso=fields.Char(string="Nombre relacionado")