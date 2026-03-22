from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


class InvoiceItem(BaseModel):
    description: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    unitPrice: float = Field(ge=0)


class InvoicePreviewRequest(BaseModel):
    customerName: str = Field(min_length=1)
    invoiceNumber: str = Field(min_length=1)
    items: list[InvoiceItem] = Field(min_length=1)


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


@app.post("/api/invoices/preview")
def preview_invoice(payload: InvoicePreviewRequest) -> dict[str, str | float]:
    total = sum(item.quantity * item.unitPrice for item in payload.items)
    summary = (
        f"Invoice {payload.invoiceNumber} for {payload.customerName} "
        f"contains {len(payload.items)} item(s) with a total of EUR {total:.2f}."
    )
    return {"summary": summary, "total": round(total, 2)}
