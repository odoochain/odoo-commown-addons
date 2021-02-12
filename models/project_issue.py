from odoo import models, api


class CommownProjectIssue(models.Model):
    _name = "project.issue"
    _inherit = [
        "project.issue",
        "commown.shipping.mixin",
        "commown.track_delivery.mixin",
    ]

    _delivery_tracking_parent_rel = _shipping_parent_rel = "project_id"
