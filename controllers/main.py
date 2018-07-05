import logging
import json

from odoo import http
from odoo.http import request, Response

from odoo.addons.website_sale.controllers.main import WebsiteSale

from odoo.addons.payment_slimpay.models import slimpay_utils


_logger = logging.getLogger(__name__)


class SlimpayController(WebsiteSale):

    @http.route(['/payment/slimpay_transaction/<int:acquirer_id>'],
                type='json', auth="public", website=True)
    def payment_slimpay_transaction(
            self, acquirer_id, tx_type='form', token=None, **kwargs):
        """ Slimpay specific payment transaction creation. Uses the standard
        website_sale method, but creates the slimpay order and respond with
        slimpay's redirect URL instead of a form to be submitted.
        """
        self.payment_transaction(
            acquirer_id, tx_type='form', token=None, **kwargs)
        # Get some required database objects
        so_id = request.session['sale_order_id']
        so = request.env['sale.order'].sudo().browse(so_id)
        partner = so.partner_id
        acquirer = request.env['payment.acquirer'].sudo().browse(acquirer_id)
        return_url = '/shop/payment/validate'
        locale = request.env.context.get('lang', 'fr_FR').split('_')[0]
        # May emit a direct debit only if a mandate exists; unsupported for now
        subscriber = slimpay_utils.subscriber_from_partner(partner)
        return acquirer.slimpay_client.approval_url(
            so.payment_tx_id.reference, so.id, locale, so.amount_total,
            so.currency_id.name, so.currency_id.decimal_places,
            subscriber, return_url)

    @http.route(['/payment/slimpay/s2s/feedback'], type='http',
                auth='public', methods=['POST'], csrf=False)
    def feedback(self):
        """Controller called by slimpay once the customer has finished the
        checkout process. Performs basic checks then delegates to the acquirer.
        """
        post = json.loads(request.httprequest.data)
        _logger.debug('slimpay feedback, post=%s', post)
        tx_ref = post['reference']
        tx = request.env['payment.transaction'].sudo().search(
            [('reference', '=', tx_ref)])
        if len(tx) != 1:
            _logger.warning('Enable to find 1 transaction for %r', tx_ref)
            return Response('Incorrect transaction reference', status=200)
        if tx.acquirer_id.provider != 'slimpay':
            _logger.warning('Feedback called with non slimpay tx %r', tx_ref)
            return Response('Incorrect transaction handler', status=200)
        if tx.state == 'done':
            _logger.debug('Transaction %r is already completed!', tx_ref)
            return Response("OK", status=200)
        if not tx.acquirer_id._slimpay_s2s_validate(tx, post):
            _logger.warning('Invalid feedback for transaction %r', tx_ref)
            return Response('Invalid feedback for order', status=200)
        return Response("OK", status=200)

    def _get_mandatory_billing_fields(self):
        ''' Replace "name" by "firstname" and "lastname" '''
        fields = super(SlimpayController, self)._get_mandatory_billing_fields()
        return ['firstname', 'lastname'] + [f for f in fields if f != 'name']

    def _get_mandatory_shipping_fields(self):
        ''' Replace "name" by "firstname" and "lastname" '''
        fields = super(SlimpayController,
                       self)._get_mandatory_shipping_fields()
        return ['firstname', 'lastname'] + [f for f in fields if f != 'name']

    def values_postprocess(self, order, mode, values, errors, error_msg):
        """ Do not drop firstname and lastname fields for `partner_firstname`
        module compatiblity. """
        new_values, errors, error_msg = super(
            SlimpayController, self).values_postprocess(order, mode, values,
                                                        errors, error_msg)
        for field in ('firstname', 'lastname'):
            if field in values:
                _logger.debug(
                    "payment_slimpay postprocess: %s value has finally *not* "
                    "been dropped.", field)
                new_values[field] = values[field]
        return new_values, errors, error_msg

    def checkout_form_validate(self, mode, all_form_values, data):
        """ Validate partner constraints wrt Slimpay's rule """
        errors, error_msg = super(
            SlimpayController, self).checkout_form_validate(
                mode, all_form_values, data)
        order = request.website.sale_get_order()
        partner = order.partner_id
        for field, msg in partner.slimpay_checks(all_form_values).items():
            errors[field] = 'error'
            error_msg.append(msg)
        return errors, error_msg