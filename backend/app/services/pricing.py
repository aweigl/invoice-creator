from datetime import date
from decimal import Decimal
from typing import cast

from app.config import (
    DAILY_PRICE,
    DAILY_PRICE_REBATED,
    DEFAULT_TAX_RATE,
    SUBSCRIPTION_PRICES,
    TEST_RUN_PRICE,
)
from app.schemas import (
    PricingInvoiceCsvRow,
    PricingInvoiceDocument,
    PricingInvoiceLineItem,
    quantize_money,
)

SUBSCRIPTION_LABELS = {
    "1x_week": "Abo Hundebetreuung 1x pro Woche",
    "2x_week": "Abo Hundebetreuung 2x pro Woche",
    "3x_week": "Abo Hundebetreuung 3x pro Woche",
    "4x_week": "Abo Hundebetreuung 4x pro Woche",
}


def _format_billing_month(value: str) -> str:
    return date.fromisoformat(f"{value}-01").strftime("%m.%Y")


def build_line_items(row: PricingInvoiceCsvRow) -> list[PricingInvoiceLineItem]:
    items: list[PricingInvoiceLineItem] = []

    subscription_price = SUBSCRIPTION_PRICES[row.subscription_plan]
    if subscription_price > 0:
        items.append(
            PricingInvoiceLineItem(
                description=(
                    f"{SUBSCRIPTION_LABELS[row.subscription_plan].format(dog_name=row.dog_name)} "
                    f"({_format_billing_month(row.billing_month)})"
                ),
                quantity=Decimal("1"),
                unit_price=subscription_price,
                amount=subscription_price,
            )
        )

    if row.daily_count > 0:
        quantity = Decimal(str(row.daily_count))
        daily_price = DAILY_PRICE_REBATED if row.daily_count_rebate else DAILY_PRICE
        items.append(
            PricingInvoiceLineItem(
                description=f"Gassiservice für {row.dog_name}",
                quantity=quantity,
                unit_price=daily_price,
                amount=quantize_money(quantity * daily_price),
            )
        )

    if row.include_test_run:
        items.append(
            PricingInvoiceLineItem(
                description=f"Probetag fuer {row.dog_name}",
                quantity=Decimal("1"),
                unit_price=TEST_RUN_PRICE,
                amount=TEST_RUN_PRICE,
            )
        )

    return items


def build_invoice_document(row: PricingInvoiceCsvRow) -> PricingInvoiceDocument:
    line_items = build_line_items(row)
    net_amount = quantize_money(cast(Decimal, sum(item.amount for item in line_items)))
    tax_amount = quantize_money(net_amount * (DEFAULT_TAX_RATE / Decimal("100")))
    gross_amount = quantize_money(net_amount + tax_amount)

    return PricingInvoiceDocument(
        invoice_number=row.invoice_number,
        invoice_date=row.invoice_date,
        due_date=row.due_date,
        customer_name=row.customer_name,
        customer_address=row.customer_address,
        dog_name=row.dog_name,
        billing_month=row.billing_month,
        currency=row.currency,
        tax_rate=DEFAULT_TAX_RATE,
        line_items=line_items,
        net_amount=net_amount,
        tax_amount=tax_amount,
        gross_amount=gross_amount,
    )
