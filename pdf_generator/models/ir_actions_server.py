from odoo import models, fields

class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    groups_id = fields.Many2many(
        'res.groups',
        'res_groups_server_rel',
        'uid',
        'gid',
        string='Groups'
    )

    pdfgen_report_id = fields.Many2one(
        comodel_name="pdfgen.report",
        string="Related Report"
    )