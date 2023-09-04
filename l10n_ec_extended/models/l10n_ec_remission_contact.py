from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    offers_transportation_service = fields.Boolean(string="¿Do you offer transportation services?", default=False)
    license_plate = fields.Char(string="License Plate Number")

    @api.onchange('offers_transportation_service')
    def _onchange_offers_transportation_service(self):
        if not self.offers_transportation_service:
            self.license_plate = False

    @api.constrains('offers_transportation_service', 'license_plate')
    def _check_license_plate(self):
        for partner in self:
            if partner.offers_transportation_service and not partner.license_plate:
                raise models.ValidationError("If you offer transportation services, the license plate number cannot be empty.")

    