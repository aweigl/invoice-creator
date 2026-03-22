from decimal import Decimal


SUPPORTED_CURRENCIES = {"EUR"}
DEFAULT_CURRENCY = "EUR"
DEFAULT_TAX_RATE = Decimal("19.00")

SENDER_DETAILS = {
    "name": "FREILAUF Hundebetreuung",
    "address": "Am Schmidtgrund 112, 50765 Köln",
    "email": "mail@freilauf-hunde.de",
    "tax_id": "DE123456789",
    "phone": "+49 163 3682 007",
    "logo_url": "https://image.jimcdn.com/app/cms/image/transf/dimension=380x10000:format=png/path/s9385516516d8a0fa/image/i8cba35488dec94d5/version/1770131785/image.png",
}

DEFAULT_INVOICE_NOTES = "Vielen Dank fuer dein Vertrauen."
