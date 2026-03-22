from decimal import Decimal
from typing import cast

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    CsvValidationResult,
    InvoicePreviewResponse,
    InvoiceRow,
    LegacyInvoicePreviewRequest,
)
from app.services.csv_parser import CsvParseError, decode_csv_content, parse_csv_rows
from app.services.invoice_calculator import calculate_totals
from app.services.validator import validate_invoice_rows


app = FastAPI(title="Invoice Creator API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/csv/validate", response_model=CsvValidationResult)
async def validate_csv(file: UploadFile = File(...)) -> CsvValidationResult:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    try:
        content = decode_csv_content(await file.read())
        rows = parse_csv_rows(content)
    except CsvParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return validate_invoice_rows(rows, filename=file.filename)


@app.post("/api/invoices/preview", response_model=InvoicePreviewResponse)
def preview_invoice(payload: InvoiceRow | LegacyInvoicePreviewRequest) -> InvoicePreviewResponse:
    if isinstance(payload, LegacyInvoicePreviewRequest):
        net_amount = sum(item.quantity * item.unit_price for item in payload.items)
        tax_amount = net_amount * 0
        gross_amount = net_amount
        summary = (
            f"Invoice {payload.invoice_number} for {payload.customer_name} "
            f"contains {len(payload.items)} item(s) with a total of EUR {gross_amount:.2f}."
        )
        return InvoicePreviewResponse(
            summary=summary,
            invoice_number=payload.invoice_number,
            customer_name=payload.customer_name,
            currency="EUR",
            net_amount=cast(Decimal, net_amount),
            tax_amount=cast(Decimal,tax_amount),
            gross_amount=cast(Decimal,gross_amount),
        )

    totals = calculate_totals(payload)
    summary = (
        f"Invoice {payload.invoice_number} for {payload.customer_name} "
        f"totals {payload.currency} {totals.gross_amount} "
        f"for {payload.quantity} x {payload.item_description}."
    )
    return InvoicePreviewResponse(
        summary=summary,
        invoice_number=payload.invoice_number,
        customer_name=payload.customer_name,
        currency=payload.currency,
        net_amount=totals.net_amount,
        tax_amount=totals.tax_amount,
        gross_amount=totals.gross_amount,
    )
