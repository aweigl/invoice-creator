from datetime import date
from decimal import Decimal, ROUND_HALF_UP

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
    sample_row: InvoiceRow | None = None

