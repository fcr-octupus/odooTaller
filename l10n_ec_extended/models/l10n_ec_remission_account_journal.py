from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_apply_r_guide = fields.Boolean(string="Is apply the remission guide?", default=False)
    l10n_ec_entity = fields.Char(string="Entity", required=False)
    l10n_ec_emission = fields.Char(string="Emission", required=False)
    l10n_ec_emission_address_id = fields.Many2one('res.partner', string="Emission Address", required=False)

    @api.constrains('is_apply_r_guide', 'type', 'l10n_ec_entity', 'l10n_ec_emission', 'l10n_ec_emission_address_id')
    def _check_fields_required(self):
        for record in self:
            if record.is_apply_r_guide and record.type == 'general':
                if not record.l10n_ec_entity or not record.l10n_ec_emission or not record.l10n_ec_emission_address_id:
                    raise ValidationError("The 'Entity', 'Emission' and 'Emission Address' fields cannot be empty if the 'Is apply the remission guide?' field is checked.")
