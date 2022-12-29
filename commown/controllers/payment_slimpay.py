import logging

from odoo import http
from odoo.http import request

from odoo.addons.website_sale_payment_slimpay.controllers.main import (
    SlimpayControllerWebsiteSale,
)

_logger = logging.getLogger(__name__)


class CommownSlimpayController(SlimpayControllerWebsiteSale):
    @http.route(
        ["/payment/slimpay_transaction/<int:acquirer_id>"],
        type="json",
        auth="public",
        website=True,
    )
    def payment_slimpay_transaction(
        self,
        acquirer_id,
        save_token=False,
        so_id=None,
        access_token=None,
        token=None,
        **kwargs
    ):
        """This method reuses the partner's token unless the SEPA mandate
        product is in current sale order. Note this plays well with
        the `commown.payment` template (in website_sale_templates.xml)
        that hides the token choices from the user. This simplifies
        things for the user, which only sees one payment choice.
        """
        _logger.debug("Examine if partner's mandate can be reused...")

        so_id = so_id or request.session["sale_order_id"]
        so = request.env["sale.order"].sudo().browse(so_id)
        sepa_id = request.env.ref("commown.sepa_mandate").id

        if (
            so.partner_id.payment_token_id
            and sepa_id not in so.mapped("order_line.product_id.product_tmpl_id").ids
        ):
            token = so.partner_id.payment_token_id.id
            _logger.info("Token %s reused!", token)
        else:
            token = None
            _logger.info("Token not reused: SEPA mandate found in the so")

        return super(CommownSlimpayController, self).payment_slimpay_transaction(
            acquirer_id,
            save_token=save_token,
            so_id=so_id,
            access_token=access_token,
            token=token,
            **kwargs,
        )
