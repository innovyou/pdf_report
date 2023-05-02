from odoo import models, fields, api, _
import io
import zipfile
import base64
from logging import getLogger
_logger = getLogger(__name__)

class PDFGenOutputWizard(models.TransientModel):
    _name = "pdfgen.output.wizard"
    _description = "Wizard PDF Generator"
    
    output_file_ids = fields.One2many(
        comodel_name="pdfgen.output.file",
        inverse_name="output_id",
        string="Documents"
    )
    
    output = fields.Char(
        string="Output",
        default=False
    )
    
    def generate_zip(self):
        zip_file = io.BytesIO()

        with zipfile.ZipFile(zip_file, mode="w",compression=zipfile.ZIP_DEFLATED) as zf:
            for f in self.env.context.get('default_output_file_ids'):
                b64 = f[2].get('download_btn')
                b64 = b64[b64.rfind('base64,'):]
                b64 = b64[:b64.rfind(' download')].replace('base64,', '')

                fb = base64.b64decode(b64)
                zf.writestr(f[2].get('filename'), fb)

        zip_file = base64.b64encode(zip_file.getvalue()).decode()
        context = self.env.context.copy()
        context['default_output'] = "<a href='data:application/zip;base64,%s' download='%s.zip'><i class='fa fa-download'></i> %s.zip</a>" % (
            zip_file,
            _('Archive'),
            _('Archive')
        )
        
        return {
            'name': self.env.context.get('default_wizard_name'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pdfgen.output.wizard',
            'target': 'new',
            'context': context,
            'flags': {'initial_mode': 'view'}
        }
        
class PDFGenOutputFile(models.TransientModel):
    _name = "pdfgen.output.file"
    _description = "PDF Generator Output File"
    
    output_id = fields.Many2one(
        comodel_name="pdfgen.output.wizard",
        string="Output"
    )

    filename = fields.Char(
        string="Name"
    )

    file = fields.Binary(
        string="File"
    )
    
    download_btn = fields.Char(
        string="Download"
    )
    
    @api.model
    def download_action(self, filename, file):
        return "<a href='data:application/pdf;base64,%s' download='%s'><i class='fa fa-download'></i> %s</a>" % (file, filename, filename)