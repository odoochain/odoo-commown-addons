from odoo import fields

from odoo.addons.payment_token_uniquify.tests.common import PaymentTokenUniquifyTC


def _payment_prefs(interval, rule_type, next_date):
    return {
        "invoice_merge_recurring_interval": interval,
        "invoice_merge_recurring_rule_type": rule_type,
        "invoice_merge_next_date": fields.Date.to_date(next_date),
    }


class PaymentTokenTC(PaymentTokenUniquifyTC):
    def setUp(self):
        """Setup test data: two partners of self.company_s1 have a token
        and a contract using it:

          * first token is the main one of the contract's partner
          * second token is directly linked to the contract
        """
        super().setUp()

        token1 = self.new_payment_token(self.company_s1_w1)
        self.contract1 = self.new_contract(self.company_s1_w1)
        self.company_s1_w1.payment_token_id = token1.id

        token2 = self.new_payment_token(self.company_s1_w2)
        self.contract2 = self.new_contract(self.company_s1_w2)
        self.contract2.payment_token_id = token2.id

    def new_contract(self, partner):
        product = self.env.ref("product.product_product_1")
        return self.env["contract.contract"].create(
            {
                "name": "Test Contract",
                "partner_id": partner.id,
                "invoice_partner_id": partner.id,
                "pricelist_id": partner.property_product_pricelist.id,
                "contract_type": "sale",
                "contract_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "name": "Services from #START# to #END#",
                            "quantity": 1,
                            "uom_id": product.uom_id.id,
                            "price_unit": 100,
                            "recurring_rule_type": "monthly",
                            "recurring_interval": 1,
                            "date_start": "2018-02-15",
                            "recurring_next_date": "2018-02-15",
                        },
                    )
                ],
            }
        )

    def _trigger_obsolescence(self, *action_refs, **new_partner_kwargs):
        """Trigger the tested code: a partner of the company creates a new token

        A payment acquirer is used that is first configured to trigger
        the token obsolescence actions passed as xml refs (without their
        common prefix).
        """
        acquirer = self.env.ref("payment.payment_acquirer_transfer")
        for action_ref in action_refs:
            acquirer.obsolescence_action_ids |= self.env.ref(
                "commown.obsolescence_action_" + action_ref
            )

        company_s1_w3 = self.new_worker(self.company_s1, **new_partner_kwargs)
        cm = self._check_obsolete_token_action_job()
        with cm:
            new_token = self.new_payment_token(company_s1_w3, acquirer)
            cm.gen.send(new_token)
        return new_token

    def check_payment_prefs(self, partner, expected_prefs):
        self.assertEqual({f: partner[f] for f in expected_prefs}, expected_prefs)

    def test_action_reattribute_contracts(self):
        # Configure acquirer with contract reattribution and trigger obsolescence:
        new_token = self._trigger_obsolescence("reattribute_contracts")

        # Check the results: the new partner has replaced the old ones as
        # contract partners; the (optional) contracts token has been removed
        # so that the new token is always used for contract automatic payment:
        self.assertEqual(self.contract1.partner_id, new_token.partner_id)
        self.assertEqual(self.contract1.invoice_partner_id, new_token.partner_id)
        self.assertFalse(self.contract1.payment_token_id)

        self.assertEqual(self.contract2.partner_id, new_token.partner_id)
        self.assertEqual(self.contract2.invoice_partner_id, new_token.partner_id)
        self.assertFalse(self.contract2.payment_token_id)

    def test_action_reattribute_draft_contract_invoices(self):
        # Generate draft invoices (contract isauto_pay is False)
        inv = self.contract1._recurring_create_invoice()

        # Configure acquirer with draft invoices reattribution and trigger obsolescence:
        new_token = self._trigger_obsolescence("reattribute_draft_contract_invoices")

        # Check the results: invoices must have been reattributed to the new partner:
        self.assertEqual(inv.partner_id, new_token.partner_id)

    def test_action_set_partner_invoice_merge_prefs_1(self):
        self.company_s1_w1.update(_payment_prefs(2, "monthly", "2018-02-19"))
        self.company_s1_w2.update(_payment_prefs(1, "yearly", "2018-02-28"))

        # Configure acquirer with invoice merge prefs set and trigger obsolescence:
        new_token = self._trigger_obsolescence("set_partner_invoice_merge_prefs")

        # Check the results: payment prefs must have been smartly set on new partner
        self.check_payment_prefs(
            new_token.partner_id, _payment_prefs(2, "monthly", "2018-02-28")
        )

    def test_action_set_partner_invoice_merge_prefs_2(self):
        "Do not change a partner's payment prefs on new mandate signature"
        self.company_s1_w1.update(_payment_prefs(2, "monthly", "2018-02-19"))
        self.company_s1_w2.update(_payment_prefs(1, "yearly", "2018-02-28"))

        # Configure acquirer with invoice merge prefs setting, preset the new
        # partner's payment preferences and trigger obsolescence
        payment_prefs = _payment_prefs(1, "monthly", "2018-02-03")
        new_token = self._trigger_obsolescence(
            "set_partner_invoice_merge_prefs",
            **payment_prefs,
        )

        # Check the results: payment prefs of the new signee must be untouched
        self.check_payment_prefs(new_token.partner_id, payment_prefs)
