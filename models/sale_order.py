from odoo import models, api


CONTRACT_EMPTY_DATE = '2030-01-01'
CONTRACT_PROD_MARKER = '##PRODUCT##'
CONTRACT_ACCESSORY_MARKER = '##ACCESSORY##'


def rental_product_price(product, partner):
    tax = partner.property_account_receivable_id.tax_ids
    to_excl = 1. / (1. + tax.amount / 100.)
    ratio = product.deposit_price_to_lease_amount_ratio
    return (product.website_public_price * to_excl / ratio)


def generate_invoice_rental_line(contract, marker, product, qtty=1):
    for tmpl_iline in contract.contract_template_id.recurring_invoice_line_ids:
        if marker not in tmpl_iline.name:
            continue
        vals = tmpl_iline._convert_to_write(tmpl_iline.read()[0])
        del vals['price_unit']  # avoid inverse price computation
        for _index in range(qtty):
            vals.update({
                'name': vals['name'].replace(marker, product.display_name),
                'quantity': 1,
                'specific_price': rental_product_price(product,
                                                       contract.partner_id),
                })
            contract.update({'recurring_invoice_line_ids': [(0, 0, vals)]})


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def _create_rental_contract(self, count, product):
        self.ensure_one()

        tmpl = product.rental_contract_tmpl_id
        contract = self.env['account.analytic.account'].create({
            'name': '%s-%02d' % (self.name, count),
            'partner_id': self.partner_id.id,
            'recurring_invoices': True,
            'contract_template_id': tmpl.id,
            'date_start': CONTRACT_EMPTY_DATE,
            'recurring_next_date': CONTRACT_EMPTY_DATE,
            })
        contract._onchange_contract_template_id()
        contract.update({'is_auto_pay': False})

        # Remove all product-marked invoice lines from the contract
        for iline in contract.recurring_invoice_line_ids:
            if (CONTRACT_PROD_MARKER in iline.name or
                    CONTRACT_ACCESSORY_MARKER in iline.name):
                iline.unlink()

        # ... and generate the main rental product one, if any
        # Note accessories will be handled later on.
        generate_invoice_rental_line(contract, CONTRACT_PROD_MARKER, product)

        return contract

    @api.multi
    def generate_rental_contracts(self):
        for record in self:
            count = 0           # count this order's generated contracts
            to_classify = []    # non-main sold products
            accessory_ids = {}  # possible accessories of sold main products
            main_product_to_contract = {}

            # Create rental contract for each ordered main rental product
            for so_line in record.order_line:
                product = so_line.product_id
                if not product.is_rental:
                    continue  # equity, fairphone open install, etc.
                elif not product.rental_contract_tmpl_id:
                    to_classify.append(so_line)  # accessory
                    continue
                for accessory in product.accessory_product_ids:
                    accessory_ids.setdefault(accessory.product_tmpl_id.id,
                                             product)
                for _num in range(int(so_line.product_uom_qty)):
                    count += 1
                    contract = record._create_rental_contract(count, product)
                    main_product_to_contract.setdefault(product.id, contract)

            # Complete contract invoice lines with ordered accessories
            for so_line in to_classify:
                accessory = so_line.product_id.product_tmpl_id
                if accessory.id not in accessory_ids:
                    continue
                main_product = accessory_ids[accessory.id]
                contract = main_product_to_contract[main_product.id]
                generate_invoice_rental_line(
                    contract, CONTRACT_ACCESSORY_MARKER,
                    accessory, int(so_line.product_uom_qty))