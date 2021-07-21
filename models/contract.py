import logging

from odoo import models, fields, api


_logger = logging.getLogger(__name__)


class Contract(models.Model):
    _inherit = "account.analytic.account"

    picking_ids = fields.One2many(
        "stock.picking",
        "contract_id",
        string=u"Pickings")

    quant_ids = fields.One2many(
        "stock.quant",
        string=u"Contract-related stock",
        compute="_compute_stock",
        store=False,
        readonly=True,
    )

    @api.depends("picking_ids")
    def _compute_stock(self):
        customer_loc = self.partner_id.property_stock_customer
        for record in self:
            self.quant_ids = self.env["stock.quant"].search([
                ("history_ids.picking_id.contract_id", "=", record.id),
                ("location_id", "=", customer_loc.id)
            ], order="location_id desc")

    def send_all_picking(self):
        self.ensure_one()

        ref = self.env.ref
        picking_type = ref("stock.picking_type_internal")
        orig_location = ref("commown_devices.stock_location_available_for_rent")

        # XXX incorrect partner for B2B:
        dest_location = self.partner_id.set_customer_location()

        move_lines = []
        picking_data = {
            "move_type": "direct",
            "picking_type_id": picking_type.id,
            "location_id": orig_location.id,
            "location_dest_id": dest_location.id,
            "min_date": fields.Date.today(),
            "origin": self.name,
            "move_lines": move_lines,
        }

        for so_line in self.mapped(
                "recurring_invoice_line_ids.sale_order_line_id"):
            product = so_line.product_id.product_tmpl_id.stockable_product_id
            if product and product.tracking == "serial":
                move_lines.append((0, 0, {
                    "name": product.name,
                    "picking_type_id": picking_type.id,
                    "location_id": orig_location.id,
                    "location_dest_id": dest_location.id,
                    "product_id": product.id,
                    "product_uom_qty": so_line.product_uom_qty,
                    "product_uom": so_line.product_uom.id,
                }))

        if not move_lines:
            raise ValueError("No storable product found on contract %s"
                             % self.name)

        picking = self.env["stock.picking"].create(picking_data)
        picking.action_confirm()
        picking.action_assign()
        self.picking_ids |= picking

        return picking
