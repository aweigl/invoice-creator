from pathlib import Path
from typing import Any, cast

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape

from app.config import DEFAULT_INVOICE_NOTES, SENDER_DETAILS
from app.schemas import InvoiceRow
from app.services.invoice_calculator import calculate_totals

try:
    from weasyprint import HTML as WeasyHTML
except (ImportError, OSError):  # pragma: no cover - depends on optional system package setup
    WeasyHTML = None

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
template_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)


def _nl2br(value: str) -> Markup:
    return Markup("<br>").join(escape(value).splitlines())


template_env.filters["nl2br"] = _nl2br


def _format_money(currency: str, amount: object) -> str:
    return f"{currency} {amount}"


def render_invoice_html(invoice: InvoiceRow) -> str:
    totals = calculate_totals(invoice)
    template = template_env.get_template("invoice.html")

    context: dict[str, Any] = {
        "sender": SENDER_DETAILS,
        "recipient": {
            "name": invoice.customer_name,
            "address": invoice.customer_address,
            "tax_id": "",
        },
        "invoice": {
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date.isoformat(),
            "due_date": invoice.due_date.isoformat(),
            "tax_rate": invoice.tax_rate,
        },
        "line_items": [
            {
                "description": invoice.item_description,
                "quantity": invoice.quantity,
                "unit_price_display": _format_money(invoice.currency, invoice.unit_price),
                "amount_display": _format_money(invoice.currency, totals.net_amount),
            }
        ],
        "totals": {
            "net_amount": _format_money(invoice.currency, totals.net_amount),
            "tax_amount": _format_money(invoice.currency, totals.tax_amount),
            "gross_amount": _format_money(invoice.currency, totals.gross_amount),
        },
        "notes": DEFAULT_INVOICE_NOTES,
    }
    return template.render(**context).strip()


def render_invoice_pdf(invoice: InvoiceRow) -> bytes:
    html_class = WeasyHTML
    if html_class is None:
        raise RuntimeError(
            "WeasyPrint is unavailable. Install the required native system libraries "
            "and the Python package before generating PDFs."
        )

    html = render_invoice_html(invoice)
    return cast(bytes, html_class(string=html).write_pdf())
