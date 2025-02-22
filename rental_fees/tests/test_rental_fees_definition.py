from datetime import date

from odoo.models import ValidationError

from .common import RentalFeesTC


class RentalFeesDefinitionTC(RentalFeesTC):
    def test_partner_coherency_1(self):
        "Check fees partner is coherent with its orders' - update fees def"
        with self.assertRaises(ValidationError) as err:
            self.fees_def.partner_id = self.env.ref("base.res_partner_4").id

        self.assertEqual(
            err.exception.name,
            (
                "Fees definition purchase orders partners must all be"
                " the same as the fees definition's partner"
            ),
        )

    def test_partner_coherency_2(self):
        "Check fees partner is coherent with its orders' - update order"
        with self.assertRaises(ValidationError) as err:
            self.po.partner_id = self.env.ref("base.res_partner_4").id

        self.assertEqual(
            err.exception.name,
            (
                "Purchase order's partner and its fees definition"
                " must have the same partner"
            ),
        )

    def test_purchase_order_no_override(self):
        "Check fees def cannot have partner & product & po in common"
        po2 = self.create_po_and_picking(("N/S 4", "N/S 5"))
        fees_def2 = self.env["rental_fees.definition"].create(
            {
                "name": "fees_def 2",
                "partner_id": po2.partner_id.id,
                "product_template_id": self.storable_product.id,
                "order_ids": [(4, po2.id, 0)],
                "agreed_to_std_price_ratio": 0.5,
            }
        )
        with self.assertRaises(ValidationError) as err:
            fees_def2.order_ids |= self.po

        self.assertEqual(
            err.exception.name,
            (
                "At least one other fees def, %s (id %d), has the same partner,"
                " product & order" % (self.fees_def.name, self.fees_def.id)
            ),
        )

    def test_devices(self):
        fees_def = self.fees_def
        self.assertEqual(
            sorted(d.name for d in fees_def.devices_delivery()),
            ["N/S 1", "N/S 2", "N/S 3"],
        )

        fees_def.order_ids |= self.create_po_and_picking(("N/S 4", "N/S 5"))
        self.assertEqual(
            sorted(d.name for d in fees_def.devices_delivery()),
            ["N/S 1", "N/S 2", "N/S 3", "N/S 4", "N/S 5"],
        )

        act = fees_def.button_open_devices()
        self.assertEqual(
            sorted(self.env[act["res_model"]].search(act["domain"]).mapped("name")),
            ["N/S 1", "N/S 2", "N/S 3", "N/S 4", "N/S 5"],
        )

    def test_prices(self):
        for device in self.fees_def.devices_delivery():
            if device.name == "N/S 1":
                break

        self.assertEqual(
            self.fees_def.prices(device),
            {"standard": 500.0, "purchase": 200.0},
        )

    def test_scrapped_devices(self):
        for device in self.fees_def.devices_delivery():
            if device.name == "N/S 1":
                break
        self.scrap_device(device, date(2021, 3, 15))

        self.assertFalse(
            self.fees_def.scrapped_devices(date(2021, 3, 1)),
        )

        self.assertDictEqual(
            self.fees_def.scrapped_devices(date(2021, 8, 1)),
            {device: {"date": date(2021, 3, 15)}},
        )
