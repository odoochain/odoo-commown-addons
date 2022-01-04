from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    phone = fields.Char(track_visibility="onchange")
    mobile = fields.Char(track_visibility="onchange")
