import logging

from dateutil.relativedelta import relativedelta

from odoo import api, models, fields


_logger = logging.getLogger(__name__)


class ContractTemplate(models.Model):
    _inherit = 'contract.template'

    transaction_label = fields.Text(
        string='Payment label', default='#INV#',
        help=('Label to be used for the bank payment. '
              'Possible markers: #START#, #END#, #INV# (invoice number)'),
    )


class Contract(models.Model):
    _inherit = 'contract.contract'

    transaction_label = fields.Text(
        string='Payment label', default='#INV#',
        help=('Label to be used for the bank payment. '
              'Possible markers: #START#, #END#, #INV# (invoice number)'),
    )

    def name_get(self):
        result = []
        for record in self:
            _id, name = super(Contract, record).name_get()[0]
            if record.contract_template_id:
                name += ' (%s)' % record.contract_template_id.name
            result.append((record.id, name))
        return result

    def _format_transaction_label(self, invoice, last_date_invoiced):
        self.ensure_one()
        lang = self.env['res.lang'].search([
            ('code', '=', self.partner_id.lang),
        ])
        date_format = lang.date_format or '%m/%d/%Y'
        label = self.transaction_label
        label = label.replace(
            '#START#', invoice.date_invoice.strftime(date_format)
        )
        label = label.replace('#END#', last_date_invoiced.strftime(date_format))
        label = label.replace('#INV#', invoice.number)
        return label

    @api.multi
    def _pay_invoice(self, invoice):
        """ Insert custom payment transaction label into the context
        before executing the standard payment process. """
        if self.transaction_label:
            last_date_invoiced = self.recurring_next_date - relativedelta(days=1)
            label = self._format_transaction_label(invoice, last_date_invoiced)
            _logger.debug('Bank label for invoice %s: %s', invoice.number, label)
            self = self.with_context(slimpay_payin_label=label)
        return super()._pay_invoice(invoice)