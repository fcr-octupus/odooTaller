# -*- coding: utf-8 -*-
from odoo import http

# class ImportFolder(http.Controller):
#     @http.route('/import_folder/import_folder/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/import_folder/import_folder/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('import_folder.listing', {
#             'root': '/import_folder/import_folder',
#             'objects': http.request.env['import_folder.import_folder'].search([]),
#         })

#     @http.route('/import_folder/import_folder/objects/<model("import_folder.import_folder"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('import_folder.object', {
#             'object': obj
#         })