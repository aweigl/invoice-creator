from decimal import Decimal


SUPPORTED_CURRENCIES = {"EUR"}
DEFAULT_CURRENCY = "EUR"
DEFAULT_TAX_RATE = Decimal("0.00")
MAX_CSV_BYTES = 2 * 1024 * 1024

SUBSCRIPTION_PRICES = {
    "none": Decimal("0.00"),
    "1x_week": Decimal("120.00"),
    "2x_week": Decimal("190.00"),
    "3x_week": Decimal("290.00"),
    "4x_week": Decimal("390.00"),
}
DAILY_PRICE = Decimal("35.00")
DAILY_PRICE_REBATED = Decimal("30.00")
TEST_RUN_PRICE = Decimal("20.00")
EXTENDED_KM_SURCHARGE_DEFAULT = Decimal("5.00")

SENDER_DETAILS = {
    "name": "FREILAUF Hundebetreuung",
    "address": "Am Schmidtgrund 112, 50765 Köln",
    "email": "mail@freilauf-hunde.de",
    "tax_id": "217/5312/4843",
    "phone": "+49 163 3682 007",
    'bank_name': "Commerzbank",
    "iban": "DE98 3704 0044 0377 6515 00",
    'bic': "COBADEFFXXX",
    "logo_url": "https://image.jimcdn.com/app/cms/image/transf/dimension=380x10000:format=png/path/s9385516516d8a0fa/image/i8cba35488dec94d5/version/1770131785/image.png",
}

DEFAULT_INVOICE_NOTES = "Bitte überweisen Sie den Rechnungsbetrag bis spätestens {{invoice.due_date}}"
