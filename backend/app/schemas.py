from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.config import EXTENDED_KM_SURCHARGE_DEFAULT


TWOPLACES = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _normalize_money_like(value: object) -> object:
    if not isinstance(value, str):
        return value

    normalized = value.strip().replace(" ", "").replace("'", "")
    if not normalized:
        return None

    has_comma = "," in normalized
    has_dot = "." in normalized

    if has_comma and has_dot:
        if normalized.rfind(",") > normalized.rfind("."):
            return normalized.replace(".", "").replace(",", ".")
        return normalized.replace(",", "")

    if has_comma:
        return normalized.replace(",", ".")

    return normalized


def _parse_daily_dates(value: str) -> list[date]:
    normalized = value.strip()
    if not normalized:
        return []

    raw_parts = normalized.split(",")
    parts = [part.strip() for part in raw_parts]
    if any(not part for part in parts):
        raise ValueError(
            "daily_dates muss eine Liste von ISO-Daten sein, die innerhalb des Feldes durch Kommas getrennt ist und keine leeren Werte enthält."
        )

    parsed_dates: list[date] = []
    for part in parts:
        try:
            parsed_dates.append(date.fromisoformat(part))
        except ValueError as exc:
            raise ValueError(
                "daily_dates muss gültige ISO-Daten im Format JJJJ-MM-TT enthalten."
            ) from exc

    return parsed_dates


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
    daily_dates: str = Field(default="", validate_default=True)
    daily_count_rebate: bool = False
    include_test_run: bool
    include_extended_km_surcharge: bool = False
    subscription_price_override: Decimal | None = Field(default=None, ge=0)
    daily_price_override: Decimal | None = Field(default=None, ge=0)
    test_run_price_override: Decimal | None = Field(default=None, ge=0)
    extended_km_surcharge_amount: Decimal = Field(
        default=EXTENDED_KM_SURCHARGE_DEFAULT,
        ge=0,
    )
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("daily_dates", mode="before")
    @classmethod
    def normalize_daily_dates(cls, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    @field_validator(
        "subscription_price_override",
        "daily_price_override",
        "test_run_price_override",
        mode="before",
    )
    @classmethod
    def normalize_optional_money(cls, value: object) -> object:
        if value is None:
            return None
        return _normalize_money_like(value)

    @field_validator("extended_km_surcharge_amount", mode="before")
    @classmethod
    def normalize_surcharge_amount(cls, value: object) -> object:
        if value is None:
            return EXTENDED_KM_SURCHARGE_DEFAULT
        normalized = _normalize_money_like(value)
        if normalized is None:
            return EXTENDED_KM_SURCHARGE_DEFAULT
        return normalized

    @field_validator("daily_dates")
    @classmethod
    def validate_daily_dates(cls, value: str, info: ValidationInfo) -> str:
        daily_count = int(info.data.get("daily_count", 0))
        parsed_dates = _parse_daily_dates(value)

        if daily_count == 0:
            if parsed_dates:
                raise ValueError(
                    "daily_dates muss leer sein, wenn daily_count 0 ist."
                )
            return ""

        if not parsed_dates:
            raise ValueError(
                "Bitte gib daily_dates an, wenn daily_count größer als 0 ist."
            )

        if len(parsed_dates) != daily_count:
            raise ValueError(
                "daily_count muss genau der Anzahl der Daten in daily_dates entsprechen."
            )

        return ",".join(parsed_date.isoformat() for parsed_date in parsed_dates)

    @property
    def parsed_daily_dates(self) -> list[date]:
        return _parse_daily_dates(self.daily_dates)


class PricingInvoiceLineItem(BaseModel):
    description: str
    detail: str | None = None
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


class AddressDistanceRequest(BaseModel):
    address: str = Field(min_length=1)


class AddressAutocompleteSuggestion(BaseModel):
    label: str
    value: str
    latitude: float
    longitude: float


class AddressAutocompleteResponse(BaseModel):
    query: str
    suggestions: list[AddressAutocompleteSuggestion] = Field(default_factory=list)


class CoordinatePoint(BaseModel):
    latitude: float
    longitude: float


class AddressDistanceResponse(BaseModel):
    address: str
    resolved_address: str
    origin: CoordinatePoint
    destination: CoordinatePoint
    route_distance_meters: float
    route_distance_km: float
    included_radius_km: float
    should_apply_extended_km_surcharge: bool
