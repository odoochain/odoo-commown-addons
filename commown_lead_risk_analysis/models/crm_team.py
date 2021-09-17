from odoo import models, fields


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    used_for_risk_analysis = fields.Boolean(
        'Used for risk analysis', default=False)