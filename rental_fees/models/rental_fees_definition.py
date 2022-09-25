from odoo import _, api, fields, models


class RentalFeesDefinition(models.Model):
    _name = "rental_fees.definition"
    _description = (
        "A definition of fees to be paid back to the supplier when renting his hardware"
    )

    name = fields.Char(required=True, copy=False)

    partner_id = fields.Many2one(
        "res.partner",
        string="Supplier",
        help="The supplier concerned by this fees definition",
        required=True,
        domain=[("supplier", "=", True), ("is_company", "=", True)],
    )

    product_template_id = fields.Many2one(
        "product.template",
        string="Product",
        help="The product concerned by this fees definition",
        required=True,
        domain=[("type", "=", "product")],
    )

    order_ids = fields.One2many(
        comodel_name="purchase.order",
        string="Purchase orders",
        inverse_name="fees_definition_id",
        cascade="delete",
        copy=False,
    )

    line_ids = fields.One2many(
        comodel_name="rental_fees.definition_line",
        string="Fees definition lines",
        inverse_name="fees_definition_id",
        cascade="delete",
        copy=False,
    )

    computed_fees_ids = fields.One2many(
        comodel_name="rental_fees.computed_fees",
        string="Computed fees",
        inverse_name="fees_definition_id",
        readonly=True,
        cascade="delete",
        copy=False,
    )

    @api.constrains("partner_id", "product_template_id", "order_ids")
    def _check_no_definition_override(self):
        for fees_def in self:
            overrides = self.env[self._name].search(
                [
                    ("id", "!=", fees_def.id),
                    ("partner_id", "=", fees_def.partner_id.id),
                    ("product_template_id", "=", fees_def.product_template_id.id),
                    ("order_ids", "in", fees_def.order_ids.ids),
                ]
            )
            if overrides:
                raise models.ValidationError(
                    _(
                        "Another fees def, %s (id %d), has the same partner,"
                        "product & order"
                    )
                    % (overrides[0].name, overrides[0].id)
                )

    @api.multi
    def button_open_devices(self):
        self.ensure_one()
        devices = self.mapped("order_ids.picking_ids.move_line_ids.lot_id")
        return {
            "name": _("Devices"),
            "domain": [("id", "in", devices.ids)],
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "res_model": "stock.production.lot",
        }


class RentalFeesDefinitionLine(models.Model):
    _name = "rental_fees.definition_line"
    _description = "Define how to compute rental fees value on a period of time"

    fees_definition_id = fields.Many2one(
        "rental_fees.definition",
        string="Fees definition",
        required=True,
    )

    sequence = fields.Integer(
        string="Index of the period in the fees definition",
        help="Useful to order the periods in the fees definition",
        required=True,
    )

    duration_value = fields.Integer(
        string="Duration value",
        help="Value of the duration of the period, in the dedicated duration units",
        required=True,
    )

    duration_unit = fields.Selection(
        [
            ("days", "Days"),
            ("weeks", "Weeks"),
            ("months", "Months"),
            ("years", "Years"),
        ],
        string="Duration unit",
        help="Units of the duration of the period",
        default="months",
        required=True,
    )

    fees_type = fields.Selection(
        [("fix", "Fixed"), ("proportional", "Proportional")],
        string="Fees type",
        help=(
            "Fixed: value is a time-independent amount. "
            "Proportional: value is the fees for full price"
            " - fees will be computed proportionally with today's price"
        ),
        default="fixed",
        required=True,
    )

    fees_value = fields.Float(
        string="Fees value",
        help="This value is to be interpreted using fees type",
        required=True,
    )

    price_reduction_forecast = fields.Float(
        string="Price reduction forecast",
        help="price ratio (in [0, 1]) used before the period start when evaluating future fees",
        required=True,
        default=0.0,
    )

    rental_rate_forecast = fields.Float(
        string="Rental rate forecast",
        help="forecast of the (rental_days / ownership days) ratio at that time",
        required=True,
        default=1.0,
    )


class RentalFeesComputedFees(models.Model):
    _name = "rental_fees.computed_fees"

    fees_definition_id = fields.Many2one(
        "rental_fees.definition",
        string="Fees definition",
        required=True,
    )

    date = fields.Date(
        string="Computation date",
        help="Last rental day taken into account (must be < today)",
        required=True,
        default=fields.Date.today,
    )

    fees = fields.Float(
        string="Computed fees",
        required=True,
    )

    details = fields.Text(
        string="Details",
        help="",
    )

    invoice_id = fields.Many2one(
        "account.invoice",
        string="Invoice",
        help="The supplier invoice of the computed fees",
        required=True,
    )

    @api.constrains("date")
    def _check_date(self):
        today = fields.Date.today()
        for record in self:
            if record.date > today:
                raise models.ValidationError(
                    _("Fees cannot be computed in the future.")
                )
