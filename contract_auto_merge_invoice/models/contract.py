from odoo import api, models


def _key_order_by_recurrence(cline):
    "Function used to sort contract lines by recurrence duration"
    return cline.get_relative_delta(cline.recurring_rule_type, cline.recurring_interval)


class Contract(models.Model):
    _inherit = "contract.contract"

    @api.multi
    def _prepare_invoice(self, *args, **kwargs):
        """Override invoice creation to setup payment at partner's chosen date
        - add auto_merge=True
        - fill-in the partner's auto-payment data

        Note that if contract is_auto_pay is True, this has no effect
        on its invoices.
        """
        vals = super(Contract, self)._prepare_invoice(*args, **kwargs)
        vals["auto_merge"] = True

        for contract in self:
            if not contract.partner_id.invoice_merge_next_date:
                cline = contract.contract_line_ids.sorted(key=_key_order_by_recurrence)
                contract.partner_id.update(
                    {
                        "invoice_merge_next_date": vals["date_invoice"],
                        "invoice_merge_recurring_rule_type": cline.recurring_rule_type,
                        "invoice_merge_recurring_interval": cline.recurring_interval,
                        "auto_merge_invoice": True,
                    }
                )
        return vals
