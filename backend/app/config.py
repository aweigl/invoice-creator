from decimal import Decimal


SUPPORTED_CURRENCIES = {"EUR"}
DEFAULT_CURRENCY = "EUR"
DEFAULT_TAX_RATE = Decimal("19.00")

SENDER_DETAILS = {
    "name": "Example Studio GmbH",
    "address": "Musterstrasse 10, 10115 Berlin",
    "email": "billing@example.com",
    "tax_id": "DE123456789",
}
