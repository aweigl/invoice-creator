from decimal import Decimal

from app.schemas import InvoiceRow, InvoiceTotals, quantize_money


def calculate_totals(invoice: InvoiceRow) -> InvoiceTotals:
    net_amount = quantize_money(invoice.quantity * invoice.unit_price)
    tax_amount = quantize_money(net_amount * (invoice.tax_rate / Decimal("100")))
    gross_amount = quantize_money(net_amount + tax_amount)
    return InvoiceTotals(
        net_amount=net_amount,
        tax_amount=tax_amount,
        gross_amount=gross_amount,
    )
