from typing import Any

from pydantic import ValidationError

from app.config import SUPPORTED_CURRENCIES
from app.schemas import CsvValidationError, CsvValidationResult, PricingInvoiceCsvRow


REQUIRED_COLUMNS = {
    "invoice_number",
    "invoice_date",
    "due_date",
    "customer_name",
    "customer_address",
    "dog_name",
    "billing_month",
    "subscription_plan",
    "daily_count",
    "include_test_run",
    "currency",
}

OPTIONAL_COLUMNS_WITH_DEFAULTS = {
    "daily_dates": "",
    "daily_count_rebate": False,
    "include_extended_km_surcharge": False,
}


def validate_invoice_rows(
    rows: list[dict[str, Any]],
    *,
    filename: str,
) -> CsvValidationResult:
    present_columns: set[str] = set(rows[0].keys()) if rows else set()
    missing_columns: list[str] = sorted(REQUIRED_COLUMNS - present_columns)
    errors: list[CsvValidationError] = []
    valid_rows: list[PricingInvoiceCsvRow] = []

    for column in missing_columns:
        errors.append(
            CsvValidationError(
                row_number=0,
                column=column,
                message=f"Pflichtspalte '{column}' fehlt.",
            )
        )

    if missing_columns:
        return CsvValidationResult(
            filename=filename,
            total_rows=len(rows),
            valid_rows=0,
            invalid_rows=len(rows),
            errors=errors,
            validated_rows=[],
            sample_row=None,
        )

    for index, row in enumerate(rows, start=2):
        try:
            invoice_row = PricingInvoiceCsvRow.model_validate(
                {**OPTIONAL_COLUMNS_WITH_DEFAULTS, **row}
            )
        except ValidationError as exc:
            for issue in exc.errors():
                location = issue.get("loc", ())
                column = str(location[0]) if location else None
                errors.append(
                    CsvValidationError(
                        row_number=index,
                        column=column,
                        message=issue.get("msg", "Ungültiger Wert."),
                    )
                )
            continue

        if invoice_row.currency not in SUPPORTED_CURRENCIES:
            errors.append(
                CsvValidationError(
                    row_number=index,
                    column="currency",
                    message=(
                        "Nicht unterstützte Währung. Bitte verwende eine von: "
                        + ", ".join(sorted(SUPPORTED_CURRENCIES))
                        + "."
                    ),
                )
            )
            continue

        valid_rows.append(invoice_row)

    return CsvValidationResult(
        filename=filename,
        total_rows=len(rows),
        valid_rows=len(valid_rows),
        invalid_rows=len(rows) - len(valid_rows),
        errors=errors,
        validated_rows=valid_rows,
        sample_row=valid_rows[0] if valid_rows else None,
    )
