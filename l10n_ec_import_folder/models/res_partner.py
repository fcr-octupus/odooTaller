# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError,UserError
from datetime import date, timedelta


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    request_import = fields.Boolean('Request Import Folder')
