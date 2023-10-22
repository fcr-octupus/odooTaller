from datetime import datetime
from odoo import _,models, fields, api
from odoo.exceptions import ValidationError
import re
import xml.etree.ElementTree as ET
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools import float_repr, float_round, html_escape
from odoo.tools.xml_utils import cleanup_xml_node, validate_xml_from_attachment
from lxml import etree
from pytz import timezone
from functools import partial
from odoo.exceptions import UserError
from odoo.addons.l10n_ec_edi.models.ir_attachment import L10N_EC_XSD_INFOS
from markupsafe import Markup

XSD = {
    'Guia de Remisión': {
    'name': 'validation.xsd',
    'url': False,  # Establece 'url' como False para indicar que no es una URL externa
}
}
TEST_URL = {
    'reception': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
    'authorization': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
}

PRODUCTION_URL = {
    'reception': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
    'authorization': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
}

DEFAULT_TIMEOUT_WS = 20

class GuiaRemisionModel(models.Model):
    _name = 'guia.remision'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin'
    ]
    _description = 'Guía de Remisión'
    _sequence_field = "name"
    _sequence_date_field = "date"
    _sequence_index = False
    _sequence_monthly_regex = r'^(?P<prefix1>.*?)(?P<year>((?<=\D)|(?<=^))((19|20|21)\d{2}|(\d{2}(?=\D))))(?P<prefix2>\D*?)(?P<month>(0[1-9]|1[0-2]))(?P<prefix3>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$'
    _sequence_yearly_regex = r'^(?P<prefix1>.*?)(?P<year>((?<=\D)|(?<=^))((19|20|21)?\d{2}))(?P<prefix2>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$'
    _sequence_fixed_regex = r'^(?P<prefix1>.*?)(?P<seq>\d{0,9})(?P<suffix>\D*?)$'

    sequence_prefix = fields.Char(compute='_compute_split_sequence', store=True)
    sequence_number = fields.Integer(compute='_compute_split_sequence', store=True)

    date = fields.Date(string='Fecha', default=lambda self: fields.Date.today())
    fecha_inicio = fields.Date('Fecha Inicio', required=True)
    fecha_fin = fields.Date('Fecha Fin', required=True)
    l10n_ec_authorization_date = fields.Datetime(
        string="Authorization date",
        copy=False, readonly=True, tracking=True,
        help="Set once the government authorizes the document, unset if document is cancelled.",
    )
    posted_before = fields.Boolean(copy=False)

    # DICCIONARIO DE DATOS PARA LA GENERACION DEL ARCHIVO XML
    datos = {
        "infoTributaria": {
            "ambiente": "1",
            "tipoEmision": "1",
            "razonSocial": "razonSocial0",
            "nombreComercial": "nombreComercial0",
            "ruc": "0000000000001",
            "claveAcceso": "0000000000000000000000000000000000000000000000000",
            "codDoc": "00",
            "estab": "000",
            "ptoEmi": "000",
            "secuencial": "000000000",
            "dirMatriz": "dirMatriz0",
            "agenteRetencion": "0",
            "contribuyenteRimpe": "CONTRIBUYENTE RÉGIMEN RIMPE",
            # Otros campos de infoTributaria
    },
        "infoGuiaRemision": {
            "dirEstablecimiento": "dirEstablecimiento0",
            "dirPartida": "dirPartida0",
            "razonSocialTransportista": "razonSocialTransportista0",
            "tipoIdentificacionTransportista": "04",
            "rucTransportista": "rucTransportista0",
            "rise": "rise0",
            "obligadoContabilidad": "SI",
            "contribuyenteEspecial": "contribuyente",
            "fechaIniTransporte": "01/01/2000",
            "fechaFinTransporte": "01/01/2000",
            "placa": "placa0",
            # Otros campos de infoGuiaRemision
    },
        "destinatarios": [
        {
            "identificacionDestinatario": "identificacionDestin0",
            "razonSocialDestinatario": "razonSocialDestinatario0",
            "dirDestinatario": "dirDestinatario0",
            "motivoTraslado": "motivoTraslado0",
            "docAduaneroUnico": "docAduaneroUnico0",
            "codEstabDestino": "000",
            "ruta": "ruta0",
            "codDocSustento": "00",
            "numDocSustento": "000-000-000000000",
            "numAutDocSustento": "0000000000",
            "fechaEmisionDocSustento": "01/01/2000",
            # Otros campos de destinatario
            "detalles": [
                {
                    "codigoInterno": "codigoInterno0",
                    "codigoAdicional": "codigoAdicional0",
                    "descripcion": "descripcion0",
                    "cantidad": "50.000000",
                    # Otros campos de detalle
                },
                {
                    "codigoInterno": "codigoInterno1",
                    "codigoAdicional": "codigoAdicional1",
                    "descripcion": "descripcion1",
                    "cantidad": "50.000000",
                    # Otros campos de detalle
                },
            ],
        },
        {
            "identificacionDestinatario": "identificacionDestin1",
            "razonSocialDestinatario": "razonSocialDestinatario1",
            "dirDestinatario": "dirDestinatario1",
            "motivoTraslado": "motivoTraslado1",
            "docAduaneroUnico": "docAduaneroUnico1",
            "codEstabDestino": "000",
            "ruta": "ruta1",
            "codDocSustento": "00",
            "numDocSustento": "000-000-000000000",
            "numAutDocSustento": "0000000000",
            "fechaEmisionDocSustento": "01/01/2000",
            # Otros campos de destinatario
            "detalles": [
                {
                    "codigoInterno": "codigoInterno2",
                    "codigoAdicional": "codigoAdicional2",
                    "descripcion": "descripcion2",
                    "cantidad": "50.000000",
                    # Otros campos de detalle
                },
                {
                    "codigoInterno": "codigoInterno3",
                    "codigoAdicional": "codigoAdicional3",
                    "descripcion": "descripcion3",
                    "cantidad": "50.000000",
                    # Otros campos de detalle
                },
            ],
        },
    ],
    "maquinaFiscal": {
        "marca": "marca0",
        "modelo": "modelo0",
        "serie": "serie0",
    },
    "infoAdicional": [
        {"nombre": "nombre0", "valor": "campoAdicional0"},
        {"nombre": "nombre1", "valor": "campoAdicional1"},
    ],
}
    
    #METODO PARA LA CREACION DEL ARCHIVO XML
    def _create_xml_file(self):
    # Crear el elemento raíz
        root = ET.Element("root")

    # Crear los elementos y subelementos según la estructura XML deseada
        for key, value in datos.items():
            elemento = ET.Element(key)
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    subelemento = ET.Element(subkey)
                    subelemento.text = subvalue
                    elemento.append(subelemento)
            elif isinstance(value, list):
                for destinatario in value:
                    destinatario_element = ET.Element("destinatario")
                    for subkey, subvalue in destinatario.items():
                        subelemento = ET.Element(subkey)
                        if subkey == "detalles":
                            for detalle in subvalue:
                                detalle_element = ET.Element("detalle")
                                for detalle_key, detalle_value in detalle.items():
                                    detalle_subelemento = ET.Element(detalle_key)
                                    detalle_subelemento.text = detalle_value
                                    detalle_element.append(detalle_subelemento)
                                subelemento.append(detalle_element)
                        else:
                            subelemento.text = subvalue
                    destinatario_element.append(subelemento)
                elemento.append(destinatario_element)
            else:
                elemento.text = value
            root.append(elemento)

    # Crear el objeto ElementTree
        tree = ET.ElementTree(root)

    # Guardar el archivo XML
        tree.write("guia_remision.xml", encoding="utf-8", xml_declaration=True)


    #METODO PARA OBTENER EL TIPO DE DOCUMENTO
    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type', string='Document Type', readonly=False, auto_join=True, index='btree_not_null',
        states={'posted': [('readonly', True)]}, store=True)
    l10n_latam_use_documents = fields.Boolean(related='diario.l10n_latam_use_documents')

    l10n_ec_authorization_number = fields.Char(
        string="Authorization number",
        size=49,
        copy=False, index=True, readonly=True,
        tracking=True,
        help="EDI authorization number (same as access key), set upon posting",
    )

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Publicado'),
    ], string='Estado', default='draft')


    #METODO PARA VALIDAR EL ESTADO DE LA GUIA DE REMISION
    def action_post(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'posted'
                record.posted_before = True
                record._l10n_ec_set_authorization_number()
                """ record._get_invoice_edi_content(record) """
                record._l10n_ec_post_move_edi(record)
            else:
                raise ValidationError("No se puede publicar una guía que no esté en estado de borrador.")
    
    def action_unpost(self):
        self.state = 'draft'
    
    @api.model
    def action_post_confirm(self):
        for record in self:
            if record.move_type == 'entry' and record.display_inactive_currency_warning:
                # Lógica para la acción "Confirm" cuando se cumple la condición
                # Por ejemplo, mostrar un mensaje de advertencia
                record.write({'state': 'posted'})
                # Realizar otras acciones necesarias
            else:
                # Lógica para la acción "Post"
                record.write({'state': 'posted'})
                # Realizar otras acciones necesariasÇ
    
    @api.model
    def action_send_print_invoice(self):
        for record in self:
            if record.state == 'posted' and not record.is_move_sent and record.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
                # Lógica para la acción "Send & Print"
                # Por ejemplo, enviar la factura por correo electrónico y marcarla como enviada
                record.write({'is_move_sent': True})
                # Realizar otras acciones necesarias

    
    #METODO PARA OBTENER EL TIPO DE MOVIMIENTO
    @api.model
    def action_reverse_entry(self):
        for record in self:
            if record.move_type == 'entry' and record.state == 'posted':
                # Lógica para la acción "Reverse Entry"
                # Por ejemplo, realizar el reverso de una entrada contable
                # y actualizar el estado de la factura
                record.write({'state': 'draft'})
                # Realizar otras acciones necesarias

    @api.model
    def action_add_credit_note(self):
        for record in self:
            if record.move_type in ('out_invoice', 'in_invoice') and record.state == 'posted':
                # Lógica para la acción "Add Credit Note"
                # Por ejemplo, crear una nota de crédito relacionada
                # y actualizar el estado de la factura
                record.write({'state': 'credit_note_created'})
                # Realizar otras acciones necesarias
    
    @api.model
    def action_cancel(self):
        for record in self:
            if record.state == 'draft' and record.move_type != 'entry':
                # Lógica para la acción "Cancel"
                # Por ejemplo, marcar la factura como cancelada
                record.write({'state': 'cancel'})
                # Realizar otras acciones necesarias

    @api.model
    def action_reset_to_draft(self):
        for record in self:
            if record.show_reset_to_draft_button:
                # Lógica para la acción "Reset to Draft"
                # Por ejemplo, restablecer el registro a estado de borrador
                record.write({'state': 'draft'})
                # Realizar otras acciones necesarias

    @api.model
    def action_set_as_checked(self):
        for record in self:
            if record.to_check:
                # Lógica para la acción "Set as Checked"
                # Por ejemplo, marcar el registro como revisado
                record.write({'checked': True})
                # Realizar otras acciones necesarias

    @api.constrains('fecha_inicio', 'fecha_fin')
    def _check_dates(self):
        for record in self:
            if record.fecha_fin < record.fecha_inicio:
                raise ValidationError("La fecha de fin no puede ser menor que la fecha de inicio.")
            
    @api.model
    def button_cancel(self):
        for record in self:
            if record.state != 'draft' or record.move_type != 'entry':
                # Realiza la lógica correspondiente para la acción "Cancel"
                # Por ejemplo, marcar la factura como cancelada
                record.write({'state': 'cancel'})
                # Realizar otras acciones necesarias

    @api.model
    def button_draft(self):
        for record in self:
            if record.show_reset_to_draft_button:
                # Realiza la lógica correspondiente para la acción "Reset to Draft"
                # Por ejemplo, restablecer el registro a estado de borrador
                record.write({'state': 'draft'})
                # Realizar otras acciones necesarias

    factura_cliente = fields.Many2many(
        comodel_name='account.move',
        string='Factura Cliente',
        domain=[('state', '=', 'posted')], 
        required=True,
    )

    diario = fields.Many2one(
        comodel_name='account.journal',
        string='Diario',
        domain=[('is_apply_r_guide', '=', True)],
        required=True,
        
    )
    company_partner_id = fields.Many2one(
        string='Compañía',
        related="diario.company_partner_id",
        required=True,
        size=300,
    )

    direccion_partida = fields.Many2one(
        string='Dirección de partida',
        related="diario.l10n_ec_emission_address_id",
        required=True,
        readonly=False,
        size=300,
    )

    despachos = fields.Many2many(
        comodel_name='stock.picking',
        string='Despachos',
        domain=[('state', '=', 'done')],
        required=True,
    )

    ruta = fields.Char(
        string='Ruta',
        required=True,
        size=300,
    )

    motivo_traslado = fields.Char(
        string='Motivo de Traslado',
        required=True,
        size=300,
    )
    
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Transportista',
        required=True,
        domain=[('offers_transportation_service', '=', True)],
    )

    license_plate = fields.Char(related='partner_id.license_plate', string="Numero de placa", size=20, required=True)
    sequence= fields.Char(string="Secuencia", readonly=True, default='New')


    #METODO PARA OBTENER LA SECUENCIA
    def _compute_sequence(self):
        for record in self:
            if record.id:
                record.sequence=f'GR-{record.id:02d}'


    #METODO PARA OBTENER EL NUMERO DE AUTORIZACION
    @api.model
    def create(self, vals):
        vals['sequence'] = self.env['ir.sequence'].next_by_code('guia.remision.sequence') or 'New'
        return super(GuiaRemisionModel, self).create(vals) 
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)
    

    name = fields.Char(
        string='Number',
        compute='_compute_name', readonly=False, store=True,
        copy=False,
        tracking=True,
        index='trigram',
    )

    def _l10n_ec_set_authorization_number(self):
            self.ensure_one()
            company = self.company_id
            # NOTE: withholds don't have l10n_latam_document_type_id (WTH journals use separate sequence)
            document_code_sri = '06'  #cambiar por el numero de documento del sri correcto
            environment = company.l10n_ec_production_env and '2' or '1'
            serie = self.diario.l10n_ec_entity + self.diario.l10n_ec_emission
            sequential = self.name.split('-')[2].rjust(9, '0')
            num_filler = '31215214'  # can be any 8 digits, thanks @3cloud !
            emission = '1'  # corresponds to "normal" emission, "contingencia" no longer supported

            if not (document_code_sri and company.partner_id.vat and environment
                    and serie and sequential and num_filler and emission):
                return ''

            now_date = (self.date).strftime('%d%m%Y')
            key_value = now_date + document_code_sri + company.partner_id.vat + environment + serie + sequential + num_filler + emission
            self.l10n_ec_authorization_number = key_value + str(self._l10n_ec_get_check_digit(key_value))

    
    #METODO PARA OBTENER EL DIGITO DE VERIFICACION
    @api.model
    def _l10n_ec_get_check_digit(self, key):
        sum_total = sum([int(key[-i - 1]) * (i % 6 + 2) for i in range(len(key))])
        sum_check = 11 - (sum_total % 11)
        if sum_check >= 10:
            sum_check = 11 - sum_check
        return sum_check
    

    #METODO PARA OBTENER LA SECUENCIA
    @api.depends('state', 'diario', 'date')
    def _compute_name(self):
        self = self.sorted(lambda m: (m.date or '', m.id))
        for move in self:
            move_has_name = move.name and move.name != '/'
            if move_has_name or move.state != 'posted':
                if not move.posted_before and not move._sequence_matches_date():
                    if move._get_last_sequence(lock=False):
                        # The name does not match the date and the move is not the first in the period:
                        # Reset to draft
                        move.name = False
                        continue
                else:
                    if move_has_name and move.posted_before or not move_has_name and move._get_last_sequence(lock=False):
                        # The move either
                        # - has a name and was posted before, or
                        # - doesn't have a name, but is not the first in the period
                        # so we don't recompute the name
                        continue
            if move.date and (not move_has_name or not move._sequence_matches_date()):
                move._set_next_sequence()

        self.filtered(lambda m: not m.name).name = '/'
        """ self._inverse_name() """
        

    #METODO PARA VERIFICAR SI LA SECUENCIA COINCIDE CON LA FECHA
    def _sequence_matches_date(self):
        self.ensure_one()
        date = fields.Date.to_date(self[self._sequence_date_field])
        sequence = self[self._sequence_field]

        if not sequence or not date:
            return True

        format_values = self._get_sequence_format_param(sequence)[1]
        year_match = (
            not format_values["year"]
            or format_values["year"] == date.year % 10 ** len(str(format_values["year"]))
        )
        month_match = not format_values['month'] or format_values['month'] == date.month
        return year_match and month_match

    
    #METODO PARA OBTENER LA SECUENCIA ANTERIOR
    def _get_last_sequence(self, relaxed=False, with_prefix=None, lock=True):
        self.ensure_one()
        if self._sequence_field not in self._fields or not self._fields[self._sequence_field].store:
            raise ValidationError(_('%s is not a stored field', self._sequence_field))
        where_string, param = self._get_last_sequence_domain()
        if self.id or self.id.origin:
            where_string += " AND id != %(id)s "
            param['id'] = self.id or self.id.origin
        if with_prefix is not None:
            where_string += " AND sequence_prefix = %(with_prefix)s "
            param['with_prefix'] = with_prefix

        query = f"""
                SELECT {{field}} FROM {self._table}
                {where_string}
                AND sequence_prefix = (SELECT sequence_prefix FROM {self._table} {where_string} ORDER BY id DESC LIMIT 1)
                ORDER BY sequence_number DESC
                LIMIT 1
        """
        if lock:
            query = f"""
            UPDATE {self._table} SET write_date = write_date WHERE id = (
                {query.format(field='id')}
            )
            RETURNING {self._sequence_field};
            """
        else:
            query = query.format(field=self._sequence_field)

        self.flush_model([self._sequence_field, 'sequence_number', 'sequence_prefix'])
        self.env.cr.execute(query, param)
        return (self.env.cr.fetchone() or [None])[0]


    #METODO PARA OBTENER EL DOMINIO DE LA SECUENCIA
    def _set_next_sequence(self):
        self.ensure_one()
        last_sequence = self._get_last_sequence(relaxed=False)
        new = not last_sequence
        if new:
            last_sequence = self._get_last_sequence(relaxed=True) or self._get_starting_sequence()

        format, format_values = self._get_sequence_format_param(last_sequence)
        if new:
            format_values['seq'] = 0
            format_values['year'] = self[self._sequence_date_field].year % (10 ** format_values['year_length'])
            format_values['month'] = self[self._sequence_date_field].month
        format_values['seq'] = format_values['seq'] + 1

        self[self._sequence_field] = format.format(**format_values)
        self._compute_split_sequence()


    #METODO PARA OBTENER EL FORMATO DE LA SECUENCIA
    def _get_sequence_format_param(self, previous):
        sequence_number_reset = self._deduce_sequence_number_reset(previous)
        regex = self._sequence_fixed_regex
        if sequence_number_reset == 'year':
            regex = self._sequence_yearly_regex
        elif sequence_number_reset == 'month':
            regex = self._sequence_monthly_regex

        format_values = re.match(regex, previous).groupdict()
        format_values['seq_length'] = len(format_values['seq'])
        format_values['year_length'] = len(format_values.get('year', ''))
        if not format_values.get('seq') and 'prefix1' in format_values and 'suffix' in format_values:
            # if we don't have a seq, consider we only have a prefix and not a suffix
            format_values['prefix1'] = format_values['suffix']
            format_values['suffix'] = ''
        for field in ('seq', 'year', 'month'):
            format_values[field] = int(format_values.get(field) or 0)

        placeholders = re.findall(r'(prefix\d|seq|suffix\d?|year|month)', regex)
        format = ''.join(
            "{seq:0{seq_length}d}" if s == 'seq' else
            "{month:02d}" if s == 'month' else
            "{year:0{year_length}d}" if s == 'year' else
            "{%s}" % s
            for s in placeholders
        )
        return format, format_values
    

    #METODO PARA SEPARAR LA SECUENCIA
    @api.depends(lambda self: [self._sequence_field])
    def _compute_split_sequence(self):
        for record in self:
            sequence = record[record._sequence_field] or ''
            regex = re.sub(r"\?P<\w+>", "?:", record._sequence_fixed_regex.replace(r"?P<seq>", ""))  # make the seq the only matching group
            matching = re.match(regex, sequence)
            record.sequence_prefix = sequence[:matching.start(1)]
            record.sequence_number = int(matching.group(1) or 0)

    
    #METODO PARA RESETEAR LA SECUENCIA
    def _conditional_add_to_compute(self, fname, condition):
        field = self._fields[fname]
        to_reset = self.filtered(lambda move:
            condition(move)
            and not self.env.is_protected(field, move._origin)
            and (move._origin or not move[fname])
        )
        to_reset.invalidate_recordset([fname])
        self.env.add_to_compute(field, to_reset)


    #METODO PARA OBTENER LA SECUENCIA
    @api.model
    def _deduce_sequence_number_reset(self, name):
        for regex, ret_val, requirements in [
            (self._sequence_monthly_regex, 'month', ['seq', 'month', 'year']),
            (self._sequence_yearly_regex, 'year', ['seq', 'year']),
            (self._sequence_fixed_regex, 'never', ['seq']),
        ]:
            match = re.match(regex, name or '')
            if match:
                groupdict = match.groupdict()
                if all(req in groupdict for req in requirements):
                    return ret_val
        raise ValidationError(_(
            'The sequence regex should at least contain the seq grouping keys. For instance:\n'
            '^(?P<prefix1>.*?)(?P<seq>\d*)(?P<suffix>\D*?)$'
        ))

    def _get_starting_sequence(self):
        """If use documents then will create a new starting sequence using the document type code prefix and the
        journal document number with a 8 padding number"""
        if (
            self.diario.l10n_latam_use_documents
            and self.company_id.country_id.code == "EC"
        ):
            """ if self.l10n_latam_document_type_id: """
        return self._get_ec_formatted_sequence()
        """ return super()._get_starting_sequence() """

    def _get_last_sequence_domain(self):
                # EXTENDS account sequence.mixin
        self.ensure_one()
        if not self.date or not self.diario:
            return "WHERE FALSE", {}
        where_string = "WHERE diario = %(diario)s AND name != '/' AND state != 'draft'"
        param = {'diario': self.diario.id}
        if self.l10n_latam_use_documents:
            internal_type = self.l10n_latam_document_type_id.internal_type
            document_types = self.env['l10n_latam.document.type'].search([
                ('internal_type', '=', internal_type),
                ('country_id.code', '=', 'EC'),
            ])
            if document_types:
                where_string += """
                AND l10n_latam_document_type_id in %(l10n_latam_document_type_id)s
                """
                param["l10n_latam_document_type_id"] = tuple(document_types.ids)
        return where_string, param
    
    def _get_ec_formatted_sequence(self, number=0):
        return "%s %s-%s-%09d" % (
            'GR',
            self.diario.l10n_ec_entity,
            self.diario.l10n_ec_emission,
            number,
        )

    def _l10n_ec_generate_xml(self, move):
        # Gather XML values
        move_info = self._l10n_ec_get_xml_common_values(move)
        print("AAAAAAAAAAAAAAAAAAAAAA")
        doc_type = 'Guia de Remisión'
        template = {
            'Guia de Remisión': 'l16n_ec_custom_accounting.guia_remision_template',
        }[doc_type]
        """ move_info.update(move._l10n_ec_get_invoice_edi_data()) """

        # Generate XML document
        xml_content = self.env['ir.qweb']._render(template, move_info)
        xml_content = cleanup_xml_node(xml_content)
        errors = self._l10n_ec_validate_with_xsd(xml_content, doc_type)
        
        # Sign the document
        if move.company_id._l10n_ec_is_demo_environment():  # unless we're in a test environment without certificate
            xml_signed = etree.tostring(xml_content, encoding='unicode')
        else:
            xml_signed = move.company_id.sudo().l10n_ec_edi_certificate_id._action_sign(xml_content)

        xml_signed = '<?xml version="1.0" encoding="utf-8" standalone="no"?>' + xml_signed
        print(xml_signed)
        return xml_signed, errors

    def _l10n_ec_generate_demo_xml_attachment(self, move, xml_string):
        """
        Generates an xml attachment to simulate a response from the SRI without the need for a digital signature.
        """
        move.l10n_ec_authorization_date = datetime.now(tz=timezone('America/Guayaquil')).date()
        attachment = self.env['ir.attachment'].create({
            'name': move.display_name + '_demo.xml',
            'res_id': move.id,
            'res_model': move._name,
            'type': 'binary',
            'raw': self._l10n_ec_create_authorization_file(
                move, xml_string,
                move.l10n_ec_authorization_number, move.l10n_ec_authorization_date),
            'mimetype': 'application/xml',
            'description': f"Ecuadorian electronic document generated for document {move.display_name}."
        })
        move.with_context(no_new_invoice=True).message_post(
            body=_(
                "<strong>This is a DEMO response, which means this document was not sent to the SRI.</strong><br/>If you want your document to be processed by the SRI, please set an <strong>Electronic Certificate File</strong> in the settings.<br/><br/>Demo electronic document.<br/><strong>Authorization num:</strong><br/>%s<br/><strong>Authorization date:</strong><br/>%s",
                move.l10n_ec_authorization_number, move.l10n_ec_authorization_date
            ),
            attachment_ids=attachment.ids,
        )
        return [], "", attachment
    

    def _l10n_ec_get_xml_common_values(self, move):
        internal_type = move.l10n_latam_document_type_id.internal_type
        return {
            'move': move,
            'sequential': move.name.split('-')[2].rjust(9, '0'),
            'company': move.company_id,
            'journal': move.diario,

        }
    """ 
                'partner_sri_code': move.partner_id._get_sri_code_for_partner().value,

    'is_invoice': internal_type == 'invoice', """
    def _get_invoice_edi_content(self, invoice):
        # EXTENDS account_edi
        return self._l10n_ec_generate_xml(invoice)[0].encode()
    
    def _l10n_ec_post_move_edi(self, moves):
        res = {}
        for move in moves:
            xml_string, errors = self._l10n_ec_generate_xml(move)

            # Error management
            if errors:

                blocking_level = 'error'
                attachment = None
            else:
                errors, blocking_level, attachment = self._l10n_ec_send_xml_to_authorize(move, xml_string)

            res.update({
                move: {
                    'success': not errors,
                    'error': '<br/>'.join([html_escape(e) for e in errors]),
                    'attachment': attachment,
                    'blocking_level': blocking_level,
                }}
            )
        return res
    
    def _l10n_ec_validate_with_xsd(self, xml_doc, doc_type):
        try:
            xsd_name = XSD[doc_type]['name']
            validate_xml_from_attachment(self.env, xml_doc, xsd_name, prefix='l10n_ec_edi')
            return []
        except UserError as e:
            return [str(e)]
        


    def _l10n_ec_send_xml_to_authorize(self, move, xml_string):
        # === DEMO ENVIRONMENT REPONSE ===
        if move.company_id._l10n_ec_is_demo_environment():
            return self._l10n_ec_generate_demo_xml_attachment(move, xml_string)

        # === STEP 1 ===
        errors, warnings = [], []
        if not move.l10n_ec_authorization_date:
            # Submit the generated XML
            response, zeep_errors, warnings = self._l10n_ec_get_client_service_response(move, 'reception', xml=xml_string.encode())
            if zeep_errors:
                return zeep_errors, 'error', None
            try:
                response_state = response.estado
                response_checks = response.comprobantes and response.comprobantes.comprobante or []
            except AttributeError as err:
                return warnings or [_("SRI response unexpected: %s", err)], 'warning' if warnings else 'error', None

            # Parse govt's response for errors or response state
            if response_state == 'DEVUELTA':
                for check in response_checks:
                    for msg in check.mensajes.mensaje:
                        if msg.identificador != '43':  # 43 means Authorization number already registered
                            errors.append(' - '.join(
                                filter(None, [msg.identificador, msg.informacionAdicional, msg.mensaje, msg.tipo])
                            ))
            elif response_state != 'RECIBIDA':
                errors.append(_("SRI response state: %s", response_state))

            # If any errors have been found (other than those indicating already-authorized document)
            if errors:
                return errors, 'error', None

        # === STEP 2 ===
        # Get authorization status, store response & raise any errors
        attachment = False
        auth_num, auth_date, auth_errors, auth_warnings = self._l10n_ec_get_authorization_status(move)
        errors.extend(auth_errors)
        warnings.extend(auth_warnings)
        if auth_num and auth_date:
            if move.l10n_ec_authorization_number != auth_num:
                warnings.append(_("Authorization number %s does not match document's %s", auth_num, move.l10n_ec_authorization_number))
            move.l10n_ec_authorization_date = auth_date.replace(tzinfo=None)
            attachment = self.env['ir.attachment'].create({
                'name': move.display_name + '.xml',
                'res_id': move.id,
                'res_model': move._name,
                'type': 'binary',
                'raw': self._l10n_ec_create_authorization_file(move, xml_string, auth_num, auth_date),
                'mimetype': 'application/xml',
                'description': f"Ecuadorian electronic document generated for document {move.display_name}."
            })
            move.with_context(no_new_invoice=True).message_post(
                body=_(
                    "Electronic document authorized.<br/><strong>Authorization num:</strong><br/>%s<br/><strong>Authorization date:</strong><br/>%s",
                    move.l10n_ec_authorization_number, move.l10n_ec_authorization_date
                ),
                attachment_ids=attachment.ids,
            )
        elif move.edi_state == 'to_cancel' and not move.company_id.l10n_ec_production_env:
            # In test environment, we act as if invoice had already been cancelled for the govt
            warnings.append(_("Document with access key %s has been cancelled", move.l10n_ec_authorization_number))
        elif not auth_num:
            # No authorization number means the invoice was no authorized
            errors.append(_("Document not authorized by SRI, please try again later"))
        else:
            warnings.append(_("Document with access key %s received by government and pending authorization",
                              move.l10n_ec_authorization_number))

        return errors or warnings, 'error' if errors else 'warning', attachment
    
    def _l10n_ec_create_authorization_file(self, move, xml_string, authorization_number, authorization_date):
        xml_values = {
            'xml_file_content': Markup(xml_string[xml_string.find('?>') + 2:]),  # remove header to embed sent xml
            'mode': 'PRODUCCION' if move.company_id.l10n_ec_production_env else 'PRUEBAS',
            'authorization_number': authorization_number,
            'authorization_date': authorization_date.strftime(DTF),
        }
        xml_response = self.env['ir.qweb']._render('l16n_ec_custom_accounting.guia_remision_template', xml_values)
        xml_response = cleanup_xml_node(xml_response)
        return etree.tostring(xml_response, encoding='unicode')