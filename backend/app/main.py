from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from app.config import MAX_CSV_BYTES
from app.schemas import (
    AddressAutocompleteResponse,
    AddressDistanceRequest,
    AddressDistanceResponse,
    CsvValidationResult,
    PricingRowsPayload,
)
from app.services.csv_parser import CsvParseError, decode_csv_content, parse_csv_rows
from app.services.geo_routing import (
    AddressLookupError,
    autocomplete_addresses,
    resolve_address_distance,
)
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
        raise HTTPException(status_code=400, detail="Bitte lade eine `.csv`-Datei hoch.")

    try:
        raw_bytes = await file.read()
        if len(raw_bytes) > MAX_CSV_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Die CSV-Datei ist zu groß. Die maximale Größe beträgt {MAX_CSV_BYTES} Byte.",
            )
        content = decode_csv_content(raw_bytes)
        rows = parse_csv_rows(content)
    except CsvParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return validate_invoice_rows(rows, filename=file.filename)


@app.post("/api/invoices/validate-rows", response_model=CsvValidationResult)
def validate_invoice_rows_payload(payload: PricingRowsPayload) -> CsvValidationResult:
    return validate_invoice_rows(payload.rows, filename=payload.filename)


@app.post("/api/address/resolve-distance", response_model=AddressDistanceResponse)
def resolve_address_distance_payload(
    payload: AddressDistanceRequest,
) -> AddressDistanceResponse:
    try:
        return resolve_address_distance(payload.address)
    except AddressLookupError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.get("/api/address/autocomplete", response_model=AddressAutocompleteResponse)
def autocomplete_address_query(q: str = Query(...)) -> AddressAutocompleteResponse:
    normalized_query = q.strip()
    if len(normalized_query) < 3:
        raise HTTPException(
            status_code=400,
            detail="Bitte gib mindestens drei Zeichen für die Adresssuche ein.",
        )

    try:
        return autocomplete_addresses(normalized_query)
    except AddressLookupError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


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
                    "PDF-Erstellung ist derzeit nicht verfügbar. "
                    "Bitte prüfe die WeasyPrint-Systembibliotheken."
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
            detail="Bitte übergebe genau eine Rechnungszeile für den Einzel-PDF-Export.",
        )

    validation_result = validate_invoice_rows(payload.rows, filename=payload.filename)
    if validation_result.invalid_rows > 0 or len(validation_result.validated_rows) != 1:
        raise HTTPException(
            status_code=400,
            detail="Bitte korrigiere die ausgewählte Zeile vor der PDF-Erstellung.",
        )

    row = validation_result.validated_rows[0]
    invoice_document = build_invoice_document(row)
    try:
        pdf_bytes = render_invoice_pdf(invoice_document)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "PDF-Erstellung ist derzeit nicht verfügbar. "
                "Bitte prüfe die WeasyPrint-Systembibliotheken."
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
                "Frontend-Build nicht gefunden. "
                "Führe zuerst den Frontend-Build aus, bevor du die Anwendung über FastAPI auslieferst."
            ),
        )
    return FileResponse(file_path)


@app.get("/")
def serve_frontend_index() -> FileResponse:
    return _frontend_file_response()


@app.get("/{full_path:path}")
def serve_frontend_app(full_path: str) -> FileResponse:
    if full_path.startswith("api/") or full_path == "health":
        raise HTTPException(status_code=404, detail="Nicht gefunden.")

    requested_file = FRONTEND_DIST_DIR / full_path
    if requested_file.exists() and requested_file.is_file():
        return FileResponse(requested_file)

    return _frontend_file_response()
