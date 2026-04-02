import base64
import binascii
import os
import secrets
import time
from collections import deque
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse

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
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "backend" / ".env")
BASIC_AUTH_REALM = "Invoice Creator"
RATE_LIMIT_WINDOW_SECONDS = 60.0
AUTH_FAILURE_LIMIT = 10
ROUTE_GROUP_LIMITS = {
    "generate": 2,
    "validate": 8,
    "address": 20,
}
_rate_limit_buckets: dict[str, deque[float]] = {}

APP_BASIC_AUTH_USERNAME = os.getenv("APP_BASIC_AUTH_USERNAME")
APP_BASIC_AUTH_PASSWORD = os.getenv("APP_BASIC_AUTH_PASSWORD")

if not APP_BASIC_AUTH_USERNAME or not APP_BASIC_AUTH_PASSWORD:
    raise RuntimeError(
        "APP_BASIC_AUTH_USERNAME and APP_BASIC_AUTH_PASSWORD must be set."
    )


def _current_time() -> float:
    return time.monotonic()


def _clear_rate_limit_buckets() -> None:
    _rate_limit_buckets.clear()


def _check_rate_limit(bucket_key: str, limit: int) -> bool:
    now = _current_time()
    bucket = _rate_limit_buckets.setdefault(bucket_key, deque())
    window_start = now - RATE_LIMIT_WINDOW_SECONDS

    while bucket and bucket[0] <= window_start:
        bucket.popleft()

    if len(bucket) >= limit:
        return False

    bucket.append(now)
    return True


def _get_client_host(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _decode_basic_auth_header(authorization: str | None) -> tuple[str, str] | None:
    if not authorization:
        return None

    scheme, _, encoded_credentials = authorization.partition(" ")
    if scheme.lower() != "basic" or not encoded_credentials:
        return None

    try:
        decoded = base64.b64decode(encoded_credentials).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None

    username, separator, password = decoded.partition(":")
    if not separator:
        return None

    return username, password


def _authenticate_request(request: Request) -> str | None:
    credentials = _decode_basic_auth_header(request.headers.get("authorization"))
    if credentials is None:
        return None

    username, password = credentials
    if not secrets.compare_digest(username, APP_BASIC_AUTH_USERNAME):
        return None
    if not secrets.compare_digest(password, APP_BASIC_AUTH_PASSWORD):
        return None

    return username


def _is_protected_path(path: str) -> bool:
    return path != "/health"


def _is_local_development_request(request: Request) -> bool:
    return request.url.hostname in {"localhost", "127.0.0.1"}


def _route_group_for_request(request: Request) -> str | None:
    if request.method == "POST" and request.url.path in {
        "/api/invoices/generate",
        "/api/invoices/generate-single",
    }:
        return "generate"

    if request.url.path in {
        "/api/csv/validate",
        "/api/invoices/validate-rows",
    }:
        return "validate"

    if request.url.path in {
        "/api/address/autocomplete",
        "/api/address/resolve-distance",
    }:
        return "address"

    return None


def _unauthorized_response() -> Response:
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": f'Basic realm="{BASIC_AUTH_REALM}"'},
    )


def _too_many_requests_response() -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Zu viele Anfragen. Bitte warte kurz und versuche es erneut."},
    )

app = FastAPI(title="Invoice Creator API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_basic_auth_and_rate_limits(request: Request, call_next):
    if not _is_protected_path(request.url.path) or _is_local_development_request(request):
        return await call_next(request)

    authenticated_username = _authenticate_request(request)
    if authenticated_username is None:
        auth_failure_bucket = f"auth-failure:{_get_client_host(request)}"
        if not _check_rate_limit(auth_failure_bucket, AUTH_FAILURE_LIMIT):
            return _too_many_requests_response()
        return _unauthorized_response()

    route_group = _route_group_for_request(request)
    if route_group is not None:
        bucket_key = f"{route_group}:{authenticated_username}"
        if not _check_rate_limit(bucket_key, ROUTE_GROUP_LIMITS[route_group]):
            return _too_many_requests_response()

    request.state.authenticated_username = authenticated_username
    return await call_next(request)


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
