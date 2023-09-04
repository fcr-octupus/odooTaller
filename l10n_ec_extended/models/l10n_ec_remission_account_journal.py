from odoo import models, fields

class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    is_apply_r_guide = fields.Boolean(string="Is apply the remission guide?",default=False)
    