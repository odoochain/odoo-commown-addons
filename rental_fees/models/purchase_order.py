from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    fees_definition_id = fields.Many2one(
        "rental_fees.definition",
        string="Fees definition",
    )
