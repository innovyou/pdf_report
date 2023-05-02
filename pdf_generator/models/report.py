from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from logging import getLogger

import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import PyPDF2
import base64

_logger = getLogger(__name__)

class PDFGenReport(models.Model):
    _name = "pdfgen.report"
    _description = "Report Generator"
    
    name = fields.Char(
        string="Name",
        required=True
    )
    
    code = fields.Char(
        string="Identified by",
        required=True
    )
    
    template_pdf = fields.Binary(
        string="Template",
        required=False
    )
    
    file_name = fields.Char(
        string="File Name",
        required=False
    )
    
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        required=False
    )
       
    placeholder_ids = fields.One2many(
        comodel_name="pdfgen.report.placeholder",
        inverse_name="report_id",
        string="Fields",
        required=True
    )

    ir_action_server_count = fields.Integer(
        string="Action server count",
        compute="_compute_ir_action_server_count"
    )   

    @api.model
    def create(self, values):
        res = super(PDFGenReport, self).create(values)
        res._validate_template_extension(values.get('file_name'))
        res._validate_name_and_identificative()
        
        return res
    
    @api.multi
    def write(self, values):
        res = super(PDFGenReport, self).write(values)
        
        for record in self:
            record._validate_template_extension(record.file_name)
            record._validate_name_and_identificative()
            
        return res
    
    def _validate_template_extension(self, filename):
        if filename and filename.split('.')[-1].lower() != 'pdf':
            raise ValidationError(_("Only PDF extensions allowed"))
        
    def _validate_name_and_identificative(self):
        if self.env['pdfgen.report'].search([('name', '=', self.name), ('id', '!=', self.id)]):
            raise ValidationError(_("A report with this name already exists, report's name need to be unique."))
        if self.env['pdfgen.report'].search([('code', '=', self.code), ('id', '!=', self.id)]):
            raise ValidationError(_("A report with this identificator already exists, report's identificator need to be unique."))
    
    @api.multi
    def copy(self, default={}):
        default.update({
            "name": "%s (Copy)" % (self.name),
            "code": "%s_copy" % (self.code)
        })

        return super(PDFGenReport, self).copy(default)

    @api.model
    def return_output(self, files, wizard_name):
        output = []
        for file in files:
            output.append((0, 0, {
                    'filename': file['name'],
                    'file': file['content'],
                    'download_btn': self.env['pdfgen.output.file'].download_action(file['name'], file['content'])
                }))
            
        return {
            'name': wizard_name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pdfgen.output.wizard',
            'target': 'new',
            'context': {
                'default_output_file_ids': output,
                'default_wizard_name': wizard_name
            },
            'flags': {'initial_mode': 'view'}
        }
    
    @api.model
    def get_report(self, code):
        return self.env['pdfgen.report'].search([('code', '=', code)], limit=1)
    
    def generate_report(self, res_id):
        try:
            template = io.BytesIO(base64.b64decode(self.template_pdf))
            existing_pdf = PyPDF2.PdfFileReader(template)
            pdf_writer = PyPDF2.PdfFileWriter()
        except:
            raise ValidationError(_('Could not load provided template, maybe is broken'))
        
        try:
            record = self.env[self.model_id.model].browse(res_id)
        except:
            raise ValidationError(_("Could not generate report, record not found: %d" % (res_id)))

        try:
            for page in range(existing_pdf.numPages):
                packet = io.BytesIO()
                can = canvas.Canvas(packet, pagesize=letter)
                
                placeholders = self.env['pdfgen.report.placeholder'].search([('id','in',self.placeholder_ids.ids), ('page','=',page+1)])

                for placeholder in placeholders:

                    rgb = [int(i) for i in placeholder.text_color.replace("rgba(", "").replace(")", "").split(",")]
                    placeholder.text_font_id.register_font()
                    can.setFont(placeholder.text_font_id.name, placeholder.text_size)
                    can.setFillColorRGB(*rgb)

                    try:
                        placeholder_value = eval(placeholder.text_field)
                    except Exception as ex:
                        raise ValidationError(_(
                            "An error has occurred while processing %s (ID: %i)'s field on report %s.\n\r%s" % (placeholder.name, placeholder.id, self.name, str(ex))
                        ))
                    
                    if placeholder_value:
                        if placeholder.text_alignment == 'left':
                            can.drawString(placeholder.position_x, placeholder.position_y, str(placeholder_value))
                        elif placeholder.text_alignment == 'right':
                            can.drawRightString(placeholder.position_x, placeholder.position_y, str(placeholder_value))
                        elif placeholder.text_alignment == 'center':
                            can.drawCentredString(placeholder.position_x, placeholder.position_y, str(placeholder_value))

                can.save()
                packet.seek(0)
                
                new_pdf = PyPDF2.PdfFileReader(packet)
                new_page = existing_pdf.getPage(page)

                if placeholders:
                    new_page.mergePage(new_pdf.getPage(0))
                
                pdf_writer.addPage(new_page)
                
            output = io.BytesIO()
            pdf_writer.write(output)
            output.seek(0)

            return {
                'content': base64.b64encode(output.read()).decode(),
                'name': '%s %i.pdf' % (self.model_id.name,res_id)
            }
        except Exception as ex:
            _logger.info("Failed elaborating resource %d >> %s" % (res_id, ex))

            raise ValidationError("An error has occurred: %s" % (str(ex)))

    def preview_report(self):
        return {
            'name': _("Preview"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pdfgen.preview.wizard',
            'target': 'new',
            'context': {
                'default_report_id': self.id
            },
            'flags': {'initial_mode': 'view'}
        }

    def action_list_action_server(self):
        return {
            'name': _('%s Actions') % (self.name),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'ir.actions.server',
            'target': 'current',
            'domain': [('pdfgen_report_id', '=', self.id)],
            'context': self._default_action_server_values()
        }

    def action_add_action_server(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ir.actions.server',
            'target': 'new',
            'context': self._default_action_server_values()
        }
        
    def _default_action_server_values(self):
        default_code = """
pdfgen = env['pdfgen.report'].sudo()
report = pdfgen.get_report('%s')
reports = []

for record in records:
    reports.append(report.generate_report(record.id))

action = pdfgen.return_output(reports, 'Documents')

""" % (self.code)

        return {
            'default_pdfgen_report_id': self.id,
            'default_model_id': self.model_id.id,
            'default_state': 'code',
            'default_name': _('%s Action' % (self.name)),
            'default_code': default_code
        }

    def _compute_ir_action_server_count(self):
        for record in self:
            record.ir_action_server_count = self.env['ir.actions.server'].sudo().search([('pdfgen_report_id', '=', record.id)], count=True)