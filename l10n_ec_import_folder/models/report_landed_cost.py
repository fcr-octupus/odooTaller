# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
from odoo.addons import decimal_precision as dp
import json
import xlsxwriter
from io import BytesIO
import base64
import string
from collections import Counter

_logger = logging.getLogger(__name__)


class LandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    valuation_adjustment_lines = fields.One2many(
        'stock.valuation.adjustment.lines', 'cost_id', 'Valuation Adjustments',
        states={'done': [('readonly', True)]})

    def get_additional_landed_cost(self, product_id, quantity):
        lis = []
        tit = []
        for i in self.valuation_adjustment_lines:
            if i.product_id.id == product_id and i.quantity == quantity:
                dct = {
                    'additional_landed_cost': i.additional_landed_cost,
                }
                lis.append(dct)
                tit.append(i.cost_line_id.name)
        return lis, tit

    def product_info(self):
        lis = []
        control = []
        for i in self.valuation_adjustment_lines:
            if i.product_id.id not in control or i.quantity not in control:
                control.append(i.product_id.id)
                control.append(i.quantity)
                cos, cant = self.get_additional_landed_cost(i.product_id.id, i.quantity)
                dct = {
                    'pro_name': i.product_id.display_name,
                    'add': lis,
                    'weight': i.weight,
                    'volume': i.volume,
                    'quantity': i.quantity,
                    'measurement': i.product_id.product_tmpl_id.uom_id.name,
                    'cost': cos,
                    'former_cost_per_unit': i.former_cost / i.quantity,
                    'former_cost': i.former_cost,
                }
                lis.append(dct)
        return lis, cant

    def prepare_costs(self):
        """Create cost list to create a pivot table bringing those per row"""
        res = {m: {} for m in set([x.move_id.id for x in self.valuation_adjustment_lines])}
        titles = {m: "" for m in set([x.cost_line_id.id for x in self.valuation_adjustment_lines])}

        for line in self.valuation_adjustment_lines:
            for k in res.keys():
                if line.move_id.id == k:
                    res[k][line.cost_line_id.id] = line.additional_landed_cost
                    titles[line.cost_line_id.id] = line.cost_line_id.name
        return res, titles

    def prepare_move(self):
        """Retrieve stock move lines as reference of report lines"""
        res = {m: None for m in set([x.move_id.id for x in self.valuation_adjustment_lines])}
        for i in self.valuation_adjustment_lines:
            dct = {
                'pro_name': i.product_id.display_name,
                'move_id': i.move_id.id,
                'weight': i.weight,
                'volume': i.volume,
                'quantity': i.quantity,
                'measurement': i.product_id.product_tmpl_id.uom_id.name,
                'former_cost_per_unit': i.former_cost / i.quantity,
                'former_cost': i.former_cost,
            }
            if not res[i.move_id.id]:
                res[i.move_id.id] = dct
        return res

    def fix_date(self, date):
        return date.strftime("%m/%d/%Y") if date else ''

    def import_info(self):
        lis = []
        for i in self.import_ids:
            lis = [{'name': _('Type'), 'value': i.type_import.name},
                   {'name': _('B/L #'), 'value': i.bl},
                   {'name': _('Container'), 'value': i.container},
                   {'name': _('DAI #'), 'value': i.dai},
                   {'name': _('Warehouse'), 'value': i.warehouse},
                   {'name': _('Customs Regime'), 'value': i.customs_regime},
                   {'name': _('Shipping Date'), 'value': self.fix_date(i.boarding_date) or ''},
                   {'name': _('Estimated Arrival Date'), 'value': self.fix_date(i.boarding_date) or ''},
                   # {'name':_('FECHA DE LLEGADA A PUERTO'), 'value':self.fix_date(i.arrival_date) or ''},
                   {'name': _('Arrival Time in Days'), 'value': i.arrival_days},
                   {'name': _('Entry Warehouse Date'), 'value': self.fix_date(i.admission_date) or ''},
                   {'name': _('Customs Processing Time'), 'value': i.processing_time},
                   {'name': _('Input Warehouse'), 'value': i.cellar}]
        return lis

    def report(self):
        pass

    def prepare_costs_values(self):
        """Merge move and costs dicts"""
        res = self.prepare_move()
        costs, cnames = self.prepare_costs()

        for k, v in costs.items():
            res[k]['costs'] = [v[c] for c in sorted(v)]
        return res, [cnames[c] for c in sorted(cnames)]

    def landed_costs_excel_action(self):
        file_data = BytesIO()
        workbook = xlsxwriter.Workbook(file_data)
        import_info = self.import_info()
        product, tit = self.product_info()
        cvalues, cnames = self.prepare_costs_values()
        _logger.info(cnames)
        name = _('Report Landed Cost')
        # self.xslx_body(workbook,product,tit,name,import_info)
        self.create_excel_report(
            workbook,
            cvalues,
            cnames,
            name,
            import_info)
        workbook.close()
        file_data.seek(0)
        attachment = self.env['ir.attachment'].create({
            'datas': base64.b64encode(file_data.getvalue()),
            'name': name,
            'store_fname': name,
            'type': 'binary',
            # 'datas_fname': name+'.xlsx',
        })
        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url += "/web/content/%s?download=true" % (attachment.id)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def create_excel_report(self, workbook, cvalues, cnames, name, import_info):
        title = workbook.add_format({'bold': True, 'border': 1})
        title.set_center_across()
        currency_format = workbook.add_format({'num_format': '[$$-409]#,##0.00', 'border': 1})
        sub_currency_format = workbook.add_format({'num_format': '[$$-409]#,##0.00', 'border': 1, 'bold': True})
        body_right = workbook.add_format({'align': 'right', 'border': 1})
        body_left = workbook.add_format({'align': 'left', 'border': 1})
        body = workbook.add_format({'align': 'left', 'border': 0})
        sheet = workbook.add_worksheet(name)
        sheet.merge_range('E2:H2', name.upper(), title)
        letter = list(string.ascii_uppercase)
        colspan = 1
        col = 2
        lis_tit = (
            _('Product'), _('Weight'), _('Volumen'), _('Quantity'), _('Unit Measure'), _('Previous Cost(Per unit)'),
            _('Previous Cost'))
        tit_f = (_('Final Product Cost(Per unit)'), _('New Cost'))
        header_list = lis_tit + tuple(cnames) + tit_f
        for imp in import_info:
            col += 1
            if col == 10:
                col = 3
                colspan += 4
            sheet.write(col, colspan, imp['name'], body)
            sheet.write(col, colspan + 2, imp['value'], body)
        col = col + 3
        colspan = 1
        colspan1 = 1
        c = 0
        col1 = col
        for j in header_list:
            sheet.set_column('{0}:{0}'.format(chr(c + ord('B'))), len(j) + 4)
            c += 1
            sheet.write(col, colspan1, j, title)
            colspan1 += 1
            if c == 25:
                c = -1
                sheet.set_column('A{0}:{0}'.format(chr(c + ord('B'))), len(j) + 4)
                c += 1

        sheet.set_column('B:B', 80)
        sheet.set_column('F:F', 20)
        _logger.info("Col start {}".format(col))
        for k, v in cvalues.items():
            col += 1
            var = 0
            sheet.write(col, colspan, v['pro_name'], body_left)
            sheet.write(col + 1, colspan, 'Total', title)
            sheet.write(col, colspan + 1, v['weight'], body_right)
            sheet.write(col, colspan + 2, v['volume'], body_right)
            sheet.write(col, colspan + 3, v['quantity'], body_right)
            sheet.write(col, colspan + 4, v['measurement'], body_right)
            sheet.write(col, colspan + 5, v['former_cost_per_unit'], currency_format)
            sheet.write(col, colspan + 6, v['former_cost'], currency_format)
            form = '=sum(' + letter[colspan + 6] + str(col + 1) + ':' + letter[colspan + 6] + str(col1 + 2) + ')'
            sheet.write(col + 1, colspan + 6, form, sub_currency_format)

            _logger.info("Col next {}".format(col))
            for count, i in enumerate(v['costs'], start=7):
                sheet.write(col, colspan + count, i, currency_format)

            last_cost_cell = colspan + count + 1

            unit_cost_fml = "={col_lt_new_cost}{row}/{col_lt_qty}{row}".format(
                col_lt_new_cost="A{}".format(letter[last_cost_cell - 25]) if last_cost_cell > 24 else letter[
                    last_cost_cell + 1],
                col_lt_qty=letter[colspan + 3],
                row=col + 1
            )
            sheet.write(col, colspan + count + 1, unit_cost_fml, currency_format)

            total_cost_fml = "=sum({previous_cost_col}{row}:{last_cost_col}{row})".format(
                previous_cost_col=letter[colspan + 6],
                last_cost_col="A{}".format(letter[last_cost_cell - 27]) if last_cost_cell > 26 else letter[
                    last_cost_cell - 1],
                row=col + 1
            )
            sheet.write(col, colspan + count + 2, total_cost_fml, currency_format)

            # colspan1=colspan
            # colspan2=0
            # for i in p['cost']:   
            #     sheet.write(col,colspan1+7,i['additional_landed_cost'],currency_format)
            #     if colspan1+7>25:
            #         form1='=sum(A'+letter[colspan2]+str(col+1)+':A'+letter[colspan2]+str(col1+2)+')'
            #         colspan2+=1
            #     else:
            #         form1='=sum('+letter[colspan1+7]+str(col+1)+':'+letter[colspan1+7]+str(col1+2)+')'
            #     sheet.write(col+1,colspan1+7,form1,sub_currency_format)
            #     var+=i['additional_landed_cost']
            #     colspan1+=1

            # sheet.write(col,colspan1+7,p['quantity'] != 0 and ((p['former_cost']+var) / p['quantity']) or 0.0,currency_format)
            # sheet.write(col,colspan1+8,p['former_cost']+var,currency_format)

    def xslx_body(self, workbook, product, tit, name, import_info):
        title = workbook.add_format({'bold': True, 'border': 1})
        title.set_center_across()
        currency_format = workbook.add_format({'num_format': '[$$-409]#,##0.00', 'border': 1})
        sub_currency_format = workbook.add_format({'num_format': '[$$-409]#,##0.00', 'border': 1, 'bold': True})
        body_right = workbook.add_format({'align': 'right', 'border': 1})
        body_left = workbook.add_format({'align': 'left', 'border': 1})
        body = workbook.add_format({'align': 'left', 'border': 0})
        sheet = workbook.add_worksheet(name)
        sheet.merge_range('E2:H2', name.upper(), title)
        letter = list(string.ascii_uppercase)
        colspan = 1
        col = 2
        lis_tit = (
            _('Product'), _('Weight'), _('Volumen'), _('Quantity'), _('Unit Measure'), _('Previous Cost(Per unit)'),
            _('Previous Cost'))
        tit_f = (_('Final Product Cost(Per unit)'), _('New Cost'))
        join = lis_tit + tuple(tit) + tit_f
        for imp in import_info:
            col += 1
            if col == 10:
                col = 3
                colspan += 4
            sheet.write(col, colspan, imp['name'], body)
            sheet.write(col, colspan + 2, imp['value'], body)
        col = col + 3
        colspan = 1
        colspan1 = 1
        c = 0
        col1 = col
        for j in join:
            sheet.set_column('{0}:{0}'.format(chr(c + ord('B'))), len(j) + 4)
            c += 1
            sheet.write(col, colspan1, j, title)
            colspan1 += 1
            if c == 25:
                c = -1
                sheet.set_column('A{0}:{0}'.format(chr(c + ord('B'))), len(j) + 4)
                c += 1

        sheet.set_column('B:B', 80)
        sheet.set_column('F:F', 20)
        for p in product:
            col += 1
            var = 0
            sheet.write(col, colspan, p['pro_name'], body_left)
            sheet.write(col + 1, colspan, 'Total', title)
            sheet.write(col, colspan + 1, p['weight'], body_right)
            sheet.write(col, colspan + 2, p['volume'], body_right)
            sheet.write(col, colspan + 3, p['quantity'], body_right)
            sheet.write(col, colspan + 4, p['measurement'], body_right)
            sheet.write(col, colspan + 5, p['former_cost_per_unit'], currency_format)
            sheet.write(col, colspan + 6, p['former_cost'], currency_format)
            form = '=sum(' + letter[colspan + 6] + str(col + 1) + ':' + letter[colspan + 6] + str(col1 + 2) + ')'
            sheet.write(col + 1, colspan + 6, form, sub_currency_format)

            colspan1 = colspan
            colspan2 = 0
            for i in p['cost']:
                sheet.write(col, colspan1 + 7, i['additional_landed_cost'], currency_format)
                if colspan1 + 7 > 25:
                    form1 = '=sum(A' + letter[colspan2] + str(col + 1) + ':A' + letter[colspan2] + str(col1 + 2) + ')'
                    colspan2 += 1
                else:
                    form1 = '=sum(' + letter[colspan1 + 7] + str(col + 1) + ':' + letter[colspan1 + 7] + str(
                        col1 + 2) + ')'
                sheet.write(col + 1, colspan1 + 7, form1, sub_currency_format)
                var += i['additional_landed_cost']
                colspan1 += 1

            sheet.write(col, colspan1 + 7, p['quantity'] != 0 and ((p['former_cost'] + var) / p['quantity']) or 0.0,
                        currency_format)
            sheet.write(col, colspan1 + 8, p['former_cost'] + var, currency_format)
