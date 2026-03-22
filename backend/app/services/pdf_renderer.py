from app.config import SENDER_DETAILS
from app.schemas import InvoiceRow
from app.services.invoice_calculator import calculate_totals

try:
    from weasyprint import HTML
except (ImportError, OSError):  # pragma: no cover - depends on optional system package setup
    HTML = None


def render_invoice_html(invoice: InvoiceRow) -> str:
    totals = calculate_totals(invoice)
    return f"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <style>
      body {{
        font-family: Arial, sans-serif;
        color: #1f2933;
        margin: 40px;
      }}
      h1 {{
        margin-bottom: 24px;
      }}
      .grid {{
        display: flex;
        justify-content: space-between;
        gap: 32px;
        margin-bottom: 32px;
      }}
      .card {{
        flex: 1;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 24px;
      }}
      th, td {{
        border-bottom: 1px solid #d9e2ec;
        padding: 12px 8px;
        text-align: left;
      }}
      .totals {{
        margin-top: 24px;
        width: 280px;
        margin-left: auto;
      }}
      .totals td {{
        border: none;
        padding: 6px 0;
      }}
      .total-row td {{
        font-weight: 700;
      }}
    </style>
  </head>
  <body>
    <h1>Invoice {invoice.invoice_number}</h1>
    <div class="grid">
      <div class="card">
        <strong>Sender</strong>
        <p>{SENDER_DETAILS["name"]}<br>{SENDER_DETAILS["address"]}<br>{SENDER_DETAILS["email"]}<br>{SENDER_DETAILS["tax_id"]}</p>
      </div>
      <div class="card">
        <strong>Bill To</strong>
        <p>{invoice.customer_name}<br>{invoice.customer_address}</p>
        <p>Invoice Date: {invoice.invoice_date}<br>Due Date: {invoice.due_date}</p>
      </div>
    </div>
    <table>
      <thead>
        <tr>
          <th>Description</th>
          <th>Qty</th>
          <th>Unit Price</th>
          <th>Net</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>{invoice.item_description}</td>
          <td>{invoice.quantity}</td>
          <td>{invoice.currency} {invoice.unit_price}</td>
          <td>{invoice.currency} {totals.net_amount}</td>
        </tr>
      </tbody>
    </table>
    <table class="totals">
      <tbody>
        <tr><td>Subtotal</td><td>{invoice.currency} {totals.net_amount}</td></tr>
        <tr><td>Tax ({invoice.tax_rate}%)</td><td>{invoice.currency} {totals.tax_amount}</td></tr>
        <tr class="total-row"><td>Total</td><td>{invoice.currency} {totals.gross_amount}</td></tr>
      </tbody>
    </table>
  </body>
</html>
""".strip()


def render_invoice_pdf(invoice: InvoiceRow) -> bytes:
    if HTML is None:
        raise RuntimeError(
            "WeasyPrint is unavailable. Install the required native system libraries "
            "and the Python package before generating PDFs."
        )

    html = render_invoice_html(invoice)
    return HTML(string=html).write_pdf()
