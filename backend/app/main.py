from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from app.config import MAX_CSV_BYTES
from app.schemas import (
    CsvValidationResult,
    PricingRowsPayload,
)
from app.services.csv_parser import CsvParseError, decode_csv_content, parse_csv_rows
from app.services.pricing import build_invoice_document
from app.services.validator import validate_invoice_rows
from app.services.zip_bundle import build_zip_bundle

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"

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
        raw_bytes = await file.read()
        if len(raw_bytes) > MAX_CSV_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"CSV file is too large. Maximum size is {MAX_CSV_BYTES} bytes.",
            )
        content = decode_csv_content(raw_bytes)
        rows = parse_csv_rows(content)
    except CsvParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return validate_invoice_rows(rows, filename=file.filename)


@app.post("/api/invoices/validate-rows", response_model=CsvValidationResult)
def validate_invoice_rows_payload(payload: PricingRowsPayload) -> CsvValidationResult:
    return validate_invoice_rows(payload.rows, filename=payload.filename)


@app.post("/api/invoices/generate")
def generate_invoices(payload: PricingRowsPayload) -> StreamingResponse:
    from app.services.pdf_renderer import render_invoice_pdf

    validation_result = validate_invoice_rows(payload.rows, filename=payload.filename)
    if validation_result.invalid_rows > 0:
        raise HTTPException(
            status_code=400,
            detail="Bitte korrigiere die CSV-Daten vor der PDF-Erstellung.",
        )

    archive_files: list[tuple[str, bytes]] = []
    for row in validation_result.validated_rows:
        invoice_document = build_invoice_document(row)
        try:
            pdf_bytes = render_invoice_pdf(invoice_document)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    "PDF-Erstellung ist derzeit nicht verfuegbar. "
                    "Bitte pruefe die WeasyPrint-Systembibliotheken."
                ),
            ) from exc
        archive_files.append((f"{row.invoice_number}.pdf", pdf_bytes))

    archive_content = build_zip_bundle(archive_files)
    return StreamingResponse(
        BytesIO(archive_content),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="rechnungen.zip"',
        },
    )


@app.post("/api/invoices/generate-single")
def generate_single_invoice(payload: PricingRowsPayload) -> StreamingResponse:
    from app.services.pdf_renderer import render_invoice_pdf

    if len(payload.rows) != 1:
        raise HTTPException(
            status_code=400,
            detail="Bitte uebergebe genau eine Rechnungszeile fuer den Einzel-PDF-Export.",
        )

    validation_result = validate_invoice_rows(payload.rows, filename=payload.filename)
    if validation_result.invalid_rows > 0 or len(validation_result.validated_rows) != 1:
        raise HTTPException(
            status_code=400,
            detail="Bitte korrigiere die ausgewaehlte Zeile vor der PDF-Erstellung.",
        )

    row = validation_result.validated_rows[0]
    invoice_document = build_invoice_document(row)
    try:
        pdf_bytes = render_invoice_pdf(invoice_document)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "PDF-Erstellung ist derzeit nicht verfuegbar. "
                "Bitte pruefe die WeasyPrint-Systembibliotheken."
            ),
        ) from exc

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{row.invoice_number}.pdf"',
        },
    )


def _frontend_file_response(path: str = "index.html") -> FileResponse:
    file_path = FRONTEND_DIST_DIR / path
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                "Frontend build not found. Run the frontend build before serving "
                "the application through FastAPI."
            ),
        )
    return FileResponse(file_path)


@app.get("/")
def serve_frontend_index() -> FileResponse:
    return _frontend_file_response()


@app.get("/{full_path:path}")
def serve_frontend_app(full_path: str) -> FileResponse:
    if full_path.startswith("api/") or full_path == "health":
        raise HTTPException(status_code=404, detail="Not found.")

    requested_file = FRONTEND_DIST_DIR / full_path
    if requested_file.exists() and requested_file.is_file():
        return FileResponse(requested_file)

    return _frontend_file_response()
