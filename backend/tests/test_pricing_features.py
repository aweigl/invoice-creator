import sys
import unittest
from decimal import Decimal
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pricing import build_line_items
from app.services.validator import validate_invoice_rows


def make_row(**overrides):
    row = {
        "invoice_number": "INV-2026-03-001",
        "invoice_date": "2026-03-31",
        "due_date": "2026-04-07",
        "customer_name": "Anna Becker",
        "customer_address": "Musterweg 12, 50823 Koeln",
        "dog_name": "Balu",
        "billing_month": "2026-03",
        "subscription_plan": "1x_week",
        "daily_count": 2,
        "daily_dates": "2026-03-05,2026-03-12",
        "daily_count_rebate": False,
        "include_test_run": True,
        "currency": "EUR",
    }
    row.update(overrides)
    return row


class PricingFeaturesTest(unittest.TestCase):
    def test_missing_km_surcharge_column_defaults_to_false(self):
        result = validate_invoice_rows([make_row()], filename="legacy.csv")

        self.assertEqual(result.invalid_rows, 0)
        self.assertFalse(result.validated_rows[0].include_extended_km_surcharge)

    def test_km_surcharge_uses_default_amount_when_enabled(self):
        result = validate_invoice_rows(
            [make_row(include_extended_km_surcharge=True)],
            filename="with-km.csv",
        )

        self.assertEqual(result.invalid_rows, 0)
        line_items = build_line_items(result.validated_rows[0])
        surcharge_item = line_items[-1]
        self.assertEqual(surcharge_item.description, "Erweiterter Kilometerbereich")
        self.assertEqual(surcharge_item.amount, Decimal("5.00"))

    def test_overrides_and_custom_km_surcharge_affect_matching_items_only(self):
        result = validate_invoice_rows(
            [
                make_row(
                    include_extended_km_surcharge=True,
                    subscription_price_override="150.00",
                    daily_price_override="42.50",
                    test_run_price_override="25.00",
                    extended_km_surcharge_amount="9.50",
                )
            ],
            filename="customized.csv",
        )

        self.assertEqual(result.invalid_rows, 0)
        line_items = build_line_items(result.validated_rows[0])
        self.assertEqual(len(line_items), 4)
        self.assertEqual(line_items[0].unit_price, Decimal("150.00"))
        self.assertEqual(line_items[1].unit_price, Decimal("42.50"))
        self.assertEqual(line_items[1].amount, Decimal("85.00"))
        self.assertEqual(line_items[2].unit_price, Decimal("25.00"))
        self.assertEqual(line_items[3].amount, Decimal("9.50"))

    def test_negative_override_is_rejected(self):
        result = validate_invoice_rows(
            [make_row(subscription_price_override="-1.00")],
            filename="invalid.csv",
        )

        self.assertEqual(result.invalid_rows, 1)
        self.assertEqual(result.errors[0].column, "subscription_price_override")

    def test_localized_money_inputs_are_accepted(self):
        result = validate_invoice_rows(
            [
                make_row(
                    include_extended_km_surcharge=True,
                    test_run_price_override="25,50",
                    extended_km_surcharge_amount="1.234,75",
                )
            ],
            filename="localized.csv",
        )

        self.assertEqual(result.invalid_rows, 0)
        line_items = build_line_items(result.validated_rows[0])
        self.assertEqual(line_items[2].amount, Decimal("25.50"))
        self.assertEqual(line_items[3].amount, Decimal("1234.75"))


if __name__ == "__main__":
    unittest.main()
