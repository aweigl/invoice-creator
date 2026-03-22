from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


TWOPLACES = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


class InvoiceItem(BaseModel):
    description: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(
        validation_alias=AliasChoices("unit_price", "unitPrice"),
        serialization_alias="unit_price",
        ge=0,
    )


class LegacyInvoicePreviewRequest(BaseModel):
    customer_name: str = Field(
        validation_alias=AliasChoices("customer_name", "customerName"),
        serialization_alias="customer_name",
        min_length=1,
    )
    invoice_number: str = Field(
        validation_alias=AliasChoices("invoice_number", "invoiceNumber"),
        serialization_alias="invoice_number",
        min_length=1,
    )
    items: list[InvoiceItem] = Field(min_length=1)


class InvoiceRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    invoice_number: str = Field(
        validation_alias=AliasChoices("invoice_number", "invoiceNumber"),
        serialization_alias="invoice_number",
        min_length=1,
    )
    invoice_date: date = Field(
        validation_alias=AliasChoices("invoice_date", "invoiceDate"),
        serialization_alias="invoice_date",
    )
    due_date: date = Field(
        validation_alias=AliasChoices("due_date", "dueDate"),
        serialization_alias="due_date",
    )
    customer_name: str = Field(
        validation_alias=AliasChoices("customer_name", "customerName"),
        serialization_alias="customer_name",
        min_length=1,
    )
    customer_address: str = Field(
        validation_alias=AliasChoices("customer_address", "customerAddress"),
        serialization_alias="customer_address",
        min_length=1,
    )
    item_description: str = Field(
        validation_alias=AliasChoices("item_description", "itemDescription"),
        serialization_alias="item_description",
        min_length=1,
    )
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(
        validation_alias=AliasChoices("unit_price", "unitPrice"),
        serialization_alias="unit_price",
        ge=0,
    )
    tax_rate: Decimal = Field(
        validation_alias=AliasChoices("tax_rate", "taxRate"),
        serialization_alias="tax_rate",
        ge=0,
    )
    currency: str = Field(min_length=3, max_length=3)


class PricingInvoiceCsvRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    invoice_number: str = Field(min_length=1)
    invoice_date: date
    due_date: date
    customer_name: str = Field(min_length=1)
    customer_address: str = Field(min_length=1)
    dog_name: str = Field(min_length=1)
    billing_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    subscription_plan: Literal["none", "1x_week", "2x_week", "3x_week", "4x_week"]
    daily_count: int = Field(ge=0)
    include_test_run: bool
    currency: str = Field(min_length=3, max_length=3)


class PricingInvoiceLineItem(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal


class PricingInvoiceDocument(BaseModel):
    invoice_number: str
    invoice_date: date
    due_date: date
    customer_name: str
    customer_address: str
    dog_name: str
    billing_month: str
    currency: str
    tax_rate: Decimal
    line_items: list[PricingInvoiceLineItem]
    net_amount: Decimal
    tax_amount: Decimal
    gross_amount: Decimal


class InvoiceTotals(BaseModel):
    net_amount: Decimal
    tax_amount: Decimal
    gross_amount: Decimal


class InvoicePreviewResponse(BaseModel):
    summary: str
    invoice_number: str
    customer_name: str
    currency: str
    net_amount: Decimal
    tax_amount: Decimal
    gross_amount: Decimal


class CsvValidationError(BaseModel):
    row_number: int
    column: str | None = None
    message: str


class CsvValidationResult(BaseModel):
    filename: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: list[CsvValidationError]
    validated_rows: list[PricingInvoiceCsvRow] = Field(default_factory=list)
    sample_row: PricingInvoiceCsvRow | None = None


class PricingRowsPayload(BaseModel):
    filename: str = "bearbeitete-rechnungen.csv"
    rows: list[dict[str, Any]]
